# -*- coding: utf-8 -*-
"""godflow v5 —— E 臂：回溯定向流（时光倒流）。

Elabation 设计（2026-09-04 凌晨）：
  · 前沿 2，神=0 才死；神冗余时选发布时间更早的神——链沿深度向历史沉底
  · 10 个新种子（round2 其余确认神作 6 + 参照库高分诚意神作 4，避开旧 5 种子）
  · 每跳记录完整候选团（神作池按 pubdate 升序），供交互式展开查看「当时如何选」
  · 深度上限 25、预算 related<=260（加大）；匿名通道
输出：data/flow_graph/godflowretro_<ts>.json（immutable）
"""
import json
import math
import os
import random
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

random.seed(20260907)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402
from godflow_v1 import (BANDS, band_pct, v3_tier, categorize, pick_seeds,  # noqa: E402
                        OUTDIR, MINE, SDIR)

DEPTH_CAP = 25
FRONTIER = 2
REQ_BUDGET = 260
SINC_P50 = 0.202  # 神作诚意比中位（diag_sincerity）
OLD_SEEDS = {"BV11bAUzBEqG", "BV1jQ87ziEKZ", "BV147411K7xu", "BV1GS411P74t", "BV1UJ41147Ej"}


def pick_seeds10():
    """6 个 round2 剩余确认神作 + 4 个参照库高诚意神作（跨门类）。"""
    rows = json.load(open(os.path.join(MINE, "round2_labels.json"), encoding="utf-8"))["rows"]
    gods = [r for r in rows if r.get("v3") == "神作" and r.get("bvid") and r["bvid"] not in OLD_SEEDS]
    seeds, used = [], set()
    for r in sorted(gods, key=lambda r: -float(r.get("coin_pct") or 0))[:6]:
        bucket, _ = categorize(r.get("title") or "", None)
        seeds.append({"bvid": r["bvid"], "title": r.get("title") or "?", "bucket": bucket,
                      "coin_pct": r.get("coin_pct"), "src": "round2"})
        used.add(r["bvid"])
    # 参照库补 4：v3 神 + 诚意比达标，按门类分散
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
                pop.setdefault(v["bvid"], {"title": v.get("title") or "", "view": vw, "stat": st})
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                vw = v.get("view") or 0
                if vw >= 3000 and v.get("bvid") and v["bvid"] not in pop:
                    pop[v["bvid"]] = {"title": v.get("title") or "", "view": vw, "stat": v.get("stat") or {}}
    cands = []
    for b, r in pop.items():
        st = r["stat"]
        vw = max(1, r["view"])
        cr, fr = (st.get("coin") or 0) / vw, (st.get("favorite") or 0) / vw
        pct = band_pct(r["view"], cr)
        if pct is None or pct < 0.93:
            continue
        if fr > 0 and cr / fr > 0.202:
            continue
        if b in used or b in OLD_SEEDS:
            continue
        bucket, _ = categorize(r["title"], None)
        cands.append({"bvid": b, "title": r["title"], "bucket": bucket, "coin_pct": round(pct, 3),
                      "src": "refdb", "sinc": round(cr / max(1, fr), 3)})
    by_bucket = {}
    for c in sorted(cands, key=lambda c: -c["coin_pct"]):
        if c["bucket"] not in by_bucket:
            by_bucket[c["bucket"]] = c
    covered = {s["bucket"] for s in seeds}
    for bucket, c in sorted(by_bucket.items(), key=lambda kv: -kv[1]["coin_pct"]):
        if len(seeds) == 10:
            break
        if bucket in covered:
            continue
        seeds.append(c)
        used.add(c["bvid"])
        covered.add(bucket)
    for c in sorted(cands, key=lambda c: -c["coin_pct"]):
        if len(seeds) == 10:
            break
        if c["bvid"] not in used:
            seeds.append(c)
            used.add(c["bvid"])
    return seeds


