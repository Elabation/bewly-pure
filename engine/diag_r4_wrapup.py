# -*- coding: utf-8 -*-
"""R4 边缘猎手 · 收尾分析（零请求）：触发物种分布 / 带位分布 / 对照组分离度。"""
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

j2 = json.load(open(os.path.join(MINE, "r4_edgehunt2_20260905.json"), encoding="utf-8"))
scored = j2["scored"]
fires = [r for r in scored if r["r4"]]
print(f"入册 {len(scored)} / R4 {len(fires)}")

def band_of(v):
    return round(math.log10(max(1, v)) / 0.2)

print("\n== R4 触发的播放量级分布（带 k: 10^0.2k）==")
bc = Counter(band_of(r["view"]) for r in fires)
for k in sorted(bc):
    print(f"  带{k} (10^{0.2*k:.1f}~10^{0.2*(k+1):.1f}): {bc[k]}")

print("\n== R4 触发的分区分布 top10 ==")
for t, n in Counter(r["tname"] or "?" for r in fires).most_common(10):
    print(f"  {t}: {n}")

print("\n== 无辜对照链 vs 极端签名链 触发率 ==")
for ch in j2["chains"]:
    s = next(r for r in scored if r["bvid"] == ch["seed"])
    tag = s.get("from") or s.get("src")
    l1r = len(ch["l1_hits"]) / max(1, ch["l1_n"])
    l2h = sum(len(x["hits"]) for x in ch["l2"])
    print(f"  [{tag}] 《{s['title'][:26]}》 L1 {len(ch['l1_hits'])}/{ch['l1_n']} = {l1r:.0%} | L2 {l2h} | 种子R4={s['r4']}")

print("\n== 真实擦边大热门（搜索 top，R4 全未触发）==")
for s in j2["search_summary"]:
    b = s["best"]
    if b:
        print(f"  [{s['kw']}] 《{b['title'][:30]}》 赞{b['like_rate']:.1%} 币{b['coin_rate']:.1%} 藏{b['fav_rate']:.1%}")

print("\n== 触发样本的赞率/币率/藏率中位数 ==")
for name, key in (("赞率", "like_rate"), ("币率", "coin_rate"), ("藏率", "fav_rate")):
    arr = sorted(r[key] for r in fires)
    print(f"  {name} p25={arr[len(arr)//4]:.1%} p50={arr[len(arr)//2]:.1%} p75={arr[3*len(arr)//4]:.1%}")

print("\n== 基线冤枉体检：整个池子里赞率>20%的带内正常度 ==")
# 全池按带统计 like>20% 的占比
allpool = {}
for fn in os.listdir(MINE):
    if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
        try:
            p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            if (v.get("view") or 0) >= 3000 and v.get("bvid") and v["bvid"] not in allpool:
                st = v.get("stat") or {}
                view = max(1, v.get("view") or 1)
                allpool[v["bvid"]] = {"view": v["view"],
                                      "like_rate": (st.get("like") or 0) / view,
                                      "coin_rate": (st.get("coin") or 0) / view,
                                      "fav_rate": (st.get("favorite") or 0) / view}
bands = defaultdict(lambda: [0, 0])
for r in allpool.values():
    k = band_of(r["view"])
    bands[k][1] += 1
    if r["like_rate"] > 0.20:
        bands[k][0] += 1
print("  带 k | 池内条数 | 赞率>20% 占比")
for k in sorted(bands):
    hi, n = bands[k]
    print(f"  带{k} (10^{0.2*k:.1f}~): {n:5d} 条, 赞率>20% 占 {hi/max(1,n):.0%}")
