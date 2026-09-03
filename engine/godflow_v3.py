# -*- coding: utf-8 -*-
"""godflow v3 —— 纵深流变体：神=0 才剪（1 个神作也续流）。

Elabation 指令（2026-09-04 凌晨）：v2 的「不足 2 即剪」放宽为「神=0 再死」——
  · 神作 >=2：随机抽 2（同 v2）
  · 神作 ==1：选这 1 个，前沿缩到 1，续流
  · 神作 ==0：剪（断供）
  · 深度上限 15、预算 related<=160——看链到底能流多少层
种子同源（v1.pick_seeds）；其余口径（v3 判档/门类/pubdate/匿名通道）与 v2 一致。
输出：data/flow_graph/godflowdeep_<ts>.json（immutable，version=godflow-deep-v2）
"""
import json
import os
import random
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

random.seed(20260905)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402
from godflow_v1 import band_pct, v3_tier, categorize, pick_seeds, OUTDIR  # noqa: E402

DEPTH_CAP = 15
FRONTIER = 2
REQ_BUDGET = 160


class DeepFlow0:
    def __init__(self, cli, seed, budget):
        self.cli = cli
        self.seed = seed
        self.budget = budget
        self.nodes = {}
        self.edges = []
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
        st = {"bvid": bvid, "title": (title or "")[:42], "view": view, "dur": dur,
              "fav_rate": round(fr, 5), "coin_rate": round(cr, 5), "like_rate": round(lr, 5),
              "coin_pct": None if pct is None else round(pct, 4), "tier": tier,
              "rules": firings, "category": bucket, "cat_src": csrc, "hop": hop,
              "parent": parent, "pubdate": pubdate, "arm": "deep0", "flow_seed": self.seed["bvid"]}
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
                    self.hops.append({"hop": hop, "expand_fail": str(err)[:60], "parent": bvid})
                    continue
                for it in items:
                    cb = it.get("bvid")
                    if not cb:
                        continue
                    cst = it.get("stat") or {}
                    n_neigh += 1
                    self.edges.append({"src": bvid, "dst": cb, "hop": hop})
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
                       "selected": [], "pruned": None}
            if len(pool) < 1:
                hop_rec["pruned"] = "神=0 断供"
                self.hops.append(hop_rec)
                self.status, self.prune = "pruned", {"hop": hop, "reason": "神=0 断供"}
                break
            sel = random.sample(pool, min(FRONTIER, len(pool)))
            hop_rec["selected"] = [p["bvid"] for p in sel]
            self.hops.append(hop_rec)
            if hop == DEPTH_CAP:
                self.status = "censored_depth"
                break
            frontier = [(p["bvid"], p.get("aid")) for p in sel]
        if self.status == "running":
            self.status = "censored_depth"
        self.n_god_total = sum(1 for n in self.nodes.values() if n["tier"] == "神作候选")
        by_hop = {h: s for h, s in [(hh["hop"], hh.get("selected") or []) for hh in self.hops]}
        seen = set()
        self.chain = []
        for hop in sorted(by_hop):
            for b in by_hop[hop]:
                if b not in seen:
                    seen.add(b)
                    n = self.nodes.get(b) or {}
                    self.chain.append({"hop": hop, "bvid": b, "pubdate": n.get("pubdate"),
                                       "title": (n.get("title") or "")[:24]})


def main():
    cli = BiliClient(interval=0.8)
    budget = {"related": 0}
    seeds = pick_seeds()
    print("[seeds] 纵深·剪@0 变体，同 5 种子：")
    for s in seeds:
        print(f"   · [{s['bucket']}] {s['title'][:32]} {s['bvid']}")
    run = {"meta": {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "version": "godflow-deep-v2 (剪@0)",
                    "depth_cap": DEPTH_CAP, "frontier": FRONTIER, "budget": REQ_BUDGET,
                    "pubdate_available": True, "requests": budget},
           "seeds": seeds, "flows": []}
    consec_fail = 0
    for seed in seeds:
        if budget["related"] >= REQ_BUDGET or consec_fail >= 15:
            break
        print(f"\n[flow] deep0 ← {seed['bucket']} {seed['title'][:30]}")
        time.sleep(2.5)
        f = DeepFlow0(cli, seed, budget)
        f.run()
        consec_fail = consec_fail + 1 if f.status == "seed_fail" else 0
        depth = len([h for h in f.hops if "n_neighbors" in h])
        print(f"   状态={f.status} 深度={depth} 节点={len(f.nodes)} 神作={f.n_god_total} 请求={budget['related']}"
              + (f" 剪因={f.prune['reason']}" if f.prune else ""))
        for h in f.hops:
            if "n_neighbors" in h:
                tail = f" 剪:{h['pruned']}" if h.get("pruned") else ""
                print(f"   hop{h['hop']}: 邻居{h['n_neighbors']} 神{h['n_gods']} 选{len(h['selected'])}{tail}")
        run["flows"].append({"seed": seed, "status": f.status, "prune": f.prune, "hops": f.hops,
                             "nodes": list(f.nodes.values()), "edges": f.edges,
                             "chain": f.chain, "n_god_total": f.n_god_total})
    out = os.path.join(OUTDIR, f"godflowdeep_{time.strftime('%Y%m%d_%H%M%S')}.json")
    json.dump(run, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n[done] -> {out}")
    print("[depths] " + " | ".join(
        f"{fl['seed']['bucket']}:{len([h for h in fl['hops'] if 'n_neighbors' in h])}层({fl['status']})"
        for fl in run["flows"]))


if __name__ == "__main__":
    main()
