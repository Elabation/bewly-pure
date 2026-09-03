# -*- coding: utf-8 -*-
"""打印相关推荐邻域前 N 条（零请求）——模拟视频页右栏。"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fav_mine")
N = 12


def fmt_view(m):
    return f"{m / 10000:.1f}万" if m >= 10000 else f"{m:,}"


for bv in ("BV1Zx7B6DE6w", "BV1cBtc65EQc"):
    d = json.load(open(os.path.join(MINE, f"related_{bv}.json"), encoding="utf-8"))
    rows = sorted(d["rows"], key=lambda r: -r["view"])[:N]
    print(f"=== {bv} 点进去的右栏（相关推荐 {d['n_related']} 条，按播放取前 {N}） ===")
    for i, r in enumerate(rows, 1):
        print(f"{i:>2}. [{fmt_view(r['view'])}] {r['dur']}s 币率{r['coin_rate']:.3%} {r['title']}")
    print()
