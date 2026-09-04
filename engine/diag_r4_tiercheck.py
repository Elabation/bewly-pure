# -*- coding: utf-8 -*-
"""检验「擦边视频币率低→v3 自动判垃圾」是否成立：T1 细胞 12 支的 v3 判档分布。"""
import json
import math
import os
import sys
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v3_rules as _rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
BAND = 0.2


def load_pop():
    pop = {}
    for fn in ("sample_20260903_185231.json", "sample_20260903_203054.json"):
        try:
            p = json.load(open(os.path.join(SDIR, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            st = v.get("stat") or {}
            view = st.get("view") or 0
            if view < 3000 or not v.get("bvid"):
                continue
            pop.setdefault(v["bvid"], (st.get("coin") or 0) / view)
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                if (v.get("view") or 0) >= 3000 and v.get("bvid"):
                    st = v.get("stat") or {}
                    view = max(1, v.get("view") or 1)
                    pop.setdefault(v["bvid"], (st.get("coin") or 0) / view)
    return pop


data = json.load(open(os.path.join(MINE, "r4_blind3_20260905.json"), encoding="utf-8"))
cards = {c["bvid"]: c for c in data["cards"]}
jud = json.load(open(r"C:\Users\33768\Desktop\r4_blind3_review_judged_2026-09-05.json", encoding="utf-8"))["judgments"]

pop = load_pop()
# 带 median coin rate：全池按带聚合（view 从 blind3 cards 不够，需池内 view —— 简化：直接用带内 cr 排名 via pop values + card view band）
bands = defaultdict(list)
for fn in os.listdir(MINE):
    if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
        try:
            p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            if (v.get("view") or 0) >= 3000 and v.get("bvid"):
                st = v.get("stat") or {}
                view = max(1, v.get("view") or 1)
                bands[round(math.log10(view) / BAND)].append((st.get("coin") or 0) / view)
med = {k: sorted(v)[len(v) // 2] for k, v in bands.items()}

print("=== T1 12 支的 v3 判档（pct = 带内币率百分位）===")
tiers = Counter()
for b, j in jud.items():
    c = cards.get(b)
    if not c or c["cell"] != "T1":
        continue
    k = round(math.log10(max(1, c["view"])) / BAND)
    band_vals = sorted(bands.get(k, []))
    if band_vals:
        lo = sum(1 for x in band_vals if x < c["cr"])
        pct = lo / max(1, len(band_vals) - 1)
    else:
        pct = None
    tier, firings = _rules.v3_tier(pct if pct is not None else 0.5, c["dur"], c["fr"], c["cr"], c["lr"], c["title"])
    tiers[tier] += 1
    r9 = [f for f in firings if f.startswith("R9")]
    print(f"  [{j['v']}] 《{c['title'][:26]}》 币率{c['cr']:.1%} 带k={k} 带中位币率{med.get(k, 0):.1%} pct={pct:.2f} → {tier}" + (f" ｜{r9[0][:24]}" if r9 else ""))
print("\nT1 判档分布:", dict(tiers))
print(f"（若『币率低自动沉底』成立，应全部为 垃圾候选；出现 一般/优秀 即存在漏网）")
