# -*- coding: utf-8 -*-
"""E1/E2 三臂多指标对比（神作率 / 优秀率 / 平均CBI / 中位CBI）

三臂设计（Elabation 提出，控制变量）：
  臂① flow_high  ：神作（CBI>=3.0）评论区用户 —— 流引导
  臂② uploader   ：UP 主种子用户（第二/三轮挖掘）—— 现状基线
  臂③ comment_low：普通视频（CBI<0.7）评论区用户 —— 排除「评论行为本身」混杂
统计：Mann-Whitney U（正态近似，用户级分布对比，单尾）。
口径：全部经 cbi_scale 单一定义源；tier 现算；只统计 view>=3000 的视频。
用法： python engine/e1_homophily.py
"""
import json
import math
import os
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cbi_scale import SCALE, GOOD_TIERS, tier_of  # noqa: E402

MINE_DIR = os.path.join(ROOT, "data", "fav_mine")
MIN_VIDEOS = 5  # 用户至少 5 条合格视频才计入

ARMS 動態发现（2026-09-03 重采版）：扫描全部 favmine_*.json，按 meta.arm 分类——
  "high" → flow_high / "low" → comment_low / "all"（无 hop，纯 uploader 种子轮）→ uploader。
不硬编码文件名（旧版硬编码时间戳是重跑炸弹）。
"""

METRICS = {
    "神作率": lambda d: d["n_high"] / d["n"],
    "优秀率": lambda d: d["n_good"] / d["n"],
    "平均CBI": lambda d: sum(d["cbis"]) / len(d["cbis"]),
    "中位CBI": lambda d: sorted(d["cbis"])[len(d["cbis"]) // 2],
}


def discover_arms():
    """按 meta.arm 自动发现三臂文件。"""
    out = defaultdict(list)
    for fn in sorted(os.listdir(MINE_DIR)):
        if not (fn.startswith("favmine_") and fn.endswith(".json")):
            continue
        if "_analysis" in fn or "merged" in fn or "flowH" in fn or "flowE3" in fn:
            continue
        try:
            meta = json.load(open(os.path.join(MINE_DIR, fn), encoding="utf-8")).get("meta") or {}
        except Exception:
            continue
        arm = meta.get("arm")
        if arm == "high":
            out["flow_high"].append(fn)
        elif arm == "low":
            out["comment_low"].append(fn)
        elif arm == "all" and meta.get("hop") is None:
            out["uploader"].append(fn)
    return out


def user_stats():
    """arm -> [每用户统计 dict]"""
    raw = defaultdict(lambda: defaultdict(lambda: {"n_high": 0, "n_good": 0, "n": 0, "cbis": []}))
    for arm, files in discover_arms().items():
        for fn in files:
            payload = json.load(open(os.path.join(MINE_DIR, fn), encoding="utf-8"))
            for v in payload.get("videos") or []:
                uh = v.get("from_user")
                view = v.get("view") or 0
                cbi = v.get("cbi") or 0
                if not uh or view < 3000:
                    continue
                d = raw[arm][uh]
                t = tier_of(cbi, view)
                d["n"] += 1
                d["cbis"].append(cbi)
                d["n_high"] += t == "high"
                d["n_good"] += t in GOOD_TIERS
    out = defaultdict(list)
    for arm, users in raw.items():
        for d in users.values():
            if d["n"] >= MIN_VIDEOS:
                out[arm].append(d)
    return out


def mwu_u(x, y):
    """Mann-Whitney U（正态近似）。返回 (z, p_one)，H1: x > y。"""
    n1, n2 = len(x), len(y)
    if n1 < 5 or n2 < 5:
        return None, None
    allv = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks, i = [0.0] * len(allv), 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        avg_rank = (i + j - 1) / 2 + 1
        for t in range(i, j):
            ranks[t] = avg_rank
        i = j
    r1 = sum(r for r, (v, g) in zip(ranks, allv) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    sigma = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (u1 - mu) / sigma if sigma else 0.0
    return z, 0.5 * math.erfc(z / math.sqrt(2))


def fmt_p(p):
    if p is None:
        return "  -  "
    return f"{p:.4f}" if p >= 1e-4 else f"{p:.1e}"


def main():
    arms = user_stats()
    names = ["flow_high", "uploader", "comment_low"]
    labels = {"flow_high": "臂①流引导", "uploader": "臂②基线", "comment_low": "臂③评论对照"}
    for a in names:
        print(f"[arm {a:12s}] 合格用户 {len(arms.get(a) or [])}")

    print("\n=== 三臂多指标对比（用户级均值，view>=3000，CBI 三档口径）===")
    print(f"{'指标':<8}", "  ".join(f"{labels[a]:>10}" for a in names))
    results = {}
    for mname, fn in METRICS.items():
        vals = {a: [fn(d) for d in arms.get(a) or []] for a in names}
        means = {a: (sum(v) / len(v) if v else 0) for a, v in vals.items()}
        results[mname] = {"means": means, "tests": {}}
        print(f"{mname:<8}", "  ".join(f"{means[a]:>10.3f}" for a in names))

    pairs = [("flow_high", "uploader"), ("flow_high", "comment_low"), ("comment_low", "uploader")]
    print("\n=== 两两 MWU（用户级分布，单尾 H1:前者>后者）===")
    for mname, fn in METRICS.items():
        vals = {a: [fn(d) for d in arms.get(a) or []] for a in names}
        row = []
        for a, b in pairs:
            z, p = mwu_u(vals[a], vals[b])
            results[mname]["tests"][f"{a}>{b}"] = {
                "z": round(z, 3) if z is not None else None, "p": p}
            row.append(f"{labels[a][2:]}>{labels[b][2:]} p={fmt_p(p)}")
        print(f"  {mname:<6}: " + "   ".join(row))

    hi = results["神作率"]
    e1 = hi["tests"]["flow_high>uploader"]
    e2 = hi["tests"]["flow_high>comment_low"]
    e1_ratio = hi["means"]["flow_high"] / max(1e-9, hi["means"]["uploader"])
    e2_ratio = hi["means"]["flow_high"] / max(1e-9, hi["means"]["comment_low"])
    cb = results["平均CBI"]
    e1_pass = bool(e1["p"] is not None and e1["p"] < 0.05 and e1_ratio >= 1.3)
    e2_pass = bool(e2["p"] is not None and e2["p"] < 0.05 and e2_ratio >= 1.3)
    print("\n=== E1/E2 判定（神作率口径，与此前判定一致）===")
    print(f"  E1 流的前提：ratio={e1_ratio:.2f} p={fmt_p(e1['p'])}  {'✓ 通过' if e1_pass else '✗'}")
    print(f"  E2 净效果  ：ratio={e2_ratio:.2f} p={fmt_p(e2['p'])}  {'✓ 通过' if e2_pass else '✗'}")
    print(f"  平均CBI比：臂①/基线 = {cb['means']['flow_high'] / max(1e-9, cb['means']['uploader']):.2f}×   "
          f"臂①/臂③ = {cb['means']['flow_high'] / max(1e-9, cb['means']['comment_low']):.2f}×")

    out = {"min_videos": MIN_VIDEOS, "scale": SCALE,
           "n_users": {a: len(arms.get(a) or []) for a in names},
           "metrics": results,
           "e1": {"ratio": round(e1_ratio, 3), "p": e1["p"], "pass": e1_pass},
           "e2": {"ratio": round(e2_ratio, 3), "p": e2["p"], "pass": e2_pass}}
    outp = os.path.join(MINE_DIR, "e1_homophily_summary.json")
    json.dump(out, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n[done] -> {outp}")


if __name__ == "__main__":
    main()
