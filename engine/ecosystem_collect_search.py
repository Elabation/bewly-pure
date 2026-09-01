# -*- coding: utf-8 -*-
"""成熟长尾补采 v2：搜索接口按播放量降序取深页（各分区第~1500名开外）。
newlist 翻页在B站日投稿体量下只够到几天内的新稿，无法构成「不火的成熟视频」样本。
搜索深页的视频投稿已久、播放已沉淀，是「高质量但不火」问题的正确地层。
用法： python engine/ecosystem_collect_search.py
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
SRC = os.path.join(ROOT, "data", "samples", "ecosystem_20260901_1910_v2.json")
ZONES = {4: "游戏", 36: "知识", 160: "生活", 211: "美食", 3: "音乐",
         188: "科技", 1: "动画", 181: "影视"}
PAGE = 40  # 按播放量降序第 40 页 ≈ 分区第 1500 名开外


def main():
    with open(SRC, encoding="utf-8") as f:
        payload = json.load(f)
    videos = payload["videos"]
    have = {v["bvid"] for v in videos if v.get("bvid")}
    cli = BiliClient(interval=0.4)
    added_items = []

    for rid, name in ZONES.items():
        got = 0
        for kw in ("", " "):
            try:
                data = cli.get_json(
                    "https://api.bilibili.com/x/web-interface/wbi/search/type",
                    {"search_type": "video", "order": "click", "tids": rid,
                     "page": PAGE, "page_size": 30, "keyword": kw}, sign_wbi=True)
                result = data.get("result") or []
                for it in result:
                    if it.get("bvid") and it["bvid"] not in have:
                        item = {
                            "bvid": it["bvid"], "title": it.get("title"),
                            "tname": it.get("typename") or name,
                            "owner": it.get("author"), "pubdate": it.get("pubdate"),
                            "duration": None, "dimension": {}, "stat": {},
                            "stat_raw_ok": False, "source": f"tailsearch:{name}",
                        }
                        videos.append(item)
                        have.add(item["bvid"])
                        added_items.append(item)
                        got += 1
                if result:
                    break
            except Exception as e:
                print(f"[search] {name} kw={kw!r} failed: {e}")
        print(f"[search] {name} 深页第{PAGE}页: +{got}")

    ok = 0
    for v in added_items:
        try:
            full = cli.fetch_view(v["bvid"])
            v.update({k: full[k] for k in ("title", "tname", "owner", "pubdate",
                                           "duration", "dimension", "stat")})
            v["stat_raw_ok"] = True
            ok += 1
        except Exception as e:
            print(f"[enrich] {v['bvid']} failed: {e}")
    print(f"[enrich] 尾部补全 {ok}/{len(added_items)}")

    payload["videos"] = videos
    payload["meta"]["count"] = len(videos)
    payload["meta"]["by_layer"]["tailsearch"] = len(added_items)
    payload["meta"]["note"] = ("三层+1层生态样本 v3：newlist 深页修复时间混淆后，"
                               "再加 search 按播放量降序深页=成熟中长尾；仅API元数据")
    out = SRC.replace("_v2.json", "_v3.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"[done] {len(videos)} -> {out}")


if __name__ == "__main__":
    main()
