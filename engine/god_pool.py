# -*- coding: utf-8 -*-
"""神作货架公共池——合并 参照库(pop) + 五臂 flow 节点，统一 v3+R9 判档。

口径：
  · 带内百分位基线 = 参照人口（favmine raw + 首页样本，view>=3000）——冻结口径
  · 池 = tier ∈ {神作候选, 优秀候选} 的去重视频
  · 字段合并：pop 有绝对计数/pubdate/owner；flow 节点有 category/pubdate(部分)
  · 缺 pubdate 的条目由 diag_pubdate_backfill.py 回填（sidecar: pubdate_backfill.json）
"""
import glob
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
import v3_rules as _rules  # noqa: E402
from godflow_v1 import categorize
from mining_data import (load_population, load_reference, load_flow_nodes,
                         build_bands, band_percentile, owner_fields)  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
FG = os.path.join(ROOT, "data", "flow_graph")
BAND = 0.2


def _load_pop():
    return {b: r for b, r in load_population(MINE, SDIR).items() if r['view'] >= 3000}

def _load_flow_nodes():
    return load_flow_nodes(FG)

def latest(pattern):
    fs = sorted(glob.glob(os.path.join(FG, pattern)), key=lambda p: os.path.basename(p))
    return fs[-1] if fs else None


def load_blacklist():
    p = os.path.join(os.path.dirname(FG), "ml", "blacklist.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return {}
    return {"owners": [], "bvids": []}


def build_pool():
    pop = _load_pop()
    fnodes = _load_flow_nodes()
    # Shared reference membership is frozen at 2026-09-03, deduplicated by bvid.
    BANDS = build_bands(load_reference(MINE, SDIR))

    def pct_of(view, coin_rate):
        return band_percentile(BANDS, view, coin_rate)

    # 合并池
    pool = {}
    for b, r in pop.items():
        vr = max(1, r["view"])
        n = fnodes.get(b) or {}
        cat = n.get("category") or categorize(r["title"], r.get("tname"))[0]
        pool[b] = {"bvid": b, "title": r["title"], "view": r["view"], "dur": r["dur"],
                   "coin": r["coin"], "fav": r["fav"], "like": r["like"],
                   "pubdate": r.get("pubdate") or n.get("pubdate"),
                   "owner": r.get("owner") or "", "owner_mid": r.get("owner_mid") or "", "category": cat,
                   "pct": pct_of(r["view"], r["coin"] / vr), "src": r.get("src"),
                   "pic": r.get("pic") or ""}
    for b, n in fnodes.items():
        if b in pool:
            if not pool[b].get("pubdate") and n.get("pubdate"):
                pool[b]["pubdate"] = n["pubdate"]
            if pool[b]["category"] in ("其他", None) and n.get("category"):
                pool[b]["category"] = n["category"]
            continue
        vr = max(1, n.get("view") or 0)
        coin_rate, fav_rate, like_rate = n.get("coin_rate") or 0, n.get("fav_rate") or 0, n.get("like_rate") or 0
        pool[b] = {"bvid": b, "title": n.get("title") or "", "view": n.get("view") or 0,
                   "dur": n.get("dur") or 0,
                   "coin": round(coin_rate * vr), "fav": round(fav_rate * vr), "like": round(like_rate * vr),
                   "pubdate": n.get("pubdate"), "owner": owner_fields(n.get("owner"))[0], "owner_mid": owner_fields(n.get("owner"))[1], "category": n.get("category") or "其他",
                   "pct": pct_of(n.get("view") or 0, coin_rate), "src": "flow:" + (n.get("arm") or ""),
                   "pic": n.get("pic") or ""}
    # 分类策略（Elabation 2026-09-04 修订）：清空全部机器/关键词标签，全池置「待分类」，
    # 由用户在货架上完成第一轮人工分类；积累带标签数据后再训练（标题+tag）。
    # ml_categorize.py 保留备用（v1 模型已冻结存档），待标注量足够后重启。
    vbf = load_view_backfill()
    out = {}
    for b, r in pool.items():
        v = vbf.get(b) or {}
        # Undated sidecars may fill metadata, not replace dated counter snapshots.
        if v.get("pubdate") and not r.get("pubdate"):
            r["pubdate"] = v["pubdate"]
        if v.get("owner") and not r.get("owner"):
            r["owner"] = v["owner"]
        if v.get("pic"):
            r["pic"] = v["pic"]
        # 分类策略（2026-09-04 修订）：全池置「待分类」，等用户第一轮人工标注
        if isinstance(r.get("owner"), dict):
            r["owner"], r["owner_mid"] = owner_fields(r["owner"])
        r["category"] = "待分类"
        r["cat_src"] = "pending"
        vr = max(1, r["view"])
        tier, fir = _rules.v3_tier(r["pct"], r["dur"], r["fav"] / vr, r["coin"] / vr, r["like"] / vr, r["title"])
        r["firings"] = fir
        if tier in ("神作候选", "优秀候选"):
            r["tier"] = tier
            r["coin_rate"] = round(r["coin"] / vr, 5)
            r["fav_rate"] = round(r["fav"] / vr, 5)
            r["like_rate"] = round(r["like"] / vr, 5)
            out[b] = r
    # 黑名单过滤（Elabation 2026-09-04：fan人张 等不推荐）
    bl = load_blacklist()
    bl_names = {o.get("name") for o in (bl.get("owners") or []) if o.get("name")}
    bl_mids = {str(o.get("mid")) for o in (bl.get("owners") or []) if o.get("mid")}
    bl_bvids = set(bl.get("bvids") or [])
    n_bl = 0
    for b in list(out.keys()):
        r = out[b]
        if (r.get("owner") in bl_names) or (str(r.get("owner_mid") or "") in bl_mids) or (b in bl_bvids):
            del out[b]
            n_bl += 1
    return out, {"pop_n": len(pop), "bands": {k: len(v) for k, v in BANDS.items()}, "n_black": n_bl}


def load_backfill():
    p = os.path.join(FG, "pubdate_backfill.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def load_view_backfill():
    p = os.path.join(FG, "pool_view_backfill.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return {}
    return {}


if __name__ == "__main__":
    pool, meta = build_pool()
    bf = load_backfill()
    n_god = sum(1 for r in pool.values() if r["tier"] == "神作候选")
    n_nopd = sum(1 for r in pool.values() if not r.get("pubdate"))
    print(f"[pool] 池 {len(pool)}（神作 {n_god} / 优秀 {len(pool)-n_god}）｜ 缺 pubdate {n_nopd} ｜ 回填表 {len(bf)}")
    cats = defaultdict(int)
    for r in pool.values():
        cats[r["category"]] += 1
    print("[cats] " + " ｜ ".join(f"{k}:{v}" for k, v in sorted(cats.items(), key=lambda kv: -kv[1])[:10]))
