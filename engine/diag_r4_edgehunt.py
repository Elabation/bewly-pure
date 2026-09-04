# -*- coding: utf-8 -*-
"""R4 擦边识别率测试 —— 首页挖矿 + 相关推荐一条龙（深度2）。

目的：验证 R4 擦边三连（赞率>20% & 币率<2% & 藏率>10%）在真实首页流中的
命中表现与误伤风险——免得冤枉好视频。

流程：
  L0 首页热门（popular 12页，空手则二轮8页）→ R4 特判 → 命中作种子
  L1 种子相关推荐（archive/related 40条）→ 全量特判 → R4 命中续挖
  L2 命中节点相关推荐（每链最多2支，总预算20次）→ 全量特判

产出：data/fav_mine/r4_edgehunt_YYYYMMDD.json + 控制台摘要。
"""
import json
import math
import os
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
MAX_SEEDS = 6
L2_PER_CHAIN = 2
MAX_RELATED = 20
DATE = time.strftime("%Y%m%d")


def load_pop():
    """参照人口 = 挖矿库 + 首页样本（与 diag_case_bv 同口径，零请求）。"""
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
            pop.setdefault(v["bvid"], {"view": view,
                                       "coin": (st.get("coin") or 0) / view,
                                       "fav": (st.get("favorite") or 0) / view,
                                       "like": (st.get("like") or 0) / view})
    n_home = len(pop)
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
                    pop.setdefault(v["bvid"], {"view": view,
                                               "coin": (st.get("coin") or 0) / view,
                                               "fav": (st.get("favorite") or 0) / view,
                                               "like": (st.get("like") or 0) / view})
    return pop, n_home


def bands_of(pop):
    bands = defaultdict(lambda: defaultdict(list))
    for b, r in pop.items():
        k = round(math.log10(r["view"]) / BAND)
        for ax in ("coin", "fav", "like"):
            bands[k][ax].append(r[ax])
    out = {}
    for k, d in bands.items():
        out[k] = {ax: sorted(d[ax]) for ax in ("coin", "fav", "like")}
    return out


def pct_of(arr, x):
    if not arr:
        return None
    lo = sum(1 for a in arr if a < x)
    return lo / max(1, len(arr) - 1) if len(arr) > 1 else 0.5


def near_a(r):
    """擦边边缘·赞未过线：币<2% 藏>10% 赞率(12%,20%]。"""
    return r["coin_rate"] < 0.02 and r["fav_rate"] > 0.10 and 0.12 < r["like_rate"] <= 0.20


def near_b(r):
    """点赞机器型：赞>20% 币<2% 但藏≤10%（收藏轴弱，不像擦边）。"""
    return r["like_rate"] > 0.20 and r["coin_rate"] < 0.02 and r["fav_rate"] <= 0.10


def near_c(r):
    """币率贴线：赞>20% 藏>10% 币率[2%,4%)。"""
    return r["like_rate"] > 0.20 and 0.02 <= r["coin_rate"] < 0.04 and r["fav_rate"] > 0.10


def weakest_ratio(r):
    """三条件中最贴线的一条（相对值，1.0=恰好压线），冤枉风险指标。"""
    cands = [(r["like_rate"] / 0.20, "赞率"), (r["coin_rate"] / 0.02, "币率"), (r["fav_rate"] / 0.10, "藏率")]
    return min(cands)  # (ratio, dim)


