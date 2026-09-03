# -*- coding: utf-8 -*-
"""相关推荐右栏卡片数据（零请求）——供人工核对。"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fav_mine")

for bv, label in (("BV1Zx7B6DE6w", "哈基米"), ("BV1cBtc65EQc", "养生")):
    d = json.load(open(os.path.join(MINE, f"related_{bv}.json"), encoding="utf-8"))
    rows = sorted(d["rows"], key=lambda r: -r["view"])[:8]
    n = len(rows)
    print(f"{label}: {n} 条")
    for i, r in enumerate(rows, 1):
        print(json.dumps({"i": i, "v": r["view"], "dur": r["dur"], "coin": round(r["coin_rate"] * 100, 3),
                          "t": r["title"]}, ensure_ascii=False))
