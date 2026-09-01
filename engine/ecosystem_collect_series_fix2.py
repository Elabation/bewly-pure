# -*- coding: utf-8 -*-
"""series 补采 v2：等距抽样 + 批间休眠 + 增量写盘
策略：缺失期号等距取 ~180 期（覆盖 2020-2026），每 12 期休眠 35s 躲风控窗口，
     每 36 期写盘一次（防会话中断丢数据）。
用法： python engine/ecosystem_collect_series_fix2.py <v5样本路径>
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
OUT = SRC.replace(".json", "_fix.json") if SRC else None
BATCH = 12        # 每批期数
BATCH_SLEEP = 35  # 批间休眠
SAVE_EVERY = 36   # 每 N 期写盘


def save(videos, meta):
    meta["count"] = len(videos)
    by = {}
    for v in videos:
        k = v["source"].split(":")[0]
        by[k] = by.get(k, 0) + 1
    meta["by_layer"] = by
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "videos": videos}, f, ensure_ascii=False, indent=1)


def main():
    with open(SRC, encoding="utf-8") as f:
        payload = json.load(f)
    videos = payload["videos"]
    meta = payload["meta"]
    have_bv = {v["bvid"] for v in videos if v.get("bvid")}
    have_eps = set()
    for v in videos:
        m = re.search(r"第(\d+)期", v["source"] or "")
        if v["source"].startswith("series:") and m:
            have_eps.add(int(m.group(1)))

    cli = BiliClient(interval=0.5)
    try:
        req = urllib.request.Request("https://www.bilibili.com/", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            for sc in (resp.headers.get_all("Set-Cookie") or []):
                m = re.match(r"([^=]+)=([^;]*)", sc)
                if m:
                    cli.cookies[m.group(1)] = m.group(2)
    except Exception as e:
        print("[cookie] failed:", e)

    seasons = cli.get_json("https://api.bilibili.com/x/web-interface/popular/series/list")
    missing = [s["number"] for s in seasons.get("list", []) if s["number"] not in have_eps]
    step = max(1, len(missing) // 180)
    todo = missing[::step]
    print(f"[series] 缺失 {len(missing)} 期 → 等距采样 {len(todo)} 期")

    added, fails = 0, 0
    t0 = time.time()
    for i, num in enumerate(todo, 1):
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/popular/series/one",
                             {"number": num})
            for it in d.get("list") or []:
                bv = it.get("bvid")
                if bv and bv not in have_bv:
                    have_bv.add(bv)
                    name = next((s["name"] for s in seasons["list"] if s["number"] == num), f"第{num}期")
                    videos.append(norm_item(it, f"series:{name}"))
                    added += 1
        except Exception as e:
            fails += 1
            if fails <= 6:
                print(f"[series] 期{num} fail: {str(e)[:60]}")
            time.sleep(20)
        if i % BATCH == 0:
            print(f"[progress] {i}/{len(todo)} +{added} fails={fails} {time.time()-t0:.0f}s")
            time.sleep(BATCH_SLEEP)
        if i % SAVE_EVERY == 0:
            save(videos, meta)
            print(f"[save] {len(videos)} 条")

    save(videos, meta)
    print(f"[done] +{added} 条（失败 {fails} 期）-> {OUT}")
    print("[by_layer]", json.dumps(meta["by_layer"], ensure_ascii=False))


if __name__ == "__main__":
    main()
