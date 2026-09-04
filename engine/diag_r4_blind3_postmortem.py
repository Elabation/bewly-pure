# -*- coding: utf-8 -*-
"""R4 盲测第三轮 · 三方对账：判定 × 细胞预测 × YuNet 信号 → 立法裁决。"""
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

data = json.load(open(os.path.join(MINE, f"r4_blind3_{DATE}.json"), encoding="utf-8"))
cards = {c["bvid"]: c for c in data["cards"]}
jud = json.load(open(r"C:\Users\33768\Desktop\r4_blind3_review_judged_2026-09-05.json", encoding="utf-8"))["judgments"]

CELL_LBL = {"T1": "触发·短·真人", "T2": "触发·短·非真人", "T3": "触发·长·赦免",
            "C1": "真人·非R4基线", "H1": "高带·低诚·真人", "G": "随机对照"}

print("=== 细胞 × 判定 ===")
xt = defaultdict(Counter)
for b, j in jud.items():
    c = cards.get(b)
    if c:
        xt[c["cell"]][j["v"]] += 1
for k in ("T1", "T2", "T3", "C1", "H1", "G"):
    t = xt[k]
    n = sum(t.values())
    print(f"  {k} {CELL_LBL[k]}: n={n} 软擦边{t.get('软擦边', 0)} 无辜{t.get('无辜', 0)} 存疑{t.get('存疑', 0)} → 擦边率 {t.get('软擦边', 0) / max(1, n):.0%}")

print("\n=== 假设裁决 ===")
t1n = sum(xt["T1"].values())
t1e = xt["T1"].get("软擦边", 0)
print(f"  ① 定向抓擦边（R4&短&真人）: T1 擦边率 {t1e}/{t1n} = {t1e / max(1, t1n):.0%} → {'✓ 成立(≥60%)' if t1e / max(1, t1n) >= 0.6 else '× 不成立'}")
t2e = xt["T2"].get("软擦边", 0) / max(1, sum(xt["T2"].values()))
print(f"  ② 封面分辨力: T1({t1e / max(1, t1n):.0%}) vs T2({t2e:.0%}) → 真人信号{'有' if t1e / max(1, t1n) > t2e + 0.2 else '弱'}判别力")
t3e = xt["T3"].get("软擦边", 0)
print(f"  ③ 赦免条款: T3 擦边 {t3e}/4 → {'✓ 三轮合计 20/20' if t3e == 0 else '× 破例'}")
c1e = xt["C1"].get("软擦边", 0)
print(f"  ④ 防裸判: C1 真人封面无辜者擦边 {c1e}/6 → {'✓ 真人单独不定罪' if c1e == 0 else '注意'}")
h1e = xt["H1"].get("软擦边", 0)
print(f"  ⑤ 高带翻案: H1 {h1e}/4 → {'× 维持死亡' if h1e == 0 else '存在信号'}")

print("\n=== 三轮合并 · 定向抓取法总成绩（R4触发 & ≤21s & YuNet真人脸）===")
# 轮1+轮2: coverlab fires with real face
lab = json.load(open(os.path.join(MINE, f"r4_coverlab_{DATE}.json"), encoding="utf-8"))["rows"]
j1 = json.load(open(r"C:\Users\33768\Desktop\r4_review_judged_2026-09-05.json", encoding="utf-8"))["judgments"]
j2 = json.load(open(r"C:\Users\33768\Desktop\r4_blind_review_judged_2026-09-05.json", encoding="utf-8"))["judgments"]
lab_map = {r["bvid"]: r for r in lab}
pooled_fire_real, pooled_fire_real_edge = 0, 0
pooled_edge_fire_total = 0
for b, j in {**j1, **j2}.items():
    r = lab_map.get(b)
    if not r or not r.get("r4"):
        continue
    if j["v"] == "软擦边":
        pooled_edge_fire_total += 1
    if r["sig"] and r["sig"]["n_real"] >= 1:
        pooled_fire_real += 1
        if j["v"] == "软擦边":
            pooled_fire_real_edge += 1
t1_edge = t1e
t1_n = t1n
pooled_n = pooled_fire_real + t1_n
pooled_e = pooled_fire_real_edge + t1_edge
print(f"  轮1+2: 真脸触发 {pooled_fire_real} 支 / 擦边 {pooled_fire_real_edge}")
print(f"  轮3(T1): {t1_n} 支 / 擦边 {t1_edge}")
print(f"  合并: {pooled_e}/{pooled_n} = {pooled_e / max(1, pooled_n):.0%}")
# 捕获：历史全部擦边触发中被真人信号保留的比例
cap_n = pooled_edge_fire_total + t1_edge
cap_y = pooled_fire_real_edge + t1_edge
print(f"  捕获: {cap_y}/{cap_n} = {cap_y / max(1, cap_n):.0%}")

print("\n=== T1 细胞揭示（10 擦边 + 2 无辜）===")
for b, j in jud.items():
    c = cards.get(b)
    if c and c["cell"] == "T1":
        print(f"  [{j['v']}] {b} 《{c['title'][:30]}》 {c['tname'] or '—'} {c['dur']}s 真脸{c['n_real']}({c['conf']:.2f}) 播放{c['view']:,}")

print("\n=== 全体判定 ===")
print(" ", Counter(j["v"] for j in jud.values()))
