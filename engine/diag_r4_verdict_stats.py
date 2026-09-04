# -*- coding: utf-8 -*-
"""R4 人工审核结果 × 卡片数据 交叉分析：找分离特征。"""
import json
import math
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

cards = {c["bvid"]: c for c in json.load(open(os.path.join(MINE, f"r4_review_cards_{DATE}.json"), encoding="utf-8"))}
jud = json.load(open(r"C:\Users\33768\Desktop\r4_review_judged_2026-09-05.json", encoding="utf-8"))["judgments"]

rows = []
for bvid, j in jud.items():
    c = cards.get(bvid)
    if not c:
        print(f"[miss] {bvid} 无卡片数据")
        continue
    sinc = (c["cr"] / c["fr"]) if c["fr"] > 0 else 9.99
    rows.append({"g": c["g"], "note": c["note"], "bvid": bvid, "v": j["v"], "fired": c["r4"],
                 "tname": c["tname"] or "—", "view": c["view"], "dur": c["dur"],
                 "lr": c["lr"], "cr": c["cr"], "fr": c["fr"], "sinc": sinc})

def med(a):
    a = sorted(a)
    return a[len(a) // 2] if a else float("nan")

print("=== 判定汇总 ===")
print("总判定:", Counter(r["v"] for r in rows))
fires = [r for r in rows if r["fired"]]
print(f"\n=== R4 终审成绩单 ===")
print(f"触发 {len(fires)} 支: 软擦边 {sum(1 for r in fires if r['v']=='软擦边')} / 无辜 {sum(1 for r in fires if r['v']=='无辜')} / 存疑 {sum(1 for r in fires if r['v']=='存疑')} → 精确率 {sum(1 for r in fires if r['v']=='软擦边')}/{len(fires)} = {sum(1 for r in fires if r['v']=='软擦边')/len(fires):.0%}")
A = [r for r in rows if r["g"] == "A"]
A_edge = [r for r in A if r["v"] == "软擦边"]
print(f"A组(真擦边候选·R4全未触发) {len(A)} 支: 确认软擦边 {len(A_edge)} / 无辜 {sum(1 for r in A if r['v']=='无辜')} / 存疑 {sum(1 for r in A if r['v']=='存疑')} → 漏报确认率 {len(A_edge)/len(A):.0%}，R4 召回 = 0/18")

print("\n=== 特征1 · 触发集内「分区」分离度 ===")
xt = defaultdict(Counter)
for r in fires:
    xt[r["tname"]][r["v"]] += 1
for t, cnt in sorted(xt.items(), key=lambda kv: -sum(kv[1].values())):
    print(f"  {t}: {dict(cnt)}")

print("\n=== 特征2 · 触发集内数值对比（软擦边 vs 无辜）===")
for key, name in (("lr", "赞率"), ("cr", "币率"), ("fr", "藏率"), ("sinc", "诚意比coin/fav"), ("dur", "时长s"), ("view", "播放")):
    a = [r[key] for r in fires if r["v"] == "软擦边"]
    b = [r[key] for r in fires if r["v"] == "无辜"]
    f = (lambda x: f"{x:.3f}") if key in ("sinc",) else ((lambda x: f"{x:.1%}") if key in ("lr", "cr", "fr") else (lambda x: f"{x:,.0f}"))
    print(f"  {name}: 软擦边中位 {f(med(a))} / 无辜中位 {f(med(b))}")

print("\n=== 特征3 · A组（大带真擦边候选）诚意比完美二分？===")
for r in sorted(A, key=lambda x: x["sinc"]):
    print(f"  sinc={r['sinc']:.3f} [{r['v']}] {r['bvid']} 《{cards[r['bvid']]['title'][:26]}》 赞{r['lr']:.1%} 币{r['cr']:.1%} 藏{r['fr']:.1%} 播放{r['view']:,}")

print("\n=== 特征4 · 触发集逐支明细（按判定分组）===")
for v in ("软擦边", "无辜"):
    print(f"  -- 判「{v}」的触发 --")
    for r in sorted([x for x in fires if x["v"] == v], key=lambda x: -x["lr"]):
        print(f"  {r['bvid']} 《{cards[r['bvid']]['title'][:30]}》 赞{r['lr']:.1%} 币{r['cr']:.1%} 藏{r['fr']:.1%} sinc={r['sinc']:.3f} 时长{r['dur']}s 播放{r['view']:,} 分区:{r['tname']} 组:{r['g']}{r['note']}")

print("\n=== 特征5 · 全体(含A组)诚意比 × 判定 ===")
for r in sorted(rows, key=lambda x: x["sinc"]):
    mark = "触" if r["fired"] else "漏"
    print(f"  sinc={r['sinc']:.3f} {mark}[{r['g']}] {r['v']}")
