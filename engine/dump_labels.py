# -*- coding: utf-8 -*-
"""95 条判定全文导出（逐条、含元数据）"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fav_mine")
d = json.load(open(os.path.join(MINE, "elabation_flow_labels.json"), encoding="utf-8"))
lines = []
for j in d["labels"]:
    lines.append(f"#{j['rank']:>3} CBI{j['cbi']:>6.2f} 汇流{j['inflow']} [{j['prov']}] "
                 f"{j['bvid']} 「{j['verdict']}」")
txt = "\n".join(lines)
open(os.path.join(MINE, "labels_fulltext.txt"), "w", encoding="utf-8").write(txt)
print(f"[done] {len(lines)} 条 -> labels_fulltext.txt")
