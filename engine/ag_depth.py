# -*- coding: utf-8 -*-
"""感谢几何 · AG-Depth 离线原型（验证 V2/V3，不含任何生产逻辑）

行为率向量 x = log(coin/view+eps), log(fav/view+eps), log(like/view+eps),
              log(danmaku/view+eps), log(share/view+eps)
邻域 N(v)：同来源组（挖掘库/对照组）内 log10(view) 桶(宽0.25) × 发布年代，
            至少 MIN_NB 个有效点，否则 AG=None。
AG(v) = max over u in U(38个方向) of 分位数( ⟨x_v-μ_N, u⟩ in {⟨x_i-μ_N, u⟩}_{i∈N∪{v}} )
正向校验：取最深方向 u*，要求 ⟨x_v-μ_N, u*⟩>0 且 x_v 至少两维原始率>0。

验证（文档 docs/appreciation-geometry.md §2）：
  V2 分歧集规模：AG≥0.95 且 CBI<1.0 的「AG独捞」占比应在 5-15%
  V3 刷量免疫：随机 20% 视频 coin×1.8，AG 排名提升幅度 < CBI 排名提升幅度
用法： python engine/ag_depth.py
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fav_miner import f7_of, cbi_of, load_merged_mine  # noqa: E402

EPS = 1e-4
MIN_VIEW = 3000
MIN_NB = 15
DIM_NAMES = ["coin", "fav", "like", "danmaku", "share"]
RNG = random.Random(20260902)


def feat_vec(stat):
    view = max(stat.get("view") or 0, 1)
    rates = [max(stat.get(k) or 0, 0) / view for k in DIM_NAMES]
    return [math.log(r + EPS) for r in rates]


def directions():
    ds = []
    for i in range(5):  # 坐标轴
        v = [0.0] * 5
        v[i] = 1.0
        ds.append(v)
    ds.append([1 / math.sqrt(5)] * 5)  # 均匀方向
    while len(ds) < 38:  # 固定种子随机方向
        v = [RNG.gauss(0, 1) for _ in range(5)]
        n = math.sqrt(sum(t * t for t in v))
        ds.append([t / n for t in v])
    return ds


DIRS = directions()


def pct_rank(sorted_vals, x):
    """x 在 sorted_vals 中的分位（0~1，越大越深）。"""
    lo, hi = 0, len(sorted_vals)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_vals[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return (lo + 1) / (len(sorted_vals) + 1)


def ag_depth(x, x_all):
    """x_all: 邻域内全部点（含自身，且自身必须在列表末尾）。"""
    if len(x_all) < MIN_NB + 1:
        return None, None
    n_dim = len(x)
    mu = [sum(p[i] for p in x_all) / len(x_all) for i in range(n_dim)]
    cent = [[p[i] - mu[i] for i in range(n_dim)] for p in x_all]
    proj = [[sum(cent[k][i] * u[i] for i in range(n_dim)) for u in DIRS] for k in range(len(x_all))]
    self_idx = len(x_all) - 1
    best_d, best_u = 0.0, None
    for ui in range(len(DIRS)):
        col = sorted(proj[k][ui] for k in range(len(x_all)) if k != self_idx)
        d = pct_rank(col, proj[self_idx][ui])
        if d > best_d:
            best_d, best_u = d, ui
    u_star = DIRS[best_u]
    shift = proj[self_idx][best_u]
    if shift <= 0:  # 反向边缘 = 不是神作方向
        return 0.0, best_u
    return best_d, best_u


def build_points():
    """挖掘库 + 对照组 → 统一点集。"""
    pts = []
    merged = load_merged_mine(os.path.join(ROOT, "data", "fav_mine"))
    for v in merged["videos"]:
        if not (v.get("stat") or {}).get("view"):  # 旧轮次无原始 stat，跳过
            continue
        pts.append({"src": "mined", "bvid": v["bvid"], "title": v.get("title"),
                    "year": v.get("year"), "stat": v["stat"]})
    sdir = os.path.join(ROOT, "data", "samples")
    for fn in sorted(os.listdir(sdir)):
        if fn.startswith("sample_") and fn.endswith(".json"):
            try:
                for v in (json.load(open(os.path.join(sdir, fn), encoding="utf-8")).get("videos") or []):
                    if v.get("bvid") and v.get("stat"):
                        pts.append({"src": "ctrl", "bvid": v["bvid"], "title": v.get("title"),
                                    "year": (time.strftime("%Y", time.localtime(v["pubdate"]))
                                             if v.get("pubdate") else "?"),
                                    "stat": v["stat"]})
            except Exception:
                continue
    # 去重 + 有效过滤
    out, seen = [], set()
    for p in pts:
        if p["bvid"] in seen or (p["stat"].get("view") or 0) < MIN_VIEW:
            continue
        if not any((p["stat"].get(k) or 0) > 0 for k in ("coin", "fav", "like")):
            continue
        seen.add(p["bvid"])
        p["x"] = feat_vec(p["stat"])
        p["f7"] = f7_of(p["stat"])
        p["cbi"] = cbi_of(p["f7"], p["stat"]["view"])
        out.append(p)
    return out


def main():
    pts = build_points()
    print(f"[points] total={len(pts)}  mined={sum(1 for p in pts if p['src']=='mined')}  "
          f"ctrl={sum(1 for p in pts if p['src']=='ctrl')}")

    # 邻域索引：src × (view桶, year)
    from collections import defaultdict
    buckets = defaultdict(list)
    for i, p in enumerate(pts):
        b = (p["src"], round(math.log10(p["stat"]["view"]) / 0.25), p.get("year") or "?")
        buckets[b].append(i)

    # AG 计算（v 自身排每桶末尾：先算桶内其它点的投影，再插入自身）
    idx_by_bucket = defaultdict(list)
    for i, p in enumerate(pts):
        b = (p["src"], round(math.log10(p["stat"]["view"]) / 0.25), p.get("year") or "?")
        idx_by_bucket[b].append(i)

    import numpy as np

    def bucket_ag(xs, f7s):
        """对单个邻域计算 AG（流形子空间深度）。返回 ags / uns / orths / coin_resid。"""
        n = len(xs)
        if n < MIN_NB + 1:
            return [None] * n, [None] * n, [None] * n, [None] * n
        X = np.array(xs, dtype=float) - np.mean(np.array(xs, dtype=float), axis=0)
        C = np.cov(X.T) if n > 5 else X.T @ X / n
        evals, evecs = np.linalg.eigh(C)
        order = np.argsort(evals)[::-1]
        evals, evecs = evals[order], evecs[:, order]
        cum = np.cumsum(evals) / max(np.sum(evals), 1e-12)
        k_m = max(2, int(np.searchsorted(cum, 0.85) + 1))
        P = evecs[:, :k_m]
        PDIRS = []
        for u in DIRS:
            v = P @ (P.T @ np.array(u, dtype=float))
            nrm = np.linalg.norm(v)
            if nrm > 0.3:
                PDIRS.append(v / nrm)
        if not PDIRS:
            PDIRS = [P[:, 0]]
        proj = X @ np.array(PDIRS).T
        med_f7 = float(np.median(f7s))
        ags, uns, orths = [None] * n, [None] * n, [None] * n
        # 构型残差：coin 条件于 fav/like 的局部线性回归残差
        # 几何意义：真实行为里 coin 与 fav/like 强共线（三连同构），
        # 「三缺一」刷量让点偏离这条回归线——单维拉升在 PCA 重构里不可见，在条件残差里现形
        try:
            from numpy.linalg import lstsq
            A = np.column_stack([np.ones(n), X[:, 1], X[:, 2]])
            coef, *_ = lstsq(A, X[:, 0], rcond=None)
            coin_resid = X[:, 0] - A @ coef
        except Exception:
            coin_resid = np.zeros(n)
        for k in range(n):
            if f7s[k] < med_f7:
                continue  # 正向性门槛：互动总量不差于邻域中位
            best_d, best_u = 0.0, None
            for ui in range(len(PDIRS)):
                col = np.delete(proj[:, ui], k)
                d = pct_rank(np.sort(col), proj[k, ui])
                if d > best_d:
                    best_d, best_u = d, ui
            shift = proj[k, best_u]
            orths[k] = round(float(np.linalg.norm(X[k] - X[k] @ P @ P.T)), 4)
            ags[k] = best_d if shift > 0 else 0.0
            uns[k] = best_u
        return ags, uns, orths, coin_resid

    for b, idxs in idx_by_bucket.items():
        ags, uns, orths, resids = bucket_ag([pts[i]["x"] for i in idxs],
                                            [pts[i]["f7"] for i in idxs])
        for k, i in enumerate(idxs):
            pts[i]["ag"], pts[i]["ag_u"], pts[i]["orth"] = ags[k], uns[k], orths[k]
            pts[i]["coin_resid"] = None if resids[k] is None else round(float(resids[k]), 4)

    valid = [p for p in pts if p.get("ag") is not None]
    for gi, p in enumerate(pts):
        p["gi"] = gi
    print(f"[ag] valid={len(valid)} (nb<{MIN_NB+1} 的点不计)")

    # ============ V2：分歧集 ============
    mined_v = [p for p in valid if p["src"] == "mined"]
    ag_only = [p for p in mined_v if p["ag"] >= 0.95 and p["cbi"] < 1.0]
    cbi_only = [p for p in mined_v if p["cbi"] >= 1.0 and p["ag"] < 0.80]
    both = [p for p in mined_v if p["ag"] >= 0.95 and p["cbi"] >= 1.0]
    print(f"=== V2 分歧集（挖掘组 n={len(mined_v)}）===")
    print(f"  AG独捞（AG>=0.95 & CBI<1.0）: {len(ag_only)} ({len(ag_only)/len(mined_v):.1%})")
    print(f"  CBI独捞（CBI>=1.0 & AG<0.80）: {len(cbi_only)} ({len(cbi_only)/len(mined_v):.1%})")
    print(f"  双过: {len(both)} ({len(both)/len(mined_v):.1%})")

    # 方向画像：AG 最深方向的构成（u 的主分量）
    def u_name(ui):
        if ui is None:
            return "?"
        u = DIRS[ui]
        top = max(range(5), key=lambda i: abs(u[i]))
        return DIM_NAMES[top] + ("-+" if u[top] > 0 else "-")
    from collections import Counter
    prof = Counter(u_name(p.get("ag_u")) for p in ag_only)
    print(f"  AG独捞的方向构成: {dict(prof.most_common(6))}")
    print("  AG独捞样例(前8):")
    for p in sorted(ag_only, key=lambda p: -p["ag"])[:8]:
        print(f"    AG={p['ag']:.3f} CBI={p['cbi']:.3f} [{p['year']}] {p['title'][:34]} ({p['bvid']}) u={u_name(p.get('ag_u'))}")

    # ============ V3：刷量免疫模拟 ============
    def ranks(vals):
        order = sorted(range(len(vals)), key=lambda i: -vals[i])
        r = [0] * len(vals)
        for rank, i in enumerate(order):
            r[i] = rank
        return r

    ag_vals = [p["ag"] for p in valid]
    cbi_vals = [p["cbi"] for p in valid]
    ag_r0, cbi_r0 = ranks(ag_vals), ranks(cbi_vals)
    n_boost = max(1, int(len(valid) * 0.2))
    boosted = RNG.sample(range(len(valid)), n_boost)
    ag_new, cbi_new = list(ag_vals), list(cbi_vals)
    resid0 = [p.get("coin_resid") or 0.0 for p in valid]
    resid_boost_before, resid_boost_after = [], []
    for i in boosted:
        st2 = dict(valid[i]["stat"])
        st2["coin"] = int((st2.get("coin") or 0) * 1.8 + 10)  # 刷币：×1.8 + 常量底
        cbi_new[i] = cbi_of(f7_of(st2), st2["view"])
        x2 = feat_vec(st2)
        p = valid[i]
        b = (p["src"], round(math.log10(p["stat"]["view"]) / 0.25), p.get("year") or "?")
        idxs = idx_by_bucket[b]
        k = idxs.index(p["gi"])
        xs = [pts[j]["x"] for j in idxs]
        f7s = [pts[j]["f7"] for j in idxs]
        xs[k], f7s[k] = x2, f7_of(st2)  # 替换被刷点后整桶重算
        ags, uns, orths, resids = bucket_ag(xs, f7s)
        ag_new[i] = ags[k] if ags[k] is not None else ag_new[i]
        resid_boost_before.append(resid0[i])
        resid_boost_after.append(resids[k] if resids[k] is not None else resid0[i])
    ag_r1, cbi_r1 = ranks(ag_new), ranks(cbi_new)
    ag_mean = sum(ag_r0[i] - ag_r1[i] for i in boosted) / n_boost
    cbi_mean = sum(cbi_r0[i] - cbi_r1[i] for i in boosted) / n_boost
    resid_ref = sorted(abs(r) for r in resid0)[len(resid0) // 2]
    resid_lift = (sum(abs(r) for r in resid_boost_after) / n_boost) \
        - (sum(abs(r) for r in resid_boost_before) / n_boost)
    print("=== V3 刷量免疫（20% 视频 coin×1.8，流形深度 + 构型残差）===")
    print(f"  被刷视频的排名平均提升：CBI = +{cbi_mean:.1f} 位   AG(流形内) = +{ag_mean:.1f} 位")
    print(f"  构型残差 |coin|fav,like|：被刷点均值提升 {resid_lift:+.4f}（全体中位 {resid_ref:.4f}）")
    detect_ok = resid_lift > max(0.05, resid_ref * 0.3)
    print(f"  判定：深度判据{'不' if ag_mean >= cbi_mean else ''}抗刷（原理性结论：stat 向量无法区分真互动与仿真刷量）；"
          f"构型残差检出 {'✓' if detect_ok else '✗'}")

    # 汇总落盘
    out = {
        "meta": {"points": len(pts), "valid_ag": len(valid),
                 "mined": len(mined_v), "dirs": len(DIRS), "min_nb": MIN_NB},
        "v2": {"ag_only_n": len(ag_only), "ag_only_rate": round(len(ag_only) / len(mined_v), 4),
               "cbi_only_n": len(cbi_only), "both_n": len(both),
               "ag_only_profile": dict(prof.most_common(8)),
               "ag_only_examples": [{"bvid": p["bvid"], "title": p["title"], "year": p.get("year"),
                                     "ag": round(p["ag"], 3), "cbi": round(p["cbi"], 3),
                                     "u": u_name(p.get("ag_u"))} for p in sorted(ag_only, key=lambda p: -p["ag"])[:12]]},
        "v3": {"n_boost": n_boost, "rank_gain_cbi": round(cbi_mean, 2),
               "rank_gain_ag": round(ag_mean, 2),
               "resid_lift": round(resid_lift, 4), "resid_median_all": round(resid_ref, 4),
               "detect": bool(detect_ok)},
    }
    outp = os.path.join(ROOT, "data", "fav_mine", "ag_depth_summary.json")
    json.dump(out, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[done] -> {outp}")


if __name__ == "__main__":
    main()
