# -*- coding: utf-8 -*-
"""感谢几何 · AG-Compass 离线原型（验证 V6/V7）

品味锥：高质量用户的行为向量方向 = 锥轴；挖矿 = 沿锥轴优先。
  V6 留出法：用户对半分（种子组建锥 / 靶组评估），
    引导策略（靶用户与锥轴余弦相似度 Top-k）vs 随机策略，神作产量比 ≥ 1.4？
  V7 锥数收敛：全体用户行为向量 k-means（k=2..10），轮廓系数最优 k 是否落在 4-8？
用法： python engine/ag_compass.py
"""
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np
from cbi_scale import SCALE, GOOD_TIERS

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fav_miner import f7_of, load_merged_mine  # noqa: E402
from ag_depth import feat_vec  # noqa: E402

MIN_V = 3000
ROUNDS = 30  # 留出随机重复轮数


def load_users():
    merged = load_merged_mine(os.path.join(ROOT, "data", "fav_mine"))
    by_user = defaultdict(lambda: {"vecs": [], "n_high": 0, "n": 0})
    for v in merged["videos"]:
        st = v.get("stat") or {}
        if not st.get("view") or st["view"] < MIN_V or not v.get("from_user"):
            continue
        u = by_user[v["from_user"]]
        u["vecs"].append(feat_vec(st))
        u["n"] += 1
        if v.get("cbi", 0) >= SCALE["high"]:
            u["n_high"] += 1
    out = {}
    for uh, d in by_user.items():
        if d["n"] >= 8:  # 至少 8 条才谈得上稳定估计
            out[uh] = {"x": np.mean(np.array(d["vecs"]), axis=0),
                       "q": d["n_high"] / d["n"], "n": d["n"], "n_high": d["n_high"]}
    return out


def v6_holdout(users):
    rng = np.random.default_rng(42)
    uh = list(users)
    gains = {10: [], 20: [], 30: []}
    base = {10: [], 20: [], 30: []}
    for _ in range(ROUNDS):
        rng.shuffle(uh)
        half = len(uh) // 2
        seeds, targets = uh[:half], uh[half:]
        # 锥轴：种子组里神作率 Top-25% 用户的行为向量均值方向
        seeds_sorted = sorted(seeds, key=lambda u: -users[u]["q"])
        elite = seeds_sorted[:max(3, len(seeds_sorted) // 4)]
        axis = np.mean([users[u]["x"] for u in elite], axis=0)
        axis = axis / (np.linalg.norm(axis) + 1e-12)
        # 靶组：按与锥轴相似度排序
        t_sorted = sorted(targets,
                          key=lambda u: -float(np.dot(users[u]["x"], axis) /
                                               (np.linalg.norm(users[u]["x"]) + 1e-12)))
        for k in gains:
            guide_hits = sum(users[u]["n_high"] for u in t_sorted[:k])
            rand_hits = float(np.mean([sum(users[u]["q"] * users[u]["n"]
                                            for u in rng.choice(targets, k, replace=False))
                                       for _ in range(8)]))
            gains[k].append(guide_hits / (rand_hits + 1e-9))
            base[k].append(rand_hits)
    return {k: {"ratio_mean": round(float(np.mean(v)), 3),
                "ratio_min": round(float(np.min(v)), 3),
                "pass_1_4x": bool(np.mean(v) >= 1.4)} for k, v in gains.items()}


def v7_cone_count(users):
    """k-means k=2..10，轮廓系数（手写，抽样加速）。"""
    X = np.array([users[u]["x"] for u in users])
    rng = np.random.default_rng(7)
    best_k, best_s = None, -1.0
    scores = {}
    for k in range(2, 11):
        labels, inertia = _kmeans(X, k, rng)
        s = _silhouette(X, labels, rng, sample=min(len(X), 400))
        scores[k] = round(s, 4)
        if s > best_s:
            best_k, best_s = k, s
    return {"best_k": best_k, "silhouette": round(best_s, 4),
            "scores": scores, "pass_4_8": bool(4 <= (best_k or 0) <= 8)}


def _kmeans(X, k, rng, iters=40):
    idx = rng.choice(len(X), k, replace=False)
    C = X[idx].copy()
    lab = np.zeros(len(X), dtype=int)
    for _ in range(iters):
        d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
        nl = d.argmin(axis=1)
        if (nl == lab).all() and _ > 0:
            break
        lab = nl
        for j in range(k):
            if (lab == j).any():
                C[j] = X[lab == j].mean(axis=0)
    inertia = float(((X - C[lab]) ** 2).sum())
    return lab, inertia


def _silhouette(X, labels, rng, sample=400):
    idx = rng.choice(len(X), sample, replace=False) if len(X) > sample else np.arange(len(X))
    uniq = np.unique(labels)
    if len(uniq) < 2:
        return -1.0
    s_vals = []
    for i in idx:
        same = np.where(labels[idx] == labels[i])[0]
        same = same[same != np.where(idx == i)[0][0]] if (idx == i).any() else same
        if len(same) == 0:
            continue
        a = np.mean(np.linalg.norm(X[idx[same]] - X[i], axis=1))
        b = min(np.mean(np.linalg.norm(X[idx[labels[idx] == c]] - X[i], axis=1))
                for c in uniq if c != labels[i] and (labels[idx] == c).any())
        s_vals.append((b - a) / max(a, b))
    return float(np.mean(s_vals)) if s_vals else -1.0


def main():
    users = load_users()
    print(f"[users] 有效用户（>=8 条）: {len(users)}")
    if len(users) < 30:
        print("[warn] 用户过少，V6 统计力不足")
    v6 = v6_holdout(users)
    print("=== V6 留出法（30 轮随机对半）===")
    for k, r in v6.items():
        print(f"  预算 {k} 用户：引导/随机 产量比 = {r['ratio_mean']}  "
              f"{'✓' if r['pass_1_4x'] else '✗'}（最差轮 {r['ratio_min']}）")
    v7 = v7_cone_count(users)
    print("=== V7 锥数收敛（k-means 轮廓系数）===")
    print(f"  最优 k = {v7['best_k']}  silhouette = {v7['silhouette']}  "
          f"{'✓ 落在 4-8' if v7['pass_4_8'] else '✗'}")
    print(f"  各 k 得分: {v7['scores']}")

    outp = os.path.join(ROOT, "data", "fav_mine", "ag_compass_summary.json")
    json.dump({"meta": {"users": len(users), "rounds": ROUNDS}, "v6": v6, "v7": v7},
              open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[done] -> {outp}")


if __name__ == "__main__":
    main()
