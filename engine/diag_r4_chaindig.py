# -*- coding: utf-8 -*-
"""R4 擦边识别率测试 · 阶段2 —— 池内种子 + 搜索物种 + 相关推荐一条龙（深度2）。

阶段1结论：首页热门 240 支 0 命中（热门流策展干净）；池内 205 命中但标题面貌混杂。
阶段2设计：
  A) 搜索 API 定位真·擦边物种（变装/宅舞/热舞/纯欲/黑丝/直拍）→ fetch_view 评分 → 识别率（召回面）
  B) 池内 R4 种子（4 极端签名 + 2 无辜对照）→ fetch_view 评分 → 误伤面
  C) 每个种子相关推荐一条龙（L1 40条 → L2 每链最多2支）→ 物种聚簇检验
产出：data/fav_mine/r4_edgehunt2_YYYYMMDD.json + 控制台摘要。
"""
import json
import math
import os
import re
import sys
import time
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402
import v3_rules as _rules  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
BAND = 0.2
VIEW_FLOOR = 3000
MAX_RELATED = 26
L2_PER_CHAIN = 2
DATE = time.strftime("%Y%m%d")

KEYWORDS = ["变装 挑战", "宅舞", "热舞", "纯欲", "黑丝", "女团 直拍"]
POOL_SEEDS = ["BV13sHVzFEby", "BV18H4MzsEFm", "BV1fqtJ6dEu8", "BV1ZtTQ68EDk"]  # 极端签名
CTRL_SEEDS = ["BV1uLth6rErU", "BV1wrcLzeEQw"]  # 无辜对照：cos道具教程 / 丹恒MMD边界


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
            pop.setdefault(v["bvid"], {"coin": (st.get("coin") or 0) / view,
                                       "fav": (st.get("favorite") or 0) / view,
                                       "like": (st.get("like") or 0) / view})
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
                    pop.setdefault(v["bvid"], {"coin": (st.get("coin") or 0) / view,
                                               "fav": (st.get("favorite") or 0) / view,
                                               "like": (st.get("like") or 0) / view})
    return pop


def bands_of(pop):
    bands = defaultdict(lambda: defaultdict(list))
    for r in pop.values():
        k = round(math.log10(max(1, r.get("view", 0))) / BAND) if r.get("view") else 3
        for ax in ("coin", "fav", "like"):
            bands[k][ax].append(r[ax])
    return {k: {ax: sorted(d[ax]) for ax in d} for k, d in bands.items()}


def pct_of(arr, x):
    if not arr:
        return None
    lo = sum(1 for a in arr if a < x)
    return lo / max(1, len(arr) - 1) if len(arr) > 1 else 0.5


def near_a(r):
    return r["coin_rate"] < 0.02 and r["fav_rate"] > 0.10 and 0.12 < r["like_rate"] <= 0.20


def near_b(r):
    return r["like_rate"] > 0.20 and r["coin_rate"] < 0.02 and r["fav_rate"] <= 0.10


def near_c(r):
    return r["like_rate"] > 0.20 and 0.02 <= r["coin_rate"] < 0.04 and r["fav_rate"] > 0.10


def weakest_ratio(r):
    cands = [(r["like_rate"] / 0.20, "赞率"), (r["coin_rate"] / 0.02, "币率"), (r["fav_rate"] / 0.10, "藏率")]
    return min(cands)


