# -*- coding: utf-8 -*-
"""R4 池内扫描 —— 零请求扫挖矿库 + 首页样本，找擦边三连签名作种子。"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
VIEW_FLOOR = 3000

rows = {}

def add(v, src):
    bvid = v.get("bvid")
    if not bvid or bvid in rows:
        return
    st = v.get("stat") or {}
    view = st.get("view") or v.get("view") or 0
    if view < VIEW_FLOOR:
        return
    vr = max(1, view)
    coin = st.get("coin") or 0
    fav = st.get("favorite") or 0
    like = st.get("like") or 0
    lr, cr, fr = like / vr, coin / vr, fav / vr
    rows[bvid] = {"bvid": bvid, "title": v.get("title") or "", "src": src,
                  "view": view, "like_rate": lr, "coin_rate": cr, "fav_rate": fr,
                  "tname": v.get("tname") or "", "owner": v.get("owner") or "",
                  "r4": lr > 0.20 and cr < 0.02 and fr > 0.10}

for fn in os.listdir(SDIR):
    if fn.startswith("sample_") and fn.endswith(".json"):
        try:
            p = json.load(open(os.path.join(SDIR, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            ow = v.get("owner") or {}
            v = dict(v)
            v["owner"] = ow.get("name") if isinstance(ow, dict) else ow
            add(v, "home")

for fn in os.listdir(MINE):
    if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
        try:
            p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            add(v, "mine")

r4 = [r for r in rows.values() if r["r4"]]
nma = [r for r in rows.values() if r["coin_rate"] < 0.02 and r["fav_rate"] > 0.10 and 0.12 < r["like_rate"] <= 0.20]
print(f"池内入册 {len(rows)} 支（view>={VIEW_FLOOR}）")
print(f"R4 命中 {len(r4)} 条 | NM-A 边缘 {len(nma)} 条")
for r in sorted(r4, key=lambda x: -x["like_rate"])[:20]:
    print(f"  [R4] {r['bvid']} {r['src']} 《{r['title'][:36]}》 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%} UP:{r['owner'][:16]}")
for r in sorted(nma, key=lambda x: -x["like_rate"])[:10]:
    print(f"  [NM-A] {r['bvid']} {r['src']} 《{r['title'][:36]}》 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%}")
