"""Daily collection -> lightweight Bocchi discovery -> existing GitHub Pages URL.

API failures and publishing failures are nonzero exits. Raw captures are append-only.
"""
from pathlib import Path
import argparse
import json
import sys
from datetime import datetime, timedelta

from collect_stats import BiliClient
from mining_data import load_population, load_flow_nodes, normalize_video
from review_miner import catalog
from publish_discovery import rebuild, publish

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


def collect(client, pages=10, seeds=8, auth_client=None, feed_pages=0, rids=()):
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
    fresh = (set(videos) | set(ranking_videos) | set(feed_videos)) - known
    log("首页有效 {} 条，首次发现 {} 条。".format(len(rows), len(fresh)))
    pool, meta = catalog(ROOT)
    choices = sorted([r for r in pool if r["bvid"] in videos and not r.get("motive_cues") and not r.get("screen_flags") and r.get("dur",0)>150
                      and r.get("reference_n",0)>=30 and r.get("recall_priority") is not None],
                     key=lambda r:r["recall_priority"], reverse=True)[:seeds]
    nodes, seen, related_ok = [], set(), 0
    for candidate in choices:
        source = videos[candidate["bvid"]]
        aid = source.get("aid")
        if not aid:
            continue
        try:
            items = client.get_json("https://api.bilibili.com/x/web-interface/archive/related", {"aid":aid}, tries=1)
            related_ok += 1
        except Exception as error:
            log("related {} failed: {}".format(candidate["bvid"], str(error)[:100]))
            continue
        for video in items if isinstance(items, list) else []:
            rec = normalize_video(video, "related")
            if not rec or rec["bvid"] in seen or rec["view"]<=0:
                continue
            seen.add(rec["bvid"])
            nodes.append({"bvid":rec["bvid"],"title":rec["title"],"view":rec["view"],"dur":rec["dur"],
                          "coin_rate":rec["coin"]/rec["view"],"fav_rate":rec["fav"]/rec["view"],
                          "like_rate":rec["like"]/rec["view"],"stat":video["stat"],"pubdate":rec["pubdate"],
                          "owner":video.get("owner"),"pic":rec["pic"],"parent":candidate["bvid"],"arm":"daily"})
    if nodes:
        write_capture(graphs/("godflowdaily_"+stamp()+".json"),{"meta":{"src":"daily","requests":{"related":len(choices)}},"flows":[{"nodes":nodes}]})
    return {"finished_at":stamp(),"popular_videos":len(rows),"new_videos":len(fresh),
            "related_nodes":len(nodes),"related_requests_succeeded":related_ok,"popular_pages_failed":len(failures),
            "ranking_videos":ranking_written,"ranking_partitions_ok":ranking_ok,"ranking_partitions_failed":ranking_failed,
            "homefeed_videos":len(feed_videos),"homefeed_pages_failed":feed_failed}


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
            result=collect(BiliClient(interval=.8), rids=RANK_RIDS, auth_client=auth, feed_pages=FEED_PAGES if auth else 0)
            status_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
            log("采集成功："+json.dumps(result,ensure_ascii=False))
        summary=rebuild(ROOT)
        log("轻量新版生成："+json.dumps(summary,ensure_ascii=False))
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