def main():
    cli = BiliClient(interval=0.6)
    baseline = load_pop()
    bands = bands_of(baseline)
    print(f"[base] 参照人口 {len(baseline)}", flush=True)

    scored = {}

    def score_card(v, layer, src, frm, kw=None):
        bvid = v.get("bvid")
        if not bvid:
            return None
        st = v.get("stat") or {}
        view = st.get("view") or v.get("view") or 0
        if view < VIEW_FLOOR:
            return None
        vr = max(1, view)
        coin = st.get("coin") or 0
        fav = st.get("favorite") or 0
        like = st.get("like") or 0
        lr, cr, fr = like / vr, coin / vr, fav / vr
        r4 = lr > _rules.R_EDGE_LIKE and cr < _rules.R_EDGE_COIN and fr > _rules.R_EDGE_FAV
        k = round(math.log10(view) / BAND)
        band = bands.get(k)
        p_coin = pct_of(band["coin"], cr) if band else None
        dur = v.get("duration") or 0
        title = re.sub(r'<em class="keyword">|</em>', "", v.get("title") or "")
        owner = v.get("owner") or {}
        tier, firings = _rules.v3_tier(p_coin if p_coin is not None else 0, dur, fr, cr, lr, title)
        rec = {"bvid": bvid, "aid": v.get("aid"), "title": title,
               "owner": owner.get("name") if isinstance(owner, dict) else (v.get("owner") or "?"),
               "mid": owner.get("mid") if isinstance(owner, dict) else None,
               "tname": v.get("tname") or "", "dur": dur, "view": view,
               "like_rate": round(lr, 4), "coin_rate": round(cr, 4), "fav_rate": round(fr, 4),
               "r4": r4, "r8": like / max(1, coin) > 50, "layer": layer, "src": src,
               "kw": kw, "from": frm, "p_coin": p_coin, "tier": tier, "firings": firings}
        old = scored.get(bvid)
        if old is None or layer < old["layer"]:
            scored[bvid] = rec
        return rec

    # ---- A) 搜索真·擦边物种 ----
    search_summary = []
    search_seeds = []
    for kw in KEYWORDS:
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/search/type",
                             {"search_type": "video", "keyword": kw, "page": 1}, sign_wbi=True, tries=2)
            res = (d or {}).get("result") or []
        except Exception as e:
            print(f"[search] {kw} fail: {str(e)[:50]}", flush=True)
            continue
        res = sorted(res, key=lambda x: -(x.get("play") or 0))[:3]
        fires, best = 0, None
        for it in res:
            try:
                v = cli.fetch_view(it.get("bvid"))
            except Exception:
                continue
            r = score_card(v, 0, "search", None, kw=kw)
            if not r:
                continue
            if r["r4"]:
                fires += 1
                if best is None or r["like_rate"] > best["like_rate"]:
                    best = r
                print(f"  [R4✓ 搜索:{kw}] {r['title'][:32]} 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%}", flush=True)
        if best and len(search_seeds) < 2:
            search_seeds.append(best["bvid"])
        search_summary.append({"kw": kw, "n_checked": len(res), "fires": fires,
                               "best": {k: best[k] for k in ("bvid", "title", "like_rate", "coin_rate", "fav_rate")} if best else None})
        print(f"[search] {kw} 抽检{len(res)} 命中{fires}", flush=True)

    # ---- B) 池内种子评分（fetch_view 刷新）----
    seeds = []
    for tag, lst in (("extreme", POOL_SEEDS), ("control", CTRL_SEEDS)):
        for bvid in lst:
            try:
                v = cli.fetch_view(bvid)
            except Exception as e:
                print(f"[seed] {bvid} fail: {str(e)[:40]}", flush=True)
                continue
            r = score_card(v, 0, "pool", tag)
            if r:
                seeds.append(r["bvid"])
                print(f"[seed:{tag}] {bvid}《{r['title'][:28]}》 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%} R4={'✓' if r['r4'] else '×'}", flush=True)
    seeds += [b for b in search_seeds if b not in seeds]

    # ---- C) 一条龙（深度2）----
    rel_calls = 0
    chains = []

    def fetch_related(aid):
        nonlocal rel_calls
        if rel_calls >= MAX_RELATED or not aid:
            return None
        rel_calls += 1
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/archive/related",
                             {"aid": aid}, tries=2)
            return d if isinstance(d, list) else ((d or {}).get("list") or [])
        except Exception as e:
            print(f"  [related] aid={aid} fail: {str(e)[:50]}", flush=True)
            return None

    for sbv in seeds:
        srec = scored[sbv]
        ch = {"seed": sbv, "seed_r4": srec["r4"], "l1_n": 0, "l1_hits": [], "l1_near": 0, "l2": []}
        items = fetch_related(srec.get("aid")) or []
        for it in items:
            r = score_card(it, 1, "related", sbv)
            if not r:
                continue
            ch["l1_n"] += 1
            if r["r4"]:
                ch["l1_hits"].append(r["bvid"])
                print(f"  [R4✓ L1@{sbv[-6:]}] {r['title'][:32]} 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%}", flush=True)
            elif near_a(r) or near_b(r) or near_c(r):
                ch["l1_near"] += 1
        for hb in sorted(ch["l1_hits"], key=lambda b: -scored[b]["like_rate"])[:L2_PER_CHAIN]:
            items2 = fetch_related(scored[hb].get("aid")) or []
            h2 = []
            for it in items2:
                r = score_card(it, 2, "related", hb)
                if r and r["r4"]:
                    h2.append(r["bvid"])
                    print(f"  [R4✓ L2@{sbv[-6:]}] {r['title'][:32]} 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%}", flush=True)
            ch["l2"].append({"node": hb, "hits": h2, "n": len(items2)})
        chains.append(ch)
        l2h = sum(len(x["hits"]) for x in ch["l2"])
        print(f"[chain] 《{srec['title'][:24]}》 L1 {len(ch['l1_hits'])}/{ch['l1_n']} 边缘{ch['l1_near']} | L2 {l2h}", flush=True)

    # ---- 汇总 ----
    all_r4 = [r for r in scored.values() if r["r4"]]
    n_a = sum(1 for r in scored.values() if near_a(r))
    n_b = sum(1 for r in scored.values() if near_b(r))
    n_c = sum(1 for r in scored.values() if near_c(r))
    print("\n=== 摘要 ===", flush=True)
    print(f"入册 {len(scored)} 支 | R4 命中 {len(all_r4)}（搜索 {sum(1 for r in all_r4 if r['src']=='search')} / 池种子 {sum(1 for r in all_r4 if r['src']=='pool')} / L1 {sum(1 for r in all_r4 if r['layer']==1)} / L2 {sum(1 for r in all_r4 if r['layer']==2)}）", flush=True)
    print(f"边缘 NM-A {n_a} | NM-B {n_b} | NM-C {n_c}", flush=True)
    for s in search_summary:
        b = s["best"]
        print(f"  搜索[{s['kw']}] 抽检{s['n_checked']} 命中{s['fires']}" + (f" 最佳《{b['title'][:24]}》赞{b['like_rate']:.0%}" if b else ""), flush=True)
    for ch in chains:
        s = scored[ch["seed"]]
        l2h = sum(len(x["hits"]) for x in ch["l2"])
        print(f"  链[{ch['seed']}]{('对照' if s['src']=='pool' and s['from']=='control' else '')}《{s['title'][:22]}》 L1 {len(ch['l1_hits'])}/{ch['l1_n']} L2 {l2h}", flush=True)

    out = {"meta": {"date": DATE, "n_scored": len(scored), "n_r4": len(all_r4)},
           "keywords": KEYWORDS, "search_summary": search_summary,
           "seeds": seeds, "chains": chains,
           "r4_hits": sorted(all_r4, key=lambda r: weakest_ratio(r)[0]),
           "nearmiss": {"A": n_a, "B": n_b, "C": n_c},
           "scored": list(scored.values())}
    path = os.path.join(MINE, f"r4_edgehunt2_{DATE}.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[done] -> {path}", flush=True)


if __name__ == "__main__":
    main()
