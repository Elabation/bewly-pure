# -*- coding: utf-8 -*-
"""洁净B站 · 生态分析
回答四个问题：
  Q1 火的就高质量吗？     → 热门层中「看过不给」(低比值) 的占比
  Q2 高质量但不火存在吗？ → 长尾/推荐层中高比值遗珠的数量与样例
  Q3 手搓就会火吗？       → 手搓/高投入标题的播放分布 vs 比值分布
  Q4 哪个公式最像"低质探测器"？ → 排列组合实验（与播放脱钩 + 与社交活跃挂钩 + 底部构成）
用法： python engine/ecosystem_analysis.py --data data/samples/ecosystem_xxx.json
"""
import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

W_BASE = {"favorite": 3.0, "coin": 2.0, "like": 0.3}


# ---------- 统计工具 ----------
def ranks(xs):
    idx = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and xs[idx[j + 1]] == xs[idx[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            r[idx[k]] = avg
        i = j + 1
    return r


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    vx = sum((a - mx) ** 2 for a in xs) ** 0.5
    vy = sum((b - my) ** 2 for b in ys) ** 0.5
    return cov / (vx * vy) if vx and vy else None


def spearman(xs, ys):
    return pearson(ranks(xs), ranks(ys))


def median(vals):
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    return (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2)


def pct(vals, p):
    if not vals:
        return 0.0
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


# ---------- 公式 ----------
def score(video, weights, denom):
    st = video["stat"]
    v = st["view"] or 0
    if v <= 0:
        return 0.0
    raw = (st["favorite"] or 0) * weights["favorite"] + (st["coin"] or 0) * weights["coin"] \
        + (st["like"] or 0) * weights["like"]
    if denom == "view":
        d = v
    elif denom == "sqrt_view":
        d = math.sqrt(v)
    else:
        d = math.log10(max(v, 10))
    return raw / d


def ratio(video, top, bot):
    st = video["stat"]
    a = sum((st.get(k) or 0) for k in top)
    b = st.get(bot) or 0
    return a / b if b > 0 else 0.0


def layer(src):
    return src.split(":")[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "analysis"))
    args = ap.parse_args()
    with open(args.data, encoding="utf-8") as f:
        payload = json.load(f)
    videos = payload["videos"]

    # 有效样本：播放>0
    vs = [v for v in videos if (v["stat"].get("view") or 0) > 0]
    trusted = [v for v in vs if v["stat"]["view"] >= 1000 and v.get("stat_raw_ok", True)]
    n_excluded = sum(1 for v in vs if v["stat"]["view"] >= 1000 and not v.get("stat_raw_ok", True))
    print(f"[load] {len(videos)} 条，播放>0: {len(vs)}，播放≥1000且stat完整: {len(trusted)}（剔除缺stat {n_excluded} 条）")

    # ---------- 公式排列组合 ----------
    formulas = {
        "F1 点赞/播放": ({"favorite": 0, "coin": 0, "like": 1}, "view"),
        "F2 投币/播放": ({"favorite": 0, "coin": 1, "like": 0}, "view"),
        "F3 收藏/播放": ({"favorite": 1, "coin": 0, "like": 0}, "view"),
        "F4 (赞+币)/播放": ({"favorite": 0, "coin": 1, "like": 1}, "view"),
        "F5 (藏+币)/播放": ({"favorite": 1, "coin": 1, "like": 0}, "view"),
        "F6 (藏+币+赞)/播放": ({"favorite": 1, "coin": 1, "like": 1}, "view"),
        "F7 基准权重/播放": (W_BASE, "view"),
        "F8 基准权重/√播放": (W_BASE, "sqrt_view"),
        "F9 基准权重/log播放": (W_BASE, "log10_view"),
        "F10 币重权重/播放": ({"favorite": 0.5, "coin": 3, "like": 0.1}, "view"),
    }
    logv = [math.log10(v["stat"]["view"]) for v in trusted]
    social = [(lambda st: ((st.get("danmaku") or 0) + (st.get("share") or 0) + (st.get("reply") or 0))
               / max(st["view"], 1))(v["stat"]) for v in trusted]

    sweep = {}
    for name, (w, d) in formulas.items():
        s = [score(v, w, d) for v in trusted]
        pairs = sorted(zip(trusted, s), key=lambda p: p[1])
        bottom50 = [p[0] for p in pairs[:50]]
        comp = defaultdict(int)
        for v in bottom50:
            comp[layer(v["source"])] += 1
        sweep[name] = {
            "corr_logview": round(spearman(s, logv), 3),
            "corr_social": round(spearman(s, social), 3),
            "bottom50_by_layer": dict(comp),
            "bottom10": [{"t": v["title"][:28], "v": v["stat"]["view"], "src": v["source"]}
                         for v, _ in pairs[:10]],
        }

    # ---------- 播放分位段：火的段位互动率被稀释了吗 ----------
    bands = [(1000, 10000, "1k-1w"), (10000, 100000, "1w-10w"), (100000, 1000000, "10w-100w"),
             (1000000, 10**12, ">100w")]
    f7 = [score(v, W_BASE, "view") for v in trusted]
    f7_p25, f7_p50, f7_p75 = pct(f7, 25), pct(f7, 50), pct(f7, 75)
    band_rows = []
    for lo, hi, name in bands:
        grp = [v for v in trusted if lo <= v["stat"]["view"] < hi]
        if not grp:
            continue
        band_rows.append({
            "band": name, "n": len(grp),
            "like_v": round(median([ratio(v, ["like"], "view") for v in grp]), 4),
            "coin_v": round(median([ratio(v, ["coin"], "view") for v in grp]), 4),
            "fav_v": round(median([ratio(v, ["favorite"], "view") for v in grp]), 4),
            "f7_p50": round(median([score(v, W_BASE, "view") for v in grp]), 4),
            "cold_share": round(sum(1 for v in grp if score(v, W_BASE, "view") < f7_p25) / len(grp), 3),
        })

    # ---------- Q1 火的就高质量吗：热门层冷门比 ----------
    hot = [v for v in trusted if layer(v["source"]) in ("ranking", "popular")]
    fire_but_cold = [v for v in hot if v["stat"]["view"] >= 500000 and score(v, W_BASE, "view") < f7_p25]
    # ---------- Q2 高质量但不火：长尾层遗珠 ----------
    tail = [v for v in trusted if layer(v["source"]) in ("newlist", "feed")]
    gems = [v for v in tail if score(v, W_BASE, "view") >= f7_p75]
    gems_sorted = sorted(gems, key=lambda v: score(v, W_BASE, "view"), reverse=True)

    # ---------- Q3 手搓会火吗 ----------
    handmade_re = re.compile(r"手搓|自制|耗时|历时|一个人|独自|Months|个月|年半|三年|两年")
    handmade = [v for v in trusted if handmade_re.search(v["title"] or "")]
    hm_rows = sorted([(v, score(v, W_BASE, "view")) for v in handmade],
                     key=lambda p: -p[0]["stat"]["view"])
    med_view_all = median([v["stat"]["view"] for v in trusted])
    med_view_hot = median([v["stat"]["view"] for v in hot]) if hot else None
    med_view_hm = median([v["stat"]["view"] for v in handmade]) if handmade else None

    # ---------- 分区价值画像（榜单层 vs 长尾层） ----------
    zones = defaultdict(list)
    for v in trusted:
        if v["source"].startswith("ranking:"):
            zones[v["source"].split(":", 1)[1]].append(v)
    zone_rows = []
    for z, grp in sorted(zones.items(), key=lambda kv: -len(kv[1])):
        if len(grp) < 8:
            continue
        zone_rows.append({
            "zone": z, "n": len(grp),
            "coin_v": round(median([ratio(v, ["coin"], "view") for v in grp]), 4),
            "fav_v": round(median([ratio(v, ["favorite"], "view") for v in grp]), 4),
            "like_v": round(median([ratio(v, ["like"], "view") for v in grp]), 4),
            "dan_v": round(median([ratio(v, ["danmaku"], "view") for v in grp]), 4),
            "med_dur": median([v.get("duration") or 0 for v in grp]),
        })

    # ---------- 网页散点数据（确定性抽样 ~230 点） ----------
    def pick(src_prefix, k):
        pool = sorted([v for v in trusted if v["source"].startswith(src_prefix)],
                      key=lambda v: v["bvid"])
        step = max(1, len(pool) // k)
        return pool[::step][:k]
    pts_pool = pick("feed", 60) + pick("newlist", 60) + pick("ranking:全站", 40) + \
        pick("popular", 30) + pick("ranking:", 20) + pick("series:", 60) + pick("precious", 20)
    points = [{"t": (v["title"] or "")[:36], "v": v["stat"]["view"],
               "r": round(score(v, W_BASE, "view"), 4),
               "s": layer(v["source"]), "z": (v["source"].split(":")[1] if ":" in v["source"] else "")}
              for v in pts_pool]

    summary = {
        "meta": {"n_total": len(videos), "n_trusted": len(trusted),
                 "by_layer": dict(sorted(defaultdict(int, {k: sum(1 for v in vs if layer(v["source"]) == k)
                                                           for k in set(layer(v["source"]) for v in vs)}).items())),
                 "f7_p25": round(f7_p25, 4), "f7_p50": round(f7_p50, 4), "f7_p75": round(f7_p75, 4)},
        "sweep": sweep,
        "bands": band_rows,
        "fire_but_cold": {"n": len(fire_but_cold), "n_hot": len(hot),
                          "examples": [{"t": v["title"][:30], "v": v["stat"]["view"],
                                        "r": round(score(v, W_BASE, "view"), 3)} for v in fire_but_cold[:10]]},
        "gems": {"n": len(gems), "n_tail": len(tail),
                 "examples": [{"t": v["title"][:30], "v": v["stat"]["view"],
                               "r": round(score(v, W_BASE, "view"), 3), "src": v["source"]}
                              for v in gems_sorted[:10]]},
        "handmade": {"n": len(handmade),
                     "med_view_all": med_view_all, "med_view_hot": med_view_hot,
                     "med_view_handmade": med_view_hm,
                     "rows": [{"t": v["title"][:30], "v": v["stat"]["view"],
                               "r": round(r, 3), "src": v["source"]} for v, r in hm_rows[:15]]},
        "zones": zone_rows,
        "points": points,
    }
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "ecosystem_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print(f"[saved] {out_path}")

    # ---------- 控制台摘要 ----------
    print("\n=== 公式扫描 ===")
    for name, r in sweep.items():
        print(f"{name:14s} |与log播放相关 {r['corr_logview']:+.3f} |与社交活跃 {r['corr_social']:+.3f}"
              f" |底部50构成 {r['bottom50_by_layer']}")
    print("\n=== 播放分位段 ===")
    for b in band_rows:
        print(f"{b['band']:9s} n={b['n']:4d} 赞/播={b['like_v']:.4f} 币/播={b['coin_v']:.4f}"
              f" 藏/播={b['fav_v']:.4f} 冷比占位={b['cold_share']:.0%}")
    print(f"\n=== Q1 火≠高质量: 热门层 n={len(hot)}，其中 ≥50w播放且比值<全局P25 的「看过不给」: {len(fire_but_cold)} ===")
    for e in fire_but_cold[:6]:
        print(f"  {e['stat']['view']:>10,} r={score(e, W_BASE, 'view'):.3f} {e['title'][:26]}")
    print(f"\n=== Q2 高质量但不火: 长尾层 n={len(tail)}，遗珠(比值≥P75): {len(gems)} ===")
    for e in gems_sorted[:6]:
        print(f"  {e['stat']['view']:>10,} r={score(e, W_BASE, 'view'):.3f} {e['title'][:26]}")
    print(f"\n=== Q3 手搓: n={len(handmade)} 中位播放={med_view_hm} (全体 {med_view_all}, 热门层 {med_view_hot}) ===")
    for v, r in hm_rows[:8]:
        print(f"  {v['stat']['view']:>10,} r={r:.3f} {v['title'][:28]}")
    print("\n=== 分区画像(榜单层) ===")
    for z in zone_rows:
        print(f"{z['zone']:4s} n={z['n']:3d} 币/播={z['coin_v']:.4f} 藏/播={z['fav_v']:.4f}"
              f" 赞/播={z['like_v']:.4f} 弹/播={z['dan_v']:.4f} 中位时长={z['med_dur']}s")


if __name__ == "__main__":
    main()
