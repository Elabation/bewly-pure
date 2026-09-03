# -*- coding: utf-8 -*-
"""R9 声援提档的效果审计（零请求）。

1) 九份特例报告的前后判档对照；
2) round2 76 行全量重算（用参照人口补 stat），对比新旧档位与人工显式判词的一致性。
"""
import json
import math
import os
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v3_rules import v3_tier  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
BAND = 0.2

# ---- 参照人口（带内 pct 用，与冻结基线同口径） ----
pop = {}
for fn in ("sample_20260903_185231.json", "sample_20260903_203054.json"):
    try:
        p = json.load(open(os.path.join(SDIR, fn), encoding="utf-8"))
    except Exception:
        continue
    for v in (p.get("videos") or []):
        st = v.get("stat") or {}
        vw = st.get("view") or 0
        if vw >= 3000 and v.get("bvid"):
            pop.setdefault(v["bvid"], {"view": vw, "dur": v.get("duration") or 0,
                                       "coin": (st.get("coin") or 0) / vw, "fav": (st.get("favorite") or 0) / vw,
                                       "like": (st.get("like") or 0) / vw})
for fn in os.listdir(MINE):
    if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
        try:
            p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            vw = v.get("view") or 0
            if vw >= 3000 and v.get("bvid"):
                st = v.get("stat") or {}
                pop.setdefault(v["bvid"], {"view": vw, "dur": v.get("duration") or 0,
                                           "coin": (st.get("coin") or 0) / max(1, vw),
                                           "fav": (st.get("favorite") or 0) / max(1, vw),
                                           "like": (st.get("like") or 0) / max(1, vw)})
bands = defaultdict(list)
for r in pop.values():
    bands[round(math.log10(r["view"]) / BAND)].append(r["coin"])
BANDS = {k: sorted(a) for k, a in bands.items()}


def pct_of(view, rate):
    arr = BANDS.get(round(math.log10(view) / BAND))
    if not arr:
        return None
    lo = sum(1 for a in arr if a < rate)
    return lo / max(1, len(arr) - 1)


print("==== 一 · 九案前后对照 ====")
case_files = [
    ("case_bv_report.json", "养生话术"),
    ("case_bv_report_BV1Zx7B6DE6w.json", "哈基米"),
    ("case_bv_report_BV1ACTa6UEY5.json", "PvZ挂机"),
    ("case_bv_report_BV1Ew846QEQk.json", "男大自我介绍"),
    ("case_bv_report_BV1Pz4968EA6.json", "擦边三连标准型"),
    ("case_bv_report_BV1nW4oz7EXT.json", "哑巴橱窗"),
    ("case_bv_report_BV1gnPFzCEo8.json", "声援时评"),
    ("case_bv_report_BV1aT4y167Pj.json", "病毒吐槽"),
    ("case_bv_report_BV1BG4y137mG.json", "真神作孤岛"),
]
for fn, lab in case_files:
    p = os.path.join(MINE, fn)
    if not os.path.exists(p):
        continue
    r = json.load(open(p, encoding="utf-8"))
    old = (r.get("v3_tier") or "?").replace("候选", "")
    new, fir = v3_tier(r.get("p_coin"), r.get("dur"), r.get("fav_rate"), r.get("coin_rate"), r.get("like_rate"))
    mark = " ←R9" if new != old else ""
    r9 = [f for f in fir if f.startswith("R9")]
    print(f"{lab}: {old} → {new}{mark}  {';'.join(r9)}")

print("\n==== 二 · round2 76 行全量重算 ====")
r2 = json.load(open(os.path.join(MINE, "round2_labels.json"), encoding="utf-8"))
rows = r2.get("rows") or []
flips = defaultdict(list)
agree_old, agree_new, n_judged = 0, 0, 0
for r in rows:
    b = r.get("bvid")
    st = pop.get(b)
    if not st:
        continue
    p_ = pct_of(st["view"], st["coin"])
    old_t, _ = v3_tier.__wrapped__(p_, st["dur"], st["fav"], st["coin"], st["like"]) if hasattr(v3_tier, "__wrapped__") else (None, None)
    # 旧口径（无 R9）——内联重算
    tier = "一般候选"
    if p_ is None:
        old_t = "无数据"
    else:
        if p_ >= 0.93:
            tier = "神作候选"
        elif p_ >= 0.85:
            tier = "优秀候选"
        elif p_ < 0.72:
            tier = "垃圾候选"
        if st["dur"] and st["dur"] < 30:
            if tier in ("神作候选", "优秀候选"):
                tier = "一般候选"
        elif st["dur"] and st["dur"] < 90 and tier == "神作候选":
            tier = "优秀候选"
        fc = st["fav"] / max(st["coin"], 1e-6)
        if fc > 8 and st["fav"] > 0.15 and tier == "神作候选":
            tier = "优秀候选"
        old_t = tier
        new_t, fir = v3_tier(p_, st["dur"], st["fav"], st["coin"], st["like"])
        short_new = new_t.replace("候选", "")
        short_old = old_t.replace("候选", "")
        if short_new != short_old:
            flips[short_old + "→" + short_new].append((b, (r.get("title") or "")[:18], round(p_, 3)))
        vd = (r.get("verdict") or "").replace("＿＿_", "").strip()
        if vd:
            n_judged += 1
            vgold = "神作" if "神作" in vd else ("优秀" if "优秀" in vd else None)
            if vgold:
                if vgold in short_old:
                    agree_old += 1
                if vgold in short_new:
                    agree_new += 1
print(f"翻档 {sum(len(v) for v in flips.values())} / {len(rows)} 行：")
for k, v in sorted(flips.items()):
    print(f"  {k}: {len(v)} 行 → " + "；".join(f"{t}(pct={p})" for _, t, p in v[:6]) + ("…" if len(v) > 6 else ""))
print(f"显式人工判词 {n_judged} 条中，旧口径命中 {agree_old}，R9 后命中 {agree_new}")
