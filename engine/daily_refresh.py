"""Daily collection -> lightweight Bocchi discovery -> existing GitHub Pages URL.

API failures and publishing failures are nonzero exits. Raw captures are append-only.
"""
from pathlib import Path
import argparse
import json
import sys
import time
from datetime import datetime, timedelta

from collect_stats import BiliClient
from mining_data import load_population, load_flow_nodes, normalize_video
from review_miner import catalog
from publish_discovery import rebuild, publish
from title_screen import anime_game_flag
from daily_picks import write_picks

ROOT = Path(__file__).resolve().parents[1]


def stamp():
    return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y%m%d_%H%M%S")


def log(message):
    now = stamp()
    line = "[{}] {}".format(now[9:11]+":"+now[11:13]+":"+now[13:15], message)
    print(line, flush=True)
    folder = ROOT / "data/logs"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ("daily_"+now[:8]+".log")).open("a", encoding="utf-8") as f:
        f.write(line+"\n")


def write_capture(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


RANK_RIDS = (1, 3, 4, 5, 36, 160, 181, 188)  # 动画/音乐/游戏/娱乐/科技/生活/影视/数码
FEED_PAGES = 5
SEARCH_KEYWORDS = ("手书", "原创动画", "定格动画", "同人短片", "原创曲", "原创音乐",
                   "翻调", "二创", "动画短片", "微电影", "演奏", "手作", "特效短片", "剧情MV",
                   "原创MV", "自制动画", "手绘动画", "同人动画", "独立短片", "毕业设计动画",
                   "翻唱", "改编曲", "乐器演奏", "定格", "黏土动画", "皮影", "沙画", "特摄",
                   "模型制作", "道具制作", "特效化妆", "分镜", "动画毕设", "原创歌曲", "曲子配布")
SEARCH_PAGES = 2
SEARCH_LIMIT = 40
SEARCH_PER_DAY = 12                      # 每天轮换 12 个词，避免同一批结果反复命中
SEARCH_ORDERS = ("scores", "pubdate", "stow", "click")


def daily_slice(items, day, count):
    """按日期对列表做确定性轮换，保证每天看到不同的一段。"""
    if not items:
        return ()
    start = sum(ord(ch) for ch in day) % len(items)
    return tuple(items[(start + index) % len(items)] for index in range(min(count, len(items))))


def duration_seconds(value):
    """搜索接口的时长是 "1:59" / "1:02:03" 字符串，其它接口是整数秒。"""
    if isinstance(value, (int, float)):
        return int(value)
    parts = str(value or "").split(":")
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return 0
    total = 0
    for number in numbers:
        total = total * 60 + number
    return total


def collect_search(client, enrich_client, keywords=None, pages=SEARCH_PAGES, limit=SEARCH_LIMIT, order=None):
    """关键词搜索（登录态）：结果自带标签，先按标签/时长粗筛，再对存活者补全统计。

    词表与排序方式按天轮换，避免每天抓到同一批结果。
    """
    day = stamp()[:8]
    keywords = keywords or daily_slice(SEARCH_KEYWORDS, day, SEARCH_PER_DAY)
    order = order or SEARCH_ORDERS[sum(ord(ch) for ch in day) % len(SEARCH_ORDERS)]
    log("搜索轮换：{} 词 / order={}".format(len(keywords), order))
    raw, failed = {}, 0
    for keyword in keywords:
        for page in range(1, pages + 1):
            try:
                data = client.get_json("https://api.bilibili.com/x/web-interface/wbi/search/type",
                                       {"search_type": "video", "keyword": keyword,
                                        "page": page, "order": order}, sign_wbi=True, tries=1)
            except Exception as error:
                failed += 1
                log("search {} p{} failed: {}".format(keyword, page, str(error)[:100]))
                continue
            for item in (data or {}).get("result") or []:
                bvid = item.get("bvid")
                if not bvid or bvid in raw:
                    continue
                duration = duration_seconds(item.get("duration"))
                if not (150 < duration <= 1800):
                    continue
                tags = [tag for tag in (item.get("tag") or "").split(",") if tag]
                if anime_game_flag(item.get("title") or "") or anime_game_flag(" ".join(tags)):
                    continue
                play = item.get("play") or 0
                favorites = item.get("favorites") or 0
                raw[bvid] = {"bvid": bvid, "score": (favorites / play if play else 0)}
    picked = sorted(raw.values(), key=lambda row: row["score"], reverse=True)[:limit]
    videos, enriched = {}, 0
    for row in picked:
        try:
            detail = enrich_client.get_json("https://api.bilibili.com/x/web-interface/view",
                                            {"bvid": row["bvid"]}, tries=1)
        except Exception as error:
            failed += 1
            log("search detail {} failed: {}".format(row["bvid"], str(error)[:100]))
            continue
        if normalize_video(detail, "search"):
            videos[row["bvid"]] = detail
            enriched += 1
    return videos, failed, len(raw)


def homefeed_client():
    """登录态客户端：仅当 data/fav_mine/.sessdata 存在且非空时启用。凭据永不打印。"""
    path = ROOT / "data/fav_mine/.sessdata"
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not value:
        return None
    client = BiliClient(interval=1.0)
    client.cookies["SESSDATA"] = value
    return client


def collect_creators(client, mids, per_author=8, limit=60, spacing=2.5):
    """站上已收录作者的新投稿：不依赖任何关键词，直接顺着作者走。

    space 接口风控较严，逐条慢放并在 412 时退避重试。
    """
    found, failed = {}, 0
    for mid in mids:
        if len(found) >= limit:
            break
        data = None
        for _ in range(2):
            try:
                data = client.get_json("https://api.bilibili.com/x/space/wbi/arc/search",
                                       {"mid": mid, "ps": per_author, "pn": 1, "order": "pubdate"},
                                       sign_wbi=True, tries=1)
                break
            except Exception as error:
                failed += 1
                log("creator {} failed: {}".format(mid, str(error)[:90]))
                time.sleep(3)
        time.sleep(spacing)
        if not data:
            continue
        for item in ((data or {}).get("list") or {}).get("vlist") or []:
            bvid = item.get("bvid")
            length = duration_seconds(item.get("length"))
            if not bvid or not (150 < length <= 1800):
                continue
            if anime_game_flag(item.get("title") or ""):
                continue
            found.setdefault(bvid, item)
    videos = {}
    for bvid in found:
        try:
            detail = client.get_json("https://api.bilibili.com/x/web-interface/view", {"bvid": bvid}, tries=1)
        except Exception:
            continue
        time.sleep(0.6)
        if normalize_video(detail, "creator"):
            videos[bvid] = detail
    return videos, failed


def collect_ranking(client, rids=RANK_RIDS):
    """分区排行榜：匿名可用，带完整元数据，一次覆盖多个分区。"""
    videos, ok, failed = {}, 0, 0
    for rid in rids:
        try:
            data = client.get_json("https://api.bilibili.com/x/web-interface/ranking/v2",
                                   {"rid": rid, "type": "all"}, tries=1)
        except Exception as error:
            failed += 1
            log("ranking rid={} failed: {}".format(rid, str(error)[:120]))
            continue
        ok += 1
        for video in (data or {}).get("list") or []:
            if normalize_video(video, "ranking"):
                videos.setdefault(video["bvid"], video)
    return videos, ok, failed


def bootstrap_buvid(client):
    """匿名调 view 需要 buvid3，popular 不会下发，单独取一次。"""
    if not hasattr(client, "cookies"):
        return False
    if "buvid3" in client.cookies:
        return True
    try:
        data = client.get_json("https://api.bilibili.com/x/frontend/finger/spi", tries=1) or {}
        client.cookies["buvid3"] = data["b_3"]
        client.cookies["buvid4"] = data["b_4"]
        return True
    except Exception as error:
        log("buvid bootstrap failed: {}".format(str(error)[:120]))
        return False


def collect_homefeed(client, viewer, pages=FEED_PAGES, max_items=60):
    """首页推荐（登录态）。条目不带宽高/投币，逐条取 view 详情补齐。"""
    videos, failed, detail_requests = {}, 0, 0
    for index in range(0, max(0, pages) * 20, 20):
        try:
            data = client.get_json("https://api.bilibili.com/x/web-interface/wbi/index/top/feed/rcmd",
                                   {"ps": 20, "fresh_type": 4, "feed_version": "V8",
                                    "homepage_ver": 1, "fresh_idx": index},
                                   sign_wbi=True, tries=1)
        except Exception as error:
            failed += 1
            log("homefeed page {} failed: {}".format(index // 20 + 1, str(error)[:120]))
            continue
        for video in (data or {}).get("item") or []:
            bvid = video.get("bvid")
            if not bvid or bvid in videos or len(videos) >= max_items:
                continue
            if normalize_video(video, "homefeed"):
                videos[bvid] = video
                continue
            try:
                detail = viewer.get_json("https://api.bilibili.com/x/web-interface/view",
                                         {"bvid": bvid}, tries=1)
                detail_requests += 1
            except Exception as error:
                failed += 1
                log("homefeed view {} failed: {}".format(bvid, str(error)[:100]))
                continue
            if normalize_video(detail, "homefeed"):
                videos[bvid] = detail
    return videos, failed, detail_requests


def write_source_capture(folder, prefix, captured, videos, src):
    rows = []
    for video in videos.values():
        rec = {key: video.get(key) for key in
               ("bvid", "title", "duration", "pubdate", "owner", "pic", "tname", "stat")}
        rec["view"] = (video.get("stat") or {}).get("view")
        rec["src"] = src
        rows.append(rec)
    if not rows:
        return 0
    write_capture(folder / (prefix + captured + ".json"),
                  {"meta": {"captured_at": captured, "src": src, "n": len(rows)}, "videos": rows})
    return len(rows)


def collect(client, pages=10, seeds=20, auth_client=None, feed_pages=0, rids=(), search_keywords=()):
    mine, samples, graphs = ROOT/"data/fav_mine", ROOT/"data/samples", ROOT/"data/flow_graph"
    known = set(load_population(mine, samples)) | set(load_flow_nodes(graphs))
    videos, failures = {}, []
    for pn in range(1, pages+1):
        try:
            data = client.get_json("https://api.bilibili.com/x/web-interface/popular", {"ps":20,"pn":pn}, tries=1)
            for video in (data or {}).get("list") or []:
                if normalize_video(video, "popular"):
                    videos[video["bvid"]] = video
        except Exception as error:
            failures.append(str(error))
            log("popular page {} failed: {}".format(pn, str(error)[:150]))
            if len(failures) >= 3 and not videos:
                break
    if not videos:
        raise RuntimeError("首页接口未返回有效视频，本次不覆盖网站。"+"; ".join(failures)[:300])
    captured = stamp()
    rows = []
    for video in videos.values():
        rec = {key: video.get(key) for key in ("bvid","title","duration","pubdate","owner","pic","tname","stat")}
        rec["view"] = video["stat"]["view"]
        rec["src"] = "home"
        rows.append(rec)
    write_capture(mine/("favmine_daily_"+captured+".json"), {"meta":{"captured_at":captured,"src":"homepage-daily","n":len(rows)},"videos":rows})
    ranking_videos, ranking_ok, ranking_failed = collect_ranking(client, rids) if rids else ({}, 0, 0)
    ranking_written = write_source_capture(mine, "favmine_rank_", captured, ranking_videos, "ranking")
    if ranking_videos:
        log("分区排行 {} 条（成功 {} 个分区，失败 {}）。".format(ranking_written, ranking_ok, ranking_failed))
    feed_videos, feed_failed, feed_details = ({}, 0, 0)
    if auth_client is not None and feed_pages:
        bootstrap_buvid(client)
        feed_videos, feed_failed, feed_details = collect_homefeed(auth_client, client, feed_pages)
        if feed_videos:
            log("首页推荐 {} 条（补详情 {} 次，失败 {} 次）。".format(
                write_source_capture(mine, "favmine_feed_", captured, feed_videos, "homefeed"),
                feed_details, feed_failed))
    search_videos, search_failed, search_raw = ({}, 0, 0)
    if auth_client is not None and search_keywords:
        bootstrap_buvid(client)
        search_videos, search_failed, search_raw = collect_search(
            auth_client, client, search_keywords, SEARCH_PAGES, SEARCH_LIMIT)
        if search_videos:
            log("关键词搜索 {} 条（粗筛 {} 条，失败 {}）。".format(
                write_source_capture(mine, "favmine_search_", captured, search_videos, "search"),
                search_raw, search_failed))
    fresh = (set(videos) | set(ranking_videos) | set(feed_videos) | set(search_videos)) - known
    log("首页有效 {} 条，首次发现 {} 条。".format(len(rows), len(fresh)))
    pool, meta = catalog(ROOT)
    pool_ids = {r["bvid"] for r in pool}
    try:
        approvals_data = json.loads((ROOT/"data/reference/shelf_approvals.json").read_text(encoding="utf-8"))
        approved_ids = [e["bvid"] for e in (approvals_data["items"] if isinstance(approvals_data, dict) else approvals_data)]
    except Exception:
        approved_ids = []
    # 种子 = 站上已收录作品（相关推荐即同口味邻居）+ 当轮热门里合格的补足
    seed_list = [b for b in approved_ids if b in pool_ids][:seeds]
    hot = sorted([r for r in pool if r["bvid"] in videos and not r.get("motive_cues") and not r.get("screen_flags")
                  and r.get("dur",0)>150 and r.get("reference_n",0)>=30 and r.get("recall_priority") is not None],
                 key=lambda r:r["recall_priority"], reverse=True)
    for row in hot:
        if len(seed_list) >= seeds:
            break
        if row["bvid"] not in seed_list:
            seed_list.append(row["bvid"])
    bootstrap_buvid(client)
    nodes, seen, related_ok = [], set(), 0
    for bvid in seed_list:
        source = videos.get(bvid)
        aid = (source or {}).get("aid")
        if not aid:
            try:
                detail = client.get_json("https://api.bilibili.com/x/web-interface/view", {"bvid": bvid}, tries=1)
                aid = (detail or {}).get("aid")
            except Exception as error:
                log("seed {} detail failed: {}".format(bvid, str(error)[:80]))
                continue
        if not aid:
            continue
        try:
            items = client.get_json("https://api.bilibili.com/x/web-interface/archive/related", {"aid":aid}, tries=1)
            related_ok += 1
        except Exception as error:
            log("related {} failed: {}".format(bvid, str(error)[:100]))
            continue
        for video in items if isinstance(items, list) else []:
            rec = normalize_video(video, "related")
            if not rec or rec["bvid"] in seen or rec["view"]<=0:
                continue
            seen.add(rec["bvid"])
            nodes.append({"bvid":rec["bvid"],"title":rec["title"],"view":rec["view"],"dur":rec["dur"],
                          "coin_rate":rec["coin"]/rec["view"],"fav_rate":rec["fav"]/rec["view"],
                          "like_rate":rec["like"]/rec["view"],"stat":video["stat"],"pubdate":rec["pubdate"],
                          "owner":video.get("owner"),"pic":rec["pic"],"parent":bvid,"arm":"daily"})
    if nodes:
        write_capture(graphs/("godflowdaily_"+stamp()+".json"),{"meta":{"src":"daily","requests":{"related":len(seed_list)}},"flows":[{"nodes":nodes}]})
    return {"finished_at":stamp(),"popular_videos":len(rows),"new_videos":len(fresh),
            "related_nodes":len(nodes),"related_requests_succeeded":related_ok,"popular_pages_failed":len(failures),
            "ranking_videos":ranking_written,"ranking_partitions_ok":ranking_ok,"ranking_partitions_failed":ranking_failed,
            "homefeed_videos":len(feed_videos),"homefeed_pages_failed":feed_failed,
            "search_videos":len(search_videos),"search_candidates":search_raw,"search_failed":search_failed}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--no-publish",action="store_true")
    parser.add_argument("--build-only",action="store_true")
    args=parser.parse_args()
    status_path=ROOT/"data/review/last_success.json"
    status_path.parent.mkdir(parents=True,exist_ok=True)
    log("=== 每日目录开始 ===")
    try:
        if not args.build_only:
            auth = homefeed_client()
            if auth is None:
                log("未找到 .sessdata，首页推荐源跳过（分区排行与热门照常）。")
            result=collect(BiliClient(interval=.8), rids=RANK_RIDS, auth_client=auth,
                           feed_pages=FEED_PAGES if auth else 0,
                           search_keywords=())
            status_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
            log("采集成功："+json.dumps(result,ensure_ascii=False))
        summary=rebuild(ROOT)
        log("轻量新版生成："+json.dumps(summary,ensure_ascii=False))
        try:
            picks_path, picks_funnel, picks = write_picks(ROOT)
            log("每日候选 {} 条 -> {}（当天新候 {}）".format(len(picks), picks_path.name, picks_funnel.get("fresh")))
        except Exception as error:
            log("每日候选生成失败（不影响发布）："+str(error)[:160])
        if not args.no_publish:
            commit=publish(ROOT,"每日目录更新 "+stamp())
            log("新版推送成功："+commit)
        log("=== 每日目录完成 ===")
    except Exception as error:
        (ROOT/"data/review/last_error.json").write_text(json.dumps({"time":stamp(),"error":str(error)},ensure_ascii=False),encoding="utf-8")
        log("FAILED: "+str(error))
        raise


if __name__=="__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8",errors="replace")
    except AttributeError:
        pass
    main()
