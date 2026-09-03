# -*- coding: utf-8 -*-
"""种子→mid 预热（2026-09-03 晨）：以 1.2s 慢速把 sample_*.json 全部 bvid 解析为
uploader mid，写入 data/fav_mine/.seedmap.json——让 fav_miner 的种子阶段零请求冷启动。

增量落盘（每 20 个）、失败跳过（挖掘时按需补解析）、不碰账号。
用法： python engine/warm_seeds.py
"""
import json
import os
import re
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient, UA  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDIR = os.path.join(ROOT, "data", "samples")
OUT = os.path.join(ROOT, "data", "fav_mine", ".seedmap.json")


def main():
    cli = BiliClient(interval=1.2)
    try:
        req = urllib.request.Request("https://www.bilibili.com/", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            for sc in (resp.headers.get_all("Set-Cookie") or []):
                m = re.match(r"([^=]+)=([^;]*)", sc)
                if m:
                    cli.cookies[m.group(1)] = m.group(2)
        print(f"[warm] warmup OK: {', '.join(cli.cookies.keys()) or 'none'}")
    except Exception as e:
        print(f"[warm] warmup failed: {e}")

    seedmap = {}
    if os.path.exists(OUT):
        try:
            seedmap = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            seedmap = {}

    bvids = []
    seen = set()
    for fn in sorted(os.listdir(SDIR)):
        if fn.startswith("sample_") and fn.endswith(".json"):
            try:
                for v in json.load(open(os.path.join(SDIR, fn), encoding="utf-8")).get("videos") or []:
                    bv = v.get("bvid")
                    if bv and bv not in seen:
                        seen.add(bv)
                        bvids.append(bv)
            except Exception:
                continue
    todo = [b for b in bvids if not seedmap.get(b)]
    print(f"[warm] 样本 bvid {len(bvids)}，缓存已有 {len(bvids) - len(todo)}，待解析 {len(todo)}")

    done = fails = 0
    for i, bv in enumerate(todo, 1):
        try:
            v = cli.fetch_view(bv)
            mid = v.get("owner_mid")
            if mid:
                seedmap[bv] = mid
                done += 1
        except Exception as e:
            fails += 1
            print(f"[warm] {bv} failed: {e}")
        if done % 20 == 0 and done:
            json.dump(seedmap, open(OUT, "w", encoding="utf-8"))
            print(f"[warm] {i}/{len(todo)} resolved（checkpoint {len(seedmap)}）")
    json.dump(seedmap, open(OUT, "w", encoding="utf-8"))
    print(f"[warm] 完成：新增 {done}，失败 {fails}，缓存总量 {len(seedmap)} → {OUT}")


if __name__ == "__main__":
    main()
