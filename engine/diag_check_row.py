# -*- coding: utf-8 -*-
"""精确检查指定 bvid 在货架 DATA 里的完整行。"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
c = open(os.path.join(ROOT, "docs", "god-shelf.html"), encoding="utf-8").read()
i = c.find("const DATA = ")
j = c.find("{", i)
depth, k, in_str, esc2 = 0, j, False, False
while k < len(c):
    ch = c[k]
    if in_str:
        if esc2:
            esc2 = False
        elif ch == "\\":
            esc2 = True
        elif ch == '"':
            in_str = False
    else:
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
    k += 1
D = json.loads(c[j:k + 1])
targets = sys.argv[1:] or ["BV1Z6th6WEq6"]
for t in targets:
    row = next((r for r in D["rows"] if r.get("bvid") == t), None)
    if row:
        print(json.dumps(row, ensure_ascii=False, indent=1))
    else:
        print(f"{t}: 不在 DATA.rows")
