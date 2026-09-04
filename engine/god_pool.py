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
from godflow_v1 import categorize  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
FG = os.path.join(ROOT, "data", "flow_graph")
BAND = 0.2


def _load_pop():
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
                pop.setdefault(v["bvid"], {"bvid": v["bvid"], "title": v.get("title") or "", "view": vw,
                                           "dur": v.get("duration") or 0,
                                           "coin": st.get("coin") or 0, "fav": st.get("favorite") or 0,
                                           "like": st.get("like") or 0,
                                           "pubdate": v.get("pubdate"), "owner": v.get("owner"),
                                           "tname": v.get("tname"), "src": "home"})
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
                    rec = {"bvid": v["bvid"], "title": v.get("title") or "", "view": vw,
                           "dur": v.get("duration") or 0,
                           "coin": st.get("coin") or 0, "fav": st.get("favorite") or 0,
                           "like": st.get("like") or 0,
                           "pubdate": v.get("pubdate"), "owner": v.get("owner") or v.get("up"),
                           "tname": v.get("tname"), "src": "mine"}
                    if v["bvid"] in pop:
                        old = pop[v["bvid"]]
                        for k in ("coin", "fav", "like", "view"):
                            rec[k] = max(rec[k] or 0, old[k] or 0)
                        rec["pubdate"] = rec.get("pubdate") or old.get("pubdate")
                        rec["owner"] = rec.get("owner") or old.get("owner")
                    pop[v["bvid"]] = rec
    return pop


def _load_flow_nodes():
    nodes = {}
    for pat in ("godflow_2*.json", "godflowdeep_*.json", "godflowbnopad_*.json", "godflowretro_*.json"):
        p = latest(pat)
        if not p:
            continue
        run = json.load(open(p, encoding="utf-8"))
        flows = run.get("flows") or []
        for a in (run.get("arms") or {}).values():
            flows.extend(a.get("flows") or [])
        for f in flows:
            for n in (f.get("nodes") or []):
                b = n.get("bvid")
                if not b:
                    continue
                old = nodes.get(b)
                if old is None or (n.get("pubdate") and not old.get("pubdate")):
                    nodes[b] = n
    return nodes


def latest(pattern):
    fs = sorted(glob.glob(os.path.join(FG, pattern)), key=lambda p: os.path.basename(p))
    return fs[-1] if fs else None


def build_pool():
    pop = _load_pop()
    fnodes = _load_flow_nodes()
    # 基线带（pop only，冻结口径）
    bands = defaultdict(list)
    for r in pop.values():
        bands[round(math.log10(r["view"]) / BAND)].append((r["coin"]) / max(1, r["view"]))
    BANDS = {k: sorted(a) for k, a in bands.items()}

    def pct_of(view, coin_rate):
        if view < 3000:
            return None
        arr = BANDS.get(round(math.log10(view) / BAND))
        if not arr:
            return None
        return sum(1 for a in arr if a < coin_rate) / max(1, len(arr) - 1)

    # 合并池
    pool = {}
    for b, r in pop.items():
        vr = max(1, r["view"])
        n = fnodes.get(b) or {}
        cat = n.get("category") or categorize(r["title"], r.get("tname"))[0]
        pool[b] = {"bvid": b, "title": r["title"], "view": r["view"], "dur": r["dur"],
                   "coin": r["coin"], "fav": r["fav"], "like": r["like"],
                   "pubdate": r.get("pubdate") or n.get("pubdate"),
                   "owner": r.get("owner") or "", "category": cat,
                   "pct": pct_of(r["view"], r["coin"] / vr), "src": r.get("src")}
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
                   "pubdate": n.get("pubdate"), "owner": "", "category": n.get("category") or "其他",
                   "pct": pct_of(n.get("view") or 0, coin_rate), "src": "flow:" + (n.get("arm") or "")}
    # 判档 + 过滤（pool_view_backfill 优先：最新计数 + 封面 + pubdate + UP 名）
    vbf = load_view_backfill()
    ml_path = os.path.join(os.path.dirname(FG), "ml", "pool_categories.json")
    ml_cat = {}
    try:
        ml_cat = json.load(open(ml_path, encoding="utf-8"))
    except Exception:
        pass
    REN = {"擦边颜值": "颜值/舞蹈/cos", "时尚颜值": "颜值/舞蹈/cos", "舞蹈": "颜值/舞蹈/cos"}
    out = {}
    for b, r in pool.items():
        v = vbf.get(b) or {}
        if v.get("stat") and not v.get("error"):
            st = v["stat"]
            vr0 = max(1, st.get("view") or 1)
            r["view"] = st.get("view") or r["view"]
            r["coin"] = st.get("coin") if st.get("coin") is not None else r["coin"]
            r["fav"] = st.get("fav") if st.get("fav") is not None else r["fav"]
            r["like"] = st.get("like") if st.get("like") is not None else r["like"]
            vr = max(1, r["view"])
            r["pct"] = pct_of(r["view"], r["coin"] / vr)
        if v.get("pubdate") and not r.get("pubdate"):
            r["pubdate"] = v["pubdate"]
        if v.get("owner") and not r.get("owner"):
            r["owner"] = v["owner"]
        if v.get("pic"):
            r["pic"] = v["pic"]
        # ML 自动分类覆盖（置信度达标时），并统一门类命名
        m = ml_cat.get(b)
        if m and m.get("cat") and m["cat"] != "待分类":
            r["category"] = m["cat"]
            r["cat_src"] = "ml"
            r["cat_conf"] = m.get("conf")
        r["category"] = REN.get(r["category"], r["category"])
        vr = max(1, r["view"])
        tier, fir = _rules.v3_tier(r["pct"], r["dur"], r["fav"] / vr, r["coin"] / vr, r["like"] / vr, r["title"])
        r["firings"] = fir
        if tier in ("神作候选", "优秀候选"):
            r["tier"] = tier
            r["coin_rate"] = round(r["coin"] / vr, 5)
            r["fav_rate"] = round(r["fav"] / vr, 5)
            r["like_rate"] = round(r["like"] / vr, 5)
            out[b] = r
    return out, {"pop_n": len(pop), "bands": {k: len(v) for k, v in BANDS.items()}}


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
