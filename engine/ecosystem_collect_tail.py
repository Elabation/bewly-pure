# -*- coding: utf-8 -*-
"""长尾补采：分区最新视频的深页（投稿数天~数周、播放已沉淀的成熟低热度视频）。
修复「newlist 第1页=刚投稿，播放低是时间混淆」的方法学问题。
用法： python engine/ecosystem_collect_tail.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402
import ecosystem_collect as ec  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SRC = os.path.join(ROOT, "data", "samples", "ecosystem_20260901_1910.json")
# newlist 可用的12个内容区（首次采集中返回非空的）
ZONES_OK = [1, 3, 4, 5, 36, 129, 155, 160, 181, 188, 202, 211]
PAGES = (8, 25)


def main():
    with open(SRC, encoding="utf-8") as f:
        payload = json.load(f)
    videos = payload["videos"]
    have = {v["bvid"] for v in videos if v.get("bvid")}
    cli = BiliClient(interval=0.4)
    added = 0

    for rid in ZONES_OK:
        name = ec.ZONES.get(rid, str(rid))
        for pn in PAGES:
            try:
                data = cli.get_json("https://api.bilibili.com/x/web-interface/newlist",
                                    {"rid": rid, "ps": 50, "pn": pn})
                archives = data.get("archives") or []
                n0 = added
                for it in archives:
                    item = ec.from_item(it, f"newlist:{name}")
                    if item["bvid"] and item["bvid"] not in have:
                        videos.append(item)
                        have.add(item["bvid"])
                        added += 1
                print(f"[tail] {name} pn={pn}: +{added - n0}")
            except Exception as e:
                print(f"[tail] {name} pn={pn} failed: {e}")

    broken = [v for v in videos if not v.get("stat_raw_ok") and v["source"].startswith("newlist")]
    for v in broken[:400]:
        try:
            full = cli.fetch_view(v["bvid"])
            v.update({k: full[k] for k in ("title", "tname", "owner", "pubdate",
                                           "duration", "dimension", "stat")})
            v["stat_raw_ok"] = True
        except Exception:
            pass
    print(f"[enrich] 补全 {min(len(broken), 400)}/{len(broken)}")

    payload["videos"] = videos
    payload["meta"]["count"] = len(videos)
    payload["meta"]["by_layer"]["newlist"] = sum(1 for v in videos if v["source"].startswith("newlist"))
    payload["meta"]["note"] = "三层生态样本 v2：newlist 深页(pn=8/25)修复时间混淆；仅API元数据"
    out = SRC.replace(".json", "_v2.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"[done] {len(videos)} -> {out}")


if __name__ == "__main__":
    main()