def brief(rec):
    return {"bvid": rec["bvid"], "title": rec["title"], "pubdate": rec.get("pubdate"),
            "coin_pct": rec["coin_pct"], "view": rec["view"]}


class RetroFlow:
    def __init__(self, cli, seed, budget):
        self.cli = cli
        self.seed = seed
        self.budget = budget
        self.nodes = {}
        self.hops = []
        self.status = "running"
        self.prune = None
        self.visited = set()
        self.n_god_total = 0

    def rec(self, bvid, title, view, dur, fav, coin, like, hop, parent, tname, pubdate):
        st = self.nodes.get(bvid)
        if st:
            return st
        vr = max(1, view)
        fr, cr, lr = fav / vr, coin / vr, like / vr
        pct = band_pct(view, cr)
        tier, firings = v3_tier(pct, dur, fr, cr, lr, title)
        bucket, csrc = categorize(title, tname)
        st = {"bvid": bvid, "title": (title or "")[:60], "view": view, "dur": dur,
              "fav_rate": round(fr, 5), "coin_rate": round(cr, 5), "like_rate": round(lr, 5),
              "coin_pct": None if pct is None else round(pct, 4), "tier": tier,
              "category": bucket, "hop": hop, "parent": parent, "pubdate": pubdate,
              "arm": "retro", "flow_seed": self.seed["bvid"]}
        self.nodes[bvid] = st
        return st

    def expand(self, bvid, aid):
        self.budget["related"] += 1
        items, err = None, None
        for wait in (0, 2):
            if wait:
                time.sleep(wait)
            try:
                d = self.cli.get_json("https://api.bilibili.com/x/web-interface/archive/related",
                                      {"aid": aid, "related": "true"}, tries=1)
                items = d if isinstance(d, list) else []
                err = None
                break
            except Exception as e:
                items, err = None, str(e)
        return items, err

    def run(self):
        v = None
        last_err = ""
        for wait in (0, 2, 4):
            if wait:
                time.sleep(wait)
            try:
                v = self.cli.fetch_view(self.seed["bvid"])
                break
            except Exception as e:
                last_err = str(e)
        if v is None:
            self.status, self.prune = "seed_fail", {"reason": f"fetch_view x3: {last_err}"}
            return
        aid = v.get("aid") or (v.get("stat") or {}).get("aid") or v.get("id")
        st = v.get("stat") or {}
        self.budget["related"] += 1
        seed_rec = self.rec(self.seed["bvid"], v.get("title"), st.get("view") or 0, v.get("duration") or 0,
                            st.get("favorite") or 0, st.get("coin") or 0, st.get("like") or 0, 0, None,
                            v.get("tname") or None, v.get("pubdate"))
        seed_rec["seed"] = True
        self.visited.add(self.seed["bvid"])
        frontier = [(self.seed["bvid"], aid)]
        for hop in range(1, DEPTH_CAP + 1):
            if self.budget["related"] >= REQ_BUDGET:
                self.status = "censored_budget"
                break
            n_neigh, pool = 0, []
            for bvid, a in frontier:
                if self.budget["related"] >= REQ_BUDGET:
                    break
                items, err = self.expand(bvid, a)
                if items is None:
                    self.hops.append({"hop": hop, "expand_fail": str(err)[:60]})
                    continue
                for it in items:
                    cb = it.get("bvid")
                    if not cb:
                        continue
                    cst = it.get("stat") or {}
                    n_neigh += 1
                    if cb in self.visited:
                        continue
                    self.visited.add(cb)
                    rec = self.rec(cb, it.get("title"), cst.get("view") or 0, it.get("duration") or 0,
                                   cst.get("favorite") or 0, cst.get("coin") or 0, cst.get("like") or 0,
                                   hop, bvid, it.get("tname") or None, it.get("pubdate"))
                    rec["aid"] = it.get("aid")
                    if rec["tier"] == "神作候选":
                        pool.append(rec)
            hop_rec = {"hop": hop, "n_neighbors": n_neigh, "n_gods": len(pool),
                       "candidates": [brief(p) for p in sorted(pool, key=lambda p: (p.get("pubdate") or 0))],
                       "selected": [], "pruned": None}
            if not pool:
                hop_rec["pruned"] = "神=0 断供"
                self.hops.append(hop_rec)
                self.status, self.prune = "pruned", {"hop": hop, "reason": "神=0 断供"}
                break
            sel = sorted(pool, key=lambda p: (p.get("pubdate") or 0))[:FRONTIER]  # 时间更早优先
            hop_rec["selected"] = [brief(p) for p in sel]
            self.hops.append(hop_rec)
            if hop == DEPTH_CAP:
                self.status = "censored_depth"
                break
            frontier = [(p["bvid"], p.get("aid")) for p in sel]
        if self.status == "running":
            self.status = "censored_depth"
        self.n_god_total = sum(1 for n in self.nodes.values() if n["tier"] == "神作候选")


