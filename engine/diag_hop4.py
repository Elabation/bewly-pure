# -*- coding: utf-8 -*-
"""hop4 雪崩归因诊断（2026-09-03，Elabation 提问触发）——零请求纯本地。

检验三个假设：
  H1 样本量少了          → 各跳合格视频数 / 用户数 / 每用户样本厚度
  H2 汇流强度降低        → 各跳种子里「真汇流(inflow>=2)」vs「随机补足」的数量 + 种子 CBI 分布
  H3 随机种子质量一般    → 各跳种子 CBI 均值/极值对比
附加检验：
  A 候选池同质化（dedupe 蚕食）→ 各跳候选 commenter 集合的两两重叠率（.flowmap.json）
  B hop4 分层对照 → 「汇流神作的评论者」vs「补足神作的评论者」的神作率对比
"""
import json
import os
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fav_mine")


def load(fn):
    return json.load(open(os.path.join(MINE, fn), encoding="utf-8"))


def raw_flow(hop, prefer_stamp=None):
    fs = [f for f in os.listdir(MINE) if f.startswith(f"favmine_flowH{hop}_") and f.endswith(".json")]
    if not fs:
        return None, None
    fs.sort()
    fn = fs[0] if len(fs) == 1 else (f"favmine_flowH{hop}_{prefer_stamp}.json" if prefer_stamp else fs[-1])
    return fn, load(fn)


def main():
    print("=== H2/H3: 种子构成与质量（per hop）===")
    seed_stats = {}
    for hop, summ_fn in ((2, "flow_h2_unbiased_summary.json"), (3, "flow_h3_summary.json"),
                         (4, "flow_h4_summary.json")):
        s = load(summ_fn)
        seeds = s.get("seeds") or []
        real = [g for g in seeds if (g.get("inflow") or 0) >= 2]
        fills = [g for g in seeds if (g.get("inflow") or 0) < 2]
        cbis = sorted((g.get("cbi") or 0) for g in seeds)
        seed_stats[hop] = seeds
        print(f"hop{hop}: 种子 {len(seeds)} | 真汇流 {len(real)} | 随机补足 {len(fills)} | "
              f"种子CBI mean={sum(cbis)/len(cbis):.2f} min={cbis[0]:.2f} max={cbis[-1]:.2f}")

    print("\n=== H1: 样本量与厚度（per hop）===")
    raws = {}
    for hop, stamp in ((2, "20260903_113231"), (3, "20260903_114437"), (4, "20260903_115415")):
        fn, p = raw_flow(hop, stamp)
        raws[hop] = p or {"users": [], "videos": []}
        vids = [v for v in p["videos"] if (v.get("view") or 0) >= 3000]
        by_u = defaultdict(list)
        for v in vids:
            by_u[v.get("from_user")].append(v)
        per_u = [len(vs) for vs in by_u.values()]
        gods = sum(1 for v in vids if v.get("tier") == "high")
        print(f"hop{hop}: 合格视频 {len(vids)} | 出贡献用户 {len(by_u)} | "
              f"每用户均 {sum(per_u)/max(1,len(per_u)):.1f} 条 | 神作率 {gods/max(1,len(vids)):.3f}")

    print("\n=== A: 候选池两两重叠（dedupe 蚕食证据）===")
    fm = load(".flowmap.json")
    cand = {}
    for hop in (2, 3, 4):
        m = fm.get(f"hop{hop}") or {}
        s = set()
        for bvid, users in m.items():
            s |= {u for u in (users or []) if u}
        cand[hop] = s
        print(f"hop{hop} 候选 commenter: {len(s)}")
    for a, b in ((2, 3), (3, 4), (2, 4)):
        inter = cand[a] & cand[b]
        print(f"hop{a}∩hop{b}: {len(inter)} 人（占 hop{b} 候选 {len(inter)/max(1,len(cand[b])):.1%}）")

    print("\n=== B: hop4 分层对照——汇流神作评论者 vs 补足神作评论者 ===")
    m4 = fm.get("hop4") or {}
    inflow_bvids = {g["bvid"] for g in seed_stats.get(4, []) if (g.get("inflow") or 0) >= 2}
    fill_bvids = {g["bvid"] for g in seed_stats.get(4, []) if (g.get("inflow") or 0) < 2}
    # 用户 → 是否为汇流神作评论者
    by_user_seeds = defaultdict(set)
    for bv, users in m4.items():
        for u in (users or []):
            if u:
                by_user_seeds[u].add(bv)
    # hop4 挖掘结果的用户级神作率
    vids4 = [v for v in raws[4]["videos"] if (v.get("view") or 0) >= 3000]
    by_u4 = defaultdict(list)
    for v in vids4:
        by_u4[v.get("from_user")].append(v)
    grp = {"inflow": [0, 0], "fill_only": [0, 0]}
    for u, vs in by_u4.items():
        seeds_touched = set()
        for bv, us in m4.items():
            if u in (us or []):
                seeds_touched.add(bv)
        key = "inflow" if (seeds_touched & inflow_bvids) else "fill_only"
        grp[key][0] += sum(1 for v in vs if v.get("tier") == "high")
        grp[key][1] += len(vs)
    for k, (h, n) in grp.items():
        print(f"hop4 [{k}] 神作 {h}/{n} = {h/max(1,n):.3f}")
    inflow_users = sum(1 for u in by_u4 if any(u in (m4.get(bv) or []) for bv in inflow_bvids))
    print(f"（hop4 挖掘用户中，评论过真汇流神作者的：{inflow_users} 人）")


if __name__ == "__main__":
    main()