def main():
    cli = BiliClient(interval=0.6)
    baseline, n_home = load_pop()
    bands = bands_of(baseline)
    print(f"[base] 参照人口 {len(baseline)} 支（首页域 {n_home}，零请求）", flush=True)

    scored = {}
    seen = set()

    def score(item, layer, src, frm):
        bvid = item.get("bvid")
        if not bvid or bvid in seen:
            return None
        seen.add(bvid)
        st = item.get("stat") or {}
        view = st.get("view") or item.get("view") or 0
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
        dur = item.get("duration") or 0
        title = item.get("title") or ""
        owner = item.get("owner") or {}
        tier, firings = _rules.v3_tier(p_coin if p_coin is not None else 0, dur, fr, cr, lr, title)
        rec = {"bvid": bvid, "aid": item.get("aid"), "title": title,
               "owner": owner.get("name") if isinstance(owner, dict) else (owner or "?"),
               "mid": owner.get("mid") if isinstance(owner, dict) else None,
               "tname": item.get("tname") or "", "dur": dur, "view": view,
               "coin": coin, "fav": fav, "like": like,
               "like_rate": round(lr, 4), "coin_rate": round(cr, 4), "fav_rate": round(fr, 4),
               "r4": r4, "r8": like / max(1, coin) > 50,
               "layer": layer, "src": src, "from": frm,
               "p_coin": p_coin, "tier": tier, "firings": firings}
        scored[bvid] = rec
        return rec

    # ---- L0 首页热门 ----
    pop_calls = 0
    seeds = []
    for rnd, pages in ((1, 12), (2, 8)):
        if seeds:
            break
        for pn in range(1, pages + 1):
            pop_calls += 1
            try:
                d = cli.get_json("https://api.bilibili.com/x/web-interface/popular",
                                 {"ps": 20, "pn": pn}, tries=2)
                items = (d or {}).get("list") or []
            except Exception as e:
                print(f"[pop] r{rnd} pn={pn} fail: {str(e)[:50]}", flush=True)
                continue
            n0 = len(scored)
            for it in items:
                rec = score(it, 0, "popular", None)
                if rec and rec["r4"]:
                    seeds.append(rec["bvid"])
                    print(f"  [R4✓ L0] {rec['title'][:36]} 赞{rec['like_rate']:.1%} 币{rec['coin_rate']:.1%} 藏{rec['fav_rate']:.1%}", flush=True)
            print(f"[pop] r{rnd} pn={pn} 新入册{len(scored) - n0} R4累计{len(seeds)}", flush=True)

    degraded = False
    seeds = list(dict.fromkeys(seeds))
    if not seeds:
        # 无 R4 命中：用边缘样本（NM-A：赞率贴线）测边界
        degraded = True
        cand = [r for r in scored.values() if near_a(r)]
        cand.sort(key=lambda r: -r["like_rate"])
        seeds = [r["bvid"] for r in cand[:3]]
        print(f"[warn] L0 无 R4 命中，降级用 NM-A 边缘种子 {len(seeds)} 支", flush=True)

    # ---- L1/L2 一条龙 ----
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

    for sbv in seeds[:MAX_SEEDS]:
        srec = scored[sbv]
        ch = {"seed": sbv, "l1_n": 0, "l1_hits": [], "l1_near": 0, "l2": []}
        items = fetch_related(srec.get("aid")) or []
        for it in items:
            r = score(it, 1, "related", sbv)
            if not r:
                continue
            ch["l1_n"] += 1
            if r["r4"]:
                ch["l1_hits"].append(r["bvid"])
                print(f"  [R4✓ L1] {r['title'][:34]} 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%}", flush=True)
            elif near_a(r) or near_b(r) or near_c(r):
                ch["l1_near"] += 1
        for hb in sorted(ch["l1_hits"], key=lambda b: -scored[b]["like_rate"])[:L2_PER_CHAIN]:
            items2 = fetch_related(scored[hb].get("aid")) or []
            h2 = []
            for it in items2:
                r = score(it, 2, "related", hb)
                if r and r["r4"]:
                    h2.append(r["bvid"])
                    print(f"  [R4✓ L2] {r['title'][:34]} 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%}", flush=True)
            ch["l2"].append({"node": hb, "hits": h2, "n": len(items2)})
        chains.append(ch)
        l2h = sum(len(x["hits"]) for x in ch["l2"])
        print(f"[chain] 种子{sbv}《{srec['title'][:26]}》 L1 {len(ch['l1_hits'])}/{ch['l1_n']} 边缘{ch['l1_near']} | L2 {l2h}", flush=True)

    # ---- 汇总 ----
    all_r4 = [r for r in scored.values() if r["r4"]]
    nm_a = [r for r in scored.values() if near_a(r)]
    nm_b = [r for r in scored.values() if near_b(r)]
    nm_c = [r for r in scored.values() if near_c(r)]
    hist = defaultdict(int)
    n_arch = 0
    for r in scored.values():
        if r["coin_rate"] < 0.02 and r["fav_rate"] > 0.10:
            n_arch += 1
            lr = r["like_rate"]
            key = ("<5%" if lr < 0.05 else "5-10%" if lr < 0.10 else
                   "10-15%" if lr < 0.15 else "15-20%" if lr <= 0.20 else
                   "20-30%" if lr < 0.30 else ">30%")
            hist[key] += 1

    print("\n=== 摘要 ===", flush=True)
    print(f"L0扫过 {pop_calls} 页 / related {rel_calls} 次 / 入册 {len(scored)} 支（view>={VIEW_FLOOR}）", flush=True)
    print(f"R4 命中 {len(all_r4)} 条（L0 {sum(1 for r in all_r4 if r['layer']==0)} / L1 {sum(1 for r in all_r4 if r['layer']==1)} / L2 {sum(1 for r in all_r4 if r['layer']==2)}）", flush=True)
    print(f"边缘样本 NM-A赞未过线 {len(nm_a)} | NM-B藏不够 {len(nm_b)} | NM-C币贴线 {len(nm_c)}", flush=True)
    print(f"档案型（币<2%藏>10%）{n_arch} 支的赞率分布: {dict(hist)}", flush=True)

    out = {"meta": {"date": DATE, "pop_calls": pop_calls, "rel_calls": rel_calls,
                    "n_scored": len(scored), "n_seeds": len(seeds[:MAX_SEEDS]), "degraded": degraded,
                    "n_r4": len(all_r4)},
           "seeds": seeds[:MAX_SEEDS], "chains": chains,
           "r4_hits": sorted(all_r4, key=lambda r: weakest_ratio(r)[0]),
           "nearmiss": {"A_like_under": [r["bvid"] for r in nm_a],
                        "B_fav_under": [r["bvid"] for r in nm_b],
                        "C_coin_marginal": [r["bvid"] for r in nm_c]},
           "hist_archive_type": dict(hist), "n_archive_type": n_arch,
           "scored": list(scored.values())}
    path = os.path.join(MINE, f"r4_edgehunt_{DATE}.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[done] -> {path}", flush=True)


if __name__ == "__main__":
    main()
