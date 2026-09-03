# -*- coding: utf-8 -*-
"""gold 候选入度速查（中带实验后的新状态）"""
import json
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fav_mine")
KW = ["美女", "小姐姐", "擦边", "颜值", "热舞", "宅舞", "跳舞", "黑丝", "JK", "jk", "制服",
      "性感", "变装", "女团", "cos", "Cos", "COS", "纯欲", "身材", "御姐", "妹子", "舞蹈", "卡点舞"]

inflow = defaultdict(set)
rec = {}
for fn in os.listdir(MINE):
    if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
        try:
            p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            if (v.get("view") or 0) >= 3000 and v.get("from_user") and v.get("bvid"):
                inflow[v["bvid"]].add(v["from_user"])
                rec[v["bvid"]] = v

gold = [(b, v, len(inflow[b])) for b, v in rec.items()
        if v.get("tier") == "high" and any(k in (v.get("title") or "") for k in KW)]
gold.sort(key=lambda x: -(x[1].get("cbi") or 0))
for b, v, k in gold:
    print(f"CBI {round(v.get('cbi', 0), 2)} 入度{k} {v.get('title', '')[:38]}")
