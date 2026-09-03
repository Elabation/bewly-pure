# -*- coding: utf-8 -*-
"""related 邻域与参照库的重叠度（零请求）——量化图遍历的净增效率。"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")

db = set()
for fn in ("sample_20260903_185231.json", "sample_20260903_203054.json"):
    try:
        p = json.load(open(os.path.join(SDIR, fn), encoding="utf-8"))
    except Exception:
        continue
    for v in (p.get("videos") or []):
        if v.get("bvid"):
            db.add(v["bvid"])
for fn in os.listdir(MINE):
    if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
        try:
            p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            if v.get("bvid"):
                db.add(v["bvid"])
print(f"参照库 bvid 总量（不过滤播放）: {len(db)}")
for bv in ("BV1Zx7B6DE6w", "BV1cBtc65EQc"):
    d = json.load(open(os.path.join(MINE, f"related_{bv}.json"), encoding="utf-8"))
    rows = d["rows"]
    new = [r for r in rows if r["bvid"] not in db]
    mid = sum(1 for r in new if r["view"] >= 3000)
    print(f"{bv}: 邻居 {len(rows)} 条 → 新面孔 {len(new)}（view>=3000 的 {mid}）→ 净增率 {len(new)/len(rows):.0%}")
