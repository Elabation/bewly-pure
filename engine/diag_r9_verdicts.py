# -*- coding: utf-8 -*-
"""翻档行 × 显式人工判词 交叉核对（零请求）。"""
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

M = r"D:\work_space\b站插件项目\bilibili-clean\data\fav_mine"
S = r"D:\work_space\b站插件项目\bilibili-clean\data\samples"
sys.path.insert(0, r"D:\work_space\b站插件项目\bilibili-clean\engine")
from v3_rules import v3_tier  # noqa: E402

pop = {}
for fn in ("sample_20260903_185231.json", "sample_20260903_203054.json"):
    p = json.load(open(os.path.join(S, fn), encoding="utf-8"))
    for v in (p.get("videos") or []):
        st = v.get("stat") or {}
        vw = st.get("view") or 0
        if vw >= 3000 and v.get("bvid"):
            pop.setdefault(v["bvid"], {"view": vw, "dur": v.get("duration") or 0,
                                       "coin": (st.get("coin") or 0) / vw,
                                       "fav": (st.get("favorite") or 0) / vw,
                                       "like": (st.get("like") or 0) / vw})
for fn in os.listdir(M):
    if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
        p = json.load(open(os.path.join(M, fn), encoding="utf-8"))
        for v in (p.get("videos") or []):
            vw = v.get("view") or 0
            if vw >= 3000 and v.get("bvid"):
                st = v.get("stat") or {}
                pop.setdefault(v["bvid"], {"view": vw, "dur": v.get("duration") or 0,
                                           "coin": (st.get("coin") or 0) / max(1, vw),
                                           "fav": (st.get("favorite") or 0) / max(1, vw),
                                           "like": (st.get("like") or 0) / max(1, vw)})
bands = {}
for r in pop.values():
    bands.setdefault(round(math.log10(r["view"]) / 0.2), []).append(r["coin"])


def pct_of(view, rate):
    arr = sorted(bands.get(round(math.log10(view) / 0.2)) or [])
    return None if not arr else sum(1 for a in arr if a < rate) / max(1, len(arr) - 1)


r2 = json.load(open(os.path.join(M, "round2_labels.json"), encoding="utf-8"))
print("翻档行 × 显式判词核对：")
n_conf = n_ok = 0
for r in r2["rows"]:
    st = pop.get(r["bvid"])
    if not st:
        continue
    p_ = pct_of(st["view"], st["coin"])
    if p_ is None:
        continue
    tier = "一般候选"
    if p_ >= 0.93:
        tier = "神作候选"
    elif p_ >= 0.85:
        tier = "优秀候选"
    elif p_ < 0.72:
        tier = "垃圾候选"
    d = st["dur"]
    if d and d < 30:
        if tier in ("神作候选", "优秀候选"):
            tier = "一般候选"
    elif d and d < 90 and tier == "神作候选":
        tier = "优秀候选"
    fc = st["fav"] / max(st["coin"], 1e-6)
    if fc > 8 and st["fav"] > 0.15 and tier == "神作候选":
        tier = "优秀候选"
    new_t, fir = v3_tier(p_, d, st["fav"], st["coin"], st["like"])
    if new_t.replace("候选", "") == tier.replace("候选", ""):
        continue
    vd = (r.get("verdict") or "").replace("＿＿_", "").strip()
    if vd:
        conflict = ("神作" in vd and "神作" not in new_t) or ("优秀" in vd and new_t in ("一般候选", "垃圾候选"))
        if conflict:
            n_conf += 1
            print(f"  [冲突] {tier}->{new_t} | 判词:{vd[:26]} | {(r.get('title') or '')[:22]}")
        else:
            n_ok += 1
            print(f"  [一致] {tier}->{new_t} | 判词:{vd[:26]} | {(r.get('title') or '')[:22]}")
    else:
        print(f"  [无判词] {tier}->{new_t} | {(r.get('title') or '')[:22]}")
print(f"\n冲突 {n_conf} / 一致 {n_ok}")
