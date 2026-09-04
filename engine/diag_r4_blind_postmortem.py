# -*- coding: utf-8 -*-
"""R4 盲测第二轮 · 验尸：细胞判定对账 + 假设死因分析。"""
import json
import os
import sys
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
DATE = "20260905"

cards = {c["bvid"]: c for c in json.load(open(os.path.join(MINE, f"r4_blindhunt_{DATE}.json"), encoding="utf-8"))["cards"]}
jud = json.load(open(r"C:\Users\33768\Desktop\r4_blind_review_judged_2026-09-05.json", encoding="utf-8"))["judgments"]

CELL_LBL = {"A": "触发·短≤21s", "B": "触发·中22~45s", "C": "触发·长>45s",
            "D": "高带低诚sinc≤0.11", "E": "高带边界0.11~0.20", "F": "低带边缘NM-A", "G": "随机对照"}

print("=== 细胞 × 判定 对账 ===")
xt = defaultdict(Counter)
for b, j in jud.items():
    c = cards.get(b)
    if c:
        xt[c["cell"]][j["v"]] += 1
for k in "ABCDEFG":
    t = xt[k]
    n = sum(t.values())
    print(f"  {k} {CELL_LBL[k]}: n={n} 软擦边{t.get('软擦边', 0)} 无辜{t.get('无辜', 0)} 存疑{t.get('存疑', 0)}")

print("\n=== 假设计分板 ===")
a_edge = xt["A"].get("软擦边", 0) / max(1, sum(xt["A"].values()))
c_innocent = xt["C"].get("无辜", 0) / max(1, sum(xt["C"].values()))
d_edge = xt["D"].get("软擦边", 0) / max(1, sum(xt["D"].values()))
g_edge = xt["G"].get("软擦边", 0) / max(1, sum(xt["G"].values()))
print(f"  H1 短时长=擦边:   A细胞擦边率 {a_edge:.0%}（第一轮 10/10）")
print(f"  H2 长时长=无辜:   C细胞无辜率 {c_innocent:.0%}（第一轮 4/4）")
print(f"  H3 高带sinc=擦边: D细胞擦边率 {d_edge:.0%}（第一轮 12/12）")
print(f"  基线:             G细胞擦边率 {g_edge:.0%}")
fires_cells = Counter()
for k in ("A", "B", "C"):
    fires_cells.update(xt[k])
fn = sum(fires_cells.values())
print(f"  R4 触发总体精确率: {fires_cells.get('软擦边', 0)}/{fn} = {fires_cells.get('软擦边', 0) / max(1, fn):.0%}（第一轮 56%）")

print("\n=== D 细胞死因排查 · 发布年代分布 ===")
ds = [c for c in cards.values() if c["cell"] == "D"]
years = sorted(c["pub"][:4] for c in ds if c["pub"] != "—")
print(f"  年份分布: {dict(Counter(years))}")
old = sum(1 for y in years if y < "2018")
print(f"  2018年前: {old}/{len(ds)}")
for c in sorted(ds, key=lambda x: x["pub"]):
    v = jud.get(c["bvid"], {}).get("v", "?")
    print(f"  [{c['pub'][:7]}][{v}] 《{c['title'][:34]}》 sinc={c['sinc']} 播放{c['view']:,} 赞{c['lr']:.1%} 币{c['cr']:.1%} 藏{c['fr']:.1%}")

print("\n=== 盲判为「软擦边」的 3 支（揭示）===")
for b, j in jud.items():
    if j["v"] == "软擦边":
        c = cards[b]
        print(f"  [{c['cell']} {CELL_LBL[c['cell']]}] {b} 《{c['title'][:36]}》 {c['pub'][:7]} 播放{c['view']:,} 时长{c['dur']}s 赞{c['lr']:.1%} 币{c['cr']:.1%} 藏{c['fr']:.1%} sinc={c['sinc']} 分区:{c['tname']}")

print("\n=== 全体判定分布 ===")
print(" ", Counter(j["v"] for j in jud.values()))
