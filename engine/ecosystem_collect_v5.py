# -*- coding: utf-8 -*-
"""大采样 v5：10 倍扩样 + 时间跨度 2020-2026
来源：
  series    每周必看 387 期（2020-2026，自带 stat，~15000 条）← 时间维度主力
  precious  入站必刷 98 条（历史经典，自带 stat）
  popular   热门 pn1-20（自带 stat）
  ranking   全站+16分区榜单（自带 stat）
  feed      未登录推荐流 40 页（enrich）
  newlist   全主分区最新 pn1（enrich）
用法： python engine/ecosystem_collect_v5.py
"""
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient, UA  # noqa: E402
from ecosystem_collect import ZONES  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAT_KEYS = ("view", "danmaku", "reply", "favorite", "coin", "share", "like")


def norm_item(it, source):
    st = it.get("stat") or {}
    dim = it.get("dimension") or {}
    return {
        "bvid": it.get("bvid"), "aid": it.get("aid"),
        "title": it.get("title"), "tname": it.get("tname"),
        "owner": (it.get("owner") or {}).get("name") if isinstance(it.get("owner"), dict) else it.get("owner"),
        "pubdate": it.get("pubdate"), "duration": it.get("duration"),
        "dimension": {"width": dim.get("width"), "height": dim.get("height"),
                      "rotate": dim.get("rotate", 0)},
        "stat": {k: st.get(k) for k in STAT_KEYS},
        "stat_raw_ok": bool(st.get("view") and st.get("like") is not None and st.get("coin") is not None),
        "source": source,
    }


def main():
    cli = BiliClient(interval=0.45)
    try:
        req = urllib.request.Request("https://www.bilibili.com/", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            for sc in (resp.headers.get_all("Set-Cookie") or []):
                m = re.match(r"([^=]+)=([^;]*)", sc)
                if m:
                    cli.cookies[m.group(1)] = m.group(2)
        print("[cookie]", list(cli.cookies.keys()))
    except Exception as e:
        print("[cookie] failed:", e)

    videos, have = [], set()

    def push(it, source):
        bv = it.get("bvid")
        if not bv or bv in have:
            return
        have.add(bv)
        videos.append(norm_item(it, source))

    # ---------- ① 每周必看（时间主力） ----------
    n0 = len(videos)
    try:
        seasons = cli.get_json("https://api.bilibili.com/x/web-interface/popular/series/list")
        nums = seasons.get("list", [])
        print(f"[series] {len(nums)} 期")
        fails = 0
        for s in nums:
            num = s["number"]
            try:
                d = cli.get_json("https://api.bilibili.com/x/web-interface/popular/series/one",
                                 {"number": num}, allow_codes=(-352,))
                for it in d.get("list") or []:
                    push(it, f"series:{s['name']}")
            except Exception as e:
                fails += 1
                if fails <= 5:
                    print(f"[series] 期{num} failed: {e}")
        print(f"[series] +{len(videos) - n0} (fails={fails})")
    except Exception as e:
        print(f"[series] LIST failed: {e}")

    # ---------- ② 入站必刷 ----------
    n0 = len(videos)
    try:
        d = cli.get_json("https://api.bilibili.com/x/web-interface/popular/precious")
        for it in d.get("list") or []:
            push(it, "precious")
        print(f"[precious] +{len(videos) - n0}")
    except Exception as e:
        print(f"[precious] failed: {e}")

    # ---------- ③ 热门深页 ----------
    n0 = len(videos)
    try:
        for pn in range(1, 21):
            d = cli.get_json("https://api.bilibili.com/x/web-interface/popular",
                             {"ps": 20, "pn": pn}, sign_wbi=True)
            for it in d.get("list") or []:
                push(it, "popular")
        print(f"[popular] +{len(videos) - n0}")
    except Exception as e:
        print(f"[popular] failed: {e}")

    # ---------- ④ 榜单 ----------
    n0 = len(videos)
    try:
        d = cli.get_json("https://api.bilibili.com/x/web-interface/ranking/v2",
                         {"rid": 0, "type": "all"})
        for it in d.get("list") or []:
            push(it, "ranking:全站")
        for rid, zname in ZONES.items():
            try:
                d = cli.get_json("https://api.bilibili.com/x/web-interface/ranking/v2",
                                 {"rid": rid, "type": "all"}, allow_codes=(-400,))
                for it in d.get("list") or []:
                    push(it, f"ranking:{zname}")
            except Exception:
                pass
        print(f"[ranking] +{len(videos) - n0}")
    except Exception as e:
        print(f"[ranking] failed: {e}")

    # ---------- ⑤ 推荐流（enrich） ----------
    feed_bvs = []
    try:
        for idx in range(1, 41):
            d = cli.get_json("https://api.bilibili.com/x/web-interface/index/top/feed/rcmd",
                             {"ps": 12, "fresh_idx": idx, "fresh_idx_1h": idx,
                              "fresh_idx_4h": idx, "fresh_idx_5d": idx}, sign_wbi=True)
            for it in d.get("item") or []:
                if it.get("goto") == "av" and it.get("bvid") and it["bvid"] not in have:
                    have.add(it["bvid"])
                    feed_bvs.append(it["bvid"])
        print(f"[feed] {len(feed_bvs)} 条待补全")
    except Exception as e:
        print(f"[feed] rcmd failed: {e}")
    ok = 0
    for bv in feed_bvs:
        try:
            v = cli.fetch_view(bv)
            v["source"] = "feed"
            v["stat_raw_ok"] = True
            videos.append(v)
            ok += 1
        except Exception:
            pass
    print(f"[feed] 补全 {ok}/{len(feed_bvs)}")

    # ---------- ⑥ 分区新稿（enrich，pn1） ----------
    new_bvs = []
    try:
        for rid, zname in ZONES.items():
            try:
                d = cli.get_json("https://api.bilibili.com/x/web-interface/newlist",
                                 {"rid": rid, "ps": 50, "pn": 1}, allow_codes=(-400,))
                for it in d.get("archives") or []:
                    if it.get("bvid") and it["bvid"] not in have:
                        have.add(it["bvid"])
                        new_bvs.append((it["bvid"], zname))
            except Exception:
                pass
        print(f"[newlist] {len(new_bvs)} 条待补全")
    except Exception as e:
        print(f"[newlist] failed: {e}")
    ok = 0
    for bv, zname in new_bvs:
        try:
            v = cli.fetch_view(bv)
            v["source"] = f"newlist:{zname}"
            v["stat_raw_ok"] = True
            videos.append(v)
            ok += 1
        except Exception:
            pass
    print(f"[newlist] 补全 {ok}/{len(new_bvs)}")

    by = {}
    for v in videos:
        key = v["source"].split(":")[0]
        by[key] = by.get(key, 0) + 1
    payload = {
        "meta": {
            "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(videos), "by_layer": by,
            "note": ("大采样 v5：每周必看387期(2020-2026时间主力)/入站必刷/热门深页/榜单/推荐流/分区新稿；"
                     "仅API元数据，未下载任何视频"),
        },
        "videos": videos,
    }
    out = os.path.join(ROOT, "data", "samples", f"ecosystem_v5_{time.strftime('%Y%m%d_%H%M')}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"[done] {len(videos)} 条 -> {out}")
    print("[by_layer]", json.dumps(by, ensure_ascii=False))


if __name__ == "__main__":
    main()
