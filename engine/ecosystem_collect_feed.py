# -*- coding: utf-8 -*-
"""数据增厚（最后一轮）：
  ① 推荐流层做厚：fresh_idx 1..30 → 未登录首页真实投喂层（含大量 1k-50w 播放的中长尾）
  ② 搜索深页重试：真实关键词 + 按播放量降序（上一轮空关键词/空格被 -400/-1200 拒绝）
用法： python engine/ecosystem_collect_feed.py
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
SRC = os.path.join(ROOT, "data", "samples", "ecosystem_20260901_1910_v3.json")
SEARCH_ZONES = {4: "游戏", 36: "知识", 160: "生活", 211: "美食", 3: "音乐",
                188: "科技", 1: "动画", 181: "影视"}
PAGE = 40


def main():
    with open(SRC, encoding="utf-8") as f:
        payload = json.load(f)
    videos = payload["videos"]
    have = {v["bvid"] for v in videos if v.get("bvid")}
    cli = BiliClient(interval=0.4)

    # ---------- ① feed 层做厚 ----------
    feed_bvs = []
    try:
        for idx in range(1, 31):
            data = cli.get_json(
                "https://api.bilibili.com/x/web-interface/index/top/feed/rcmd",
                {"ps": 12, "fresh_idx": idx, "fresh_idx_1h": idx,
                 "fresh_idx_4h": idx, "fresh_idx_5d": idx}, sign_wbi=True)
            for it in (data.get("item") or []):
                if it.get("goto") == "av" and it.get("bvid"):
                    feed_bvs.append(it["bvid"])
    except Exception as e:
        print(f"[feed] rcmd stopped: {e}")
    feed_new = []
    for bv in feed_bvs:
        if bv not in have:
            have.add(bv)
            feed_new.append(bv)
    print(f"[feed] rcmd {len(feed_bvs)} 条，新增 {len(feed_new)}")

    ok = 0
    for bv in feed_new:
        try:
            v = cli.fetch_view(bv)
            v["source"] = "feed"
            v["stat_raw_ok"] = True
            videos.append(v)
            ok += 1
        except Exception as e:
            print(f"[feed] {bv} enrich failed: {e}")
    print(f"[feed] 补全 {ok}/{len(feed_new)}")

    # ---------- ② 搜索深页重试（真实关键词） ----------
    search_added = []
    for rid, name in SEARCH_ZONES.items():
        try:
            data = cli.get_json(
                "https://api.bilibili.com/x/web-interface/wbi/search/type",
                {"search_type": "video", "order": "click", "tids": rid,
                 "page": PAGE, "page_size": 30, "keyword": name}, sign_wbi=True)
            result = data.get("result") or []
            got = 0
            for it in result:
                if it.get("bvid") and it["bvid"] not in have:
                    have.add(it["bvid"])
                    item = {"bvid": it["bvid"], "title": it.get("title"),
                            "tname": it.get("typename") or name, "owner": it.get("author"),
                            "pubdate": it.get("pubdate"), "duration": None,
                            "dimension": {}, "stat": {}, "stat_raw_ok": False,
                            "source": f"tailsearch:{name}"}
                    videos.append(item)
                    search_added.append(item)
                    got += 1
            print(f"[search] {name} 深页: +{got}")
        except Exception as e:
            print(f"[search] {name} failed: {e}")

    ok = 0
    for v in search_added:
        try:
            full = cli.fetch_view(v["bvid"])
            v.update({k: full[k] for k in ("title", "tname", "owner", "pubdate",
                                           "duration", "dimension", "stat")})
            v["stat_raw_ok"] = True
            ok += 1
        except Exception:
            pass
    print(f"[search] 补全 {ok}/{len(search_added)}")

    payload["videos"] = videos
    payload["meta"]["count"] = len(videos)
    by = {}
    for v in videos:
        key = v["source"].split(":")[0]
        by[key] = by.get(key, 0) + 1
    payload["meta"]["by_layer"] = by
    payload["meta"]["note"] = ("生态样本 v4（最终）：榜单火/热门/推荐流(360页厚采样)/newlist深页/"
                               "搜索深页(风控受限)；仅API元数据，不下载视频")
    out = SRC.replace("_v3.json", "_v4.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"[done] {len(videos)} -> {out}")


if __name__ == "__main__":
    main()
