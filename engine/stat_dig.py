# -*- coding: utf-8 -*-
"""统计学家夜班 · 疑点攻坚（2026-09-03 午）——零请求纯本地统计。

疑点1  hop3 反增（29.6% vs 臂① 25.3%）：用户级 MWU + 自助法 CI
疑点2  工程链探针 41.9%（7 用户）：逐用户解剖——金簇还是噪声
疑点3  认证效应：流收获神作的 CBI 分布 vs 神作库总体（补足池并非中性）
疑点4  全库二部图入度分布：汇流稀疏是采样粒度还是结构问题
疑点5  hop4 21.6%：用户级自助法 CI——聚簇噪声内还是真衰减
输出：data/fav_mine/stat_dig_summary.json
"""
import json
import math
import os
import random
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cbi_scale import tier_of, SCALE  # noqa: E402
from fav_miner import f7_of, cbi_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
B = 4000  # 自助法重采样次数
random.seed(20260903)


def load(fn):
    return json.load(open(os.path.join(MINE, fn), encoding="utf-8"))


def mwu_u(x, y):
    """Mann-Whitney U（正态近似，单尾 H1: x>y）。返回 (z, p)。"""
    n1, n2 = len(x), len(y)
    if n1 < 5 or n2 < 5:
        return None, None
    allv = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks, i = [0.0] * len(allv), 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        avg = (i + j - 1) / 2 + 1
        for t in range(i, j):
            ranks[t] = avg
        i = j
    r1 = sum(r for r, (_, g) in zip(ranks, allv) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    sig = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (u1 - mu) / sig if sig else 0.0
    return round(z, 3), 0.5 * math.erfc(z / math.sqrt(2))


def user_rates(payload, min_v=5):
    """payload -> {user_hash: (god_rate, n_qual)}（合格视频≥min_v 的用户）。"""
    by_u = defaultdict(list)
    for v in (payload.get("videos") or []):
        if (v.get("view") or 0) >= 3000:
            by_u[v.get("from_user")].append(v)
    out = {}
    for u, vs in by_u.items():
        if len(vs) >= min_v:
            out[u] = (sum(1 for v in vs if v["tier"] == "high") / len(vs), len(vs))
    return out


def pooled_rate(payload):
    vids = [v for v in (payload.get("videos") or []) if (v.get("view") or 0) >= 3000]
    g = sum(1 for v in vids if v["tier"] == "high")
    return g, len(vids)


def boot_ci(payload, b=B):
    """用户级自助法：重采样用户（保持整簇），给出视频池神作率的 95% CI。"""
    by_u = defaultdict(list)
    for v in (payload.get("videos") or []):
        if (v.get("view") or 0) >= 3000:
            by_u[v.get("from_user")].append(v)
    clusters = list(by_u.values())
    if not clusters:
        return None, None, None
    stats = []
    for _ in range(b):
        g = n = 0
        for _ in clusters:
            c = clusters[random.randrange(len(clusters))]
            n += len(c)
            g += sum(1 for v in c if v["tier"] == "high")
        stats.append(g / max(1, n))
    stats.sort()
    mean = sum(stats) / len(stats)
    lo, hi = stats[int(0.025 * b)], stats[int(0.975 * b) - 1]
    return round(mean, 3), round(lo, 3), round(hi, 3)


def main():
    out = {}
    arm1 = load("favmine_20260903_102226.json")
    f2 = load("favmine_flowH2_20260903_113231.json")
    f3 = load("favmine_flowH3_20260903_114437.json")
    f4 = load("favmine_flowH4_20260903_115415.json")
    eng = load("favmine_flowH2_20260903_120735.json")

    # ── 疑点1: hop3 反增的显著性 ──
    r1, r2, r3 = user_rates(arm1), user_rates(f2), user_rates(f3)
    rates1 = [r for r, _ in r1.values()]
    rates3 = [r for r, _ in r3.values()]
    z, p = mwu_u(rates3, rates1)
    out["Q1_hop3_vs_arm1"] = {"n_hop3": len(rates3), "n_arm1": len(rates1),
                              "mean_hop3": round(sum(rates3) / len(rates3), 3),
                              "mean_arm1": round(sum(rates1) / len(rates1), 3),
                              "mwu_z": z, "p_one": p}
    g2, n2 = pooled_rate(f2)
    g3, n3 = pooled_rate(f3)
    g1, n1 = pooled_rate(arm1)
    out["Q1_bootstrap"] = {"hop1": boot_ci(arm1), "hop2": boot_ci(f2), "hop3": boot_ci(f3), "hop4": boot_ci(f4)}
    print(f"[疑点1] hop3 vs 臂① 用户级 MWU：n={len(rates3)}/{len(rates1)} "
          f"均值 {out['Q1_hop3_vs_arm1']['mean_hop3']} vs {out['Q1_hop3_vs_arm1']['mean_arm1']} "
          f"z={z} p={p}")
    print(f"[疑点1] 用户级自助法 95%CI：hop1={out['Q1_bootstrap']['hop1']} "
          f"hop2={out['Q1_bootstrap']['hop2']} hop3={out['Q1_bootstrap']['hop3']} "
          f"hop4={out['Q1_bootstrap']['hop4']}")

    # ── 疑点5: hop4 在聚簇噪声内吗（hop3 CI 是否覆盖 hop4 点估计）──
    _, lo3, hi3 = out["Q1_bootstrap"]["hop3"]
    g4, n4 = pooled_rate(f4)
    r4 = g4 / max(1, n4)
    out["Q5_hop4_in_noise"] = {"hop4_rate": round(r4, 3), "hop3_ci": [lo3, hi3],
                               "in_ci": bool(lo3 <= r4 <= hi3)}
    print(f"[疑点5] hop4={r4:.3f} 是否落入 hop3 自助CI [{lo3},{hi3}]："
          f"{out['Q5_hop4_in_noise']['in_ci']}")

    # ── 疑点2: 探针组逐用户解剖 ──
    probe = {}
    for u in (eng.get("users") or []):
        if u.get("probe"):
            probe.setdefault(u["user_hash"], {"strength": u.get("flow_strength")})
    by_u = defaultdict(list)
    for v in (eng.get("videos") or []):
        if (v.get("view") or 0) >= 3000 and v.get("from_user") in probe:
            by_u[v["from_user"]].append(v)
    rows = []
    for uh, vs in sorted(by_u.items(), key=lambda kv: -len(kv[1])):
        god = sum(1 for v in vs if v["tier"] == "high")
        rows.append({"user": uh[:8], "n": len(vs), "god": god,
                     "rate": round(god / len(vs), 3), "strength": probe[uh]["strength"]})
    out["Q2_probe_anatomy"] = rows
    top1 = rows[0] if rows else {}
    print(f"[疑点2] 探针组 {len(rows)} 用户：top={rows[:3]}")
    # 金簇集中度：去掉最高产的 1 用户后探针率
    if rows:
        rest_g = sum(r["god"] for r in rows[1:])
        rest_n = sum(r["n"] for r in rows[1:])
        out["Q2_probe_minus_top1"] = {"rate": round(rest_g / max(1, rest_n), 3), "n": rest_n}
        print(f"[疑点2] 去掉 top1 用户后探针率：{out['Q2_probe_minus_top1']['rate']}（n={rest_n}）")

    # ── 疑点3: 认证效应——臂①收获神作 CBI vs 神作库总体 CBI ──
    harvest = [v["cbi"] for v in (arm1.get("videos") or [])
               if (v.get("view") or 0) >= 3000 and v["tier"] == "high"]
    lib = []
    for fn in os.listdir(SDIR):
        if (fn.startswith("sample_") or fn.startswith("ecosystem_")) and fn.endswith(".json") \
                and not fn.endswith("_scored.json"):
            try:
                for v in json.load(open(os.path.join(SDIR, fn), encoding="utf-8")).get("videos") or []:
                    st = v.get("stat") or {}
                    view = st.get("view") or 0
                    if view >= 3000:
                        c = cbi_of(f7_of(st), view)
                        if c >= SCALE["high"]:
                            lib.append(round(c, 3))
            except Exception:
                continue
    z3, p3 = mwu_u(harvest, lib)
    out["Q3_certification"] = {"harvest_n": len(harvest), "harvest_mean": round(sum(harvest) / max(1, len(harvest)), 3),
                               "lib_n": len(lib), "lib_mean": round(sum(lib) / max(1, len(lib)), 3),
                               "mwu_z": z3, "p_one": p3}
    print(f"[疑点3] 认证效应：臂①收获神作 CBI 均值 {out['Q3_certification']['harvest_mean']}（n={len(harvest)}）"
          f" vs 神作库总体 {out['Q3_certification']['lib_mean']}（n={len(lib)}） z={z3} p={p3}")

    # ── 疑点4(修正版): 真实二部图入度——必须从原始档案取边！
    #    merged 的 bvid 去重会把「多收藏者」压扁成单 from_user（§4.6 树vs图分野的现形记）──
    edges = defaultdict(set)
    tier_by_bv = {}
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn \
                and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                if (v.get("view") or 0) >= 3000 and v.get("from_user") and v.get("bvid"):
                    edges[v["bvid"]].add(v["from_user"])
                    tier_by_bv[v["bvid"]] = tier_of(v.get("cbi", 0), v.get("view") or 0)
    dist = defaultdict(int)
    high_dist = defaultdict(int)
    for b, us in edges.items():
        k = min(len(us), 6)
        dist[k] += 1
        if tier_by_bv.get(b) == "high":
            high_dist[k] += 1
    multi = sum(v for k, v in dist.items() if k >= 2)
    out["Q4_inflow_dist_raw"] = {"all": dict(sorted(dist.items())),
                                 "high": dict(sorted(high_dist.items())),
                                 "n_videos_multi": multi,
                                 "note": "从原始档案边集计算（merged 去重会抹掉汇流结构）"}
    print(f"[疑点4-修正] 真实入度分布（cap6）：{dict(sorted(dist.items()))}；"
          f"入度≥2 的视频 {multi} 个；神作侧 {dict(sorted(high_dist.items()))}")

    # ── Q6: 播种响应曲线——用户所评种子的 CBI（=单人用户的强度）分带 × 神作率 ──
    bands = [(3.0, 4.0), (4.0, 6.0), (6.0, 9.0), (9.0, 12.0), (12.0, 999.0)]
    all_users = {}
    for tag, payload in (("hop2", f2), ("hop3", f3), ("hop4", f4), ("eng", eng)):
        st = {}
        for u in (payload.get("users") or []):
            st.setdefault(u["user_hash"], u.get("flow_strength"))
        by_u = defaultdict(list)
        for v in (payload.get("videos") or []):
            if (v.get("view") or 0) >= 3000:
                by_u[v.get("from_user")].append(v)
        for uh, vs in by_u.items():
            god = sum(1 for v in vs if v["tier"] == "high")
            if uh in all_users:
                all_users[uh]["god"] += god
                all_users[uh]["n"] += len(vs)
            else:
                all_users[uh] = {"strength": st.get(uh), "god": god, "n": len(vs)}
    q6 = []
    for lo, hi in bands:
        sel = [u for u in all_users.values() if u["strength"] and lo <= u["strength"] < hi]
        n_v = sum(u["n"] for u in sel)
        g = sum(u["god"] for u in sel)
        q6.append({"band": f"[{lo},{hi if hi < 999 else '∞'})", "users": len(sel),
                   "videos": n_v, "god_rate": round(g / max(1, n_v), 3)})
    out["Q6_seeding_response"] = q6
    print(f"[Q6] 播种响应曲线（种子CBI带 × 神作率）：{[(r['band'], r['god_rate'], r['users']) for r in q6]}")

    json.dump(out, open(os.path.join(MINE, "stat_dig_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("[done] -> data/fav_mine/stat_dig_summary.json")


if __name__ == "__main__":
    main()
