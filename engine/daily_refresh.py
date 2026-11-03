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


def collect(client, pages=10, seeds=8):
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
    fresh = set(videos) - known
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
        write_capture(graphs/("godflowdaily_"+stamp()+".json"),{"meta":{"src":"daily-v6","requests":{"related":len(choices)}},"flows":[{"nodes":nodes}]})
    return {"finished_at":stamp(),"popular_videos":len(rows),"new_videos":len(fresh),
            "related_nodes":len(nodes),"related_requests_succeeded":related_ok,"popular_pages_failed":len(failures)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--no-publish",action="store_true")
    parser.add_argument("--build-only",action="store_true")
    args=parser.parse_args()
    status_path=ROOT/"data/review/last_success.json"
    status_path.parent.mkdir(parents=True,exist_ok=True)
    log("=== 每日目录 v6 开始 ===")
    try:
        if not args.build_only:
            result=collect(BiliClient(interval=.8))
            status_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
            log("采集成功："+json.dumps(result,ensure_ascii=False))
        summary=rebuild(ROOT)
        log("轻量新版生成："+json.dumps(summary,ensure_ascii=False))
        if not args.no_publish:
            commit=publish(ROOT,"每日目录更新 "+stamp())
            log("新版推送成功："+commit)
        log("=== 每日目录 v6 完成 ===")
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
