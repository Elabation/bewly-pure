# -*- coding: utf-8 -*-
"""series 补丁：重采每周必看缺失期（v5 采集时 370 期被 -352 风控吞掉）
修复点：① allow_codes 不再放行 -352（让 BiliClient 退避重试生效）
        ② 节流 0.9s + 每 30 期休眠 4s + 单期失败休眠 8s
用法： python engine/ecosystem_collect_series_fix.py <v5样本路径>
"""
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient, UA  # noqa: E402
from ecosystem_collect_v5 import norm_item  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

SRC = sys.argv[1] if len(sys.argv) > 1 else None


def main():
    with open(SRC, encoding="utf-8") as f:
        payload = json.load(f)
    videos = payload["videos"]
    have_eps = set()
    have_bv = {v["bvid"] for v in videos if v.get("bvid")}
    for v in videos:
        m = re.search(r"第(\d+)期", v["source"] or "")
        if v["source"].startswith("series:") and m:
            have_eps.add(int(m.group(1)))
    print(f"[load] 已有 {len(videos)} 条，已采期号 {len(have_eps)} 个")

    cli = BiliClient(interval=0.9)
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

    seasons = cli.get_json("https://api.bilibili.com/x/web-interface/popular/series/list")
    todo = [s for s in seasons.get("list", []) if s["number"] not in have_eps]
    print(f"[series] 待补 {len(todo)} 期")
    added, still_fail = 0, []
    t0 = time.time()
    for i, s in enumerate(todo, 1):
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/popular/series/one",
                             {"number": s["number"]})
            items = d.get("list") or []
            for it in items:
                bv = it.get("bvid")
                if bv and bv not in have_bv:
                    have_bv.add(bv)
                    videos.append(norm_item(it, f"series:{s['name']}"))
                    added += 1
        except Exception as e:
            still_fail.append(s["number"])
            if len(still_fail) <= 8:
                print(f"[series] 期{s['number']} fail: {e}")
            time.sleep(8)
        if i % 30 == 0:
            print(f"[progress] {i}/{len(todo)} 期，+{added} 条，失败 {len(still_fail)}，elapsed {time.time()-t0:.0f}s")
            time.sleep(4)

    payload["videos"] = videos
    payload["meta"]["count"] = len(videos)
    by = {}
    for v in videos:
        key = v["source"].split(":")[0]
        by[key] = by.get(key, 0) + 1
    payload["meta"]["by_layer"] = by
    out = SRC.replace(".json", "_fix.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"[done] +{added} 条（仍失败 {len(still_fail)} 期）-> {out}")
    print("[by_layer]", json.dumps(by, ensure_ascii=False))


if __name__ == "__main__":
    main()