def main():
    cli = BiliClient(interval=0.8)
    budget = {"related": 0}
    seeds = pick_seeds10()
    print(f"[seeds] E 臂回溯定向，{len(seeds)} 个新种子：")
    for s in seeds:
        print(f"   · [{s['bucket']}] pct={s.get('coin_pct')} {s['title'][:32]} {s['bvid']} ({s['src']})")
    run = {"meta": {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "version": "godflow-retro-v1",
                    "depth_cap": DEPTH_CAP, "frontier": FRONTIER, "budget": REQ_BUDGET,
                    "rule": "frontier<=2, earliest-pubdate gods first, prune at gods=0",
                    "requests": budget},
           "seeds": seeds, "flows": []}
    consec_fail = 0
    for seed in seeds:
        if budget["related"] >= REQ_BUDGET or consec_fail >= 15:
            break
        print(f"\n[flow] retro ← {seed['bucket']} {seed['title'][:30]}")
        time.sleep(2.0)
        f = RetroFlow(cli, seed, budget)
        f.run()
        consec_fail = consec_fail + 1 if f.status == "seed_fail" else 0
        depth = len([h for h in f.hops if "n_neighbors" in h])
        ch = [s for h in f.hops for s in h.get("selected") or [] if s.get("pubdate")]
        span = ""
        if ch:
            ds = [c["pubdate"] for c in ch]
            span = f"{time.strftime('%Y-%m', time.localtime(min(ds)))} ~ {time.strftime('%Y-%m', time.localtime(max(ds)))}"
        print(f"   状态={f.status} 深度={depth} 节点={len(f.nodes)} 神作={f.n_god_total} 请求={budget['related']} 跨度={span}"
              + (f" 剪因={f.prune['reason']}" if f.prune else ""))
        for h in f.hops:
            if "n_neighbors" in h:
                tail = f" 剪:{h['pruned']}" if h.get("pruned") else ""
                sel0 = h["selected"][0] if h["selected"] else None
                ym = time.strftime("%Y-%m", time.localtime(sel0["pubdate"])) if sel0 and sel0.get("pubdate") else "?"
                print(f"   hop{h['hop']}: 邻{h['n_neighbors']} 神{h['n_gods']} 选{len(h['selected'])} 最早={ym}{tail}")
        run["flows"].append({"seed": seed, "status": f.status, "prune": f.prune, "hops": f.hops,
                             "nodes": list(f.nodes.values()), "n_god_total": f.n_god_total})
    out = os.path.join(OUTDIR, f"godflowretro_{time.strftime('%Y%m%d_%H%M%S')}.json")
    json.dump(run, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n[done] -> {out}")
    print("[depths] " + " | ".join(
        f"{fl['seed']['bucket']}:{len([h for h in fl['hops'] if 'n_neighbors' in h])}层({fl['status']})"
        for fl in run["flows"]))


if __name__ == "__main__":
    main()
