# -*- coding: utf-8 -*-
"""构建报告网页：把分析 JSON 注入 HTML（幂等：占位态/已注入态均可）。
用法： python engine/build_report.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "web", "ecosystem-report.html")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

deep = json.load(open(os.path.join(ROOT, "data", "analysis", "deep_summary.json"), encoding="utf-8"))
eco = json.load(open(os.path.join(ROOT, "data", "analysis", "ecosystem_summary.json"), encoding="utf-8"))
deep["fire_but_cold"] = eco.get("fire_but_cold", {"n": 0, "n_hot": 1, "examples": []})
deep["gems"] = eco.get("gems", {"n": 0, "n_tail": 1, "examples": []})
deep_js = json.dumps(deep, ensure_ascii=False)
points_js = json.dumps(eco["points"], ensure_ascii=False)

lines = open(HTML, encoding="utf-8").read().split("\n")
hit_deep = hit_pts = False
for i, ln in enumerate(lines):
    if ln.startswith("const DEEP = "):
        lines[i] = "const DEEP = " + deep_js + ";"
        hit_deep = True
    elif ln.startswith("const POINTS = "):
        lines[i] = "const POINTS = " + points_js + ";"
        hit_pts = True
if not (hit_deep and hit_pts):
    raise SystemExit("未找到 const DEEP / const POINTS 行")
open(HTML, "w", encoding="utf-8").write("\n".join(lines))
print(f"[done] DEEP {len(deep_js)}B · POINTS {len(points_js)}B -> {HTML}")
