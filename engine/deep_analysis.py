# -*- coding: utf-8 -*-
"""洁净B站 · 深度统计分析（第二轮：剥干扰看本质）
十个实验，每个对应一个问题的干扰源：
  A 偏相关     控制[视频年龄/时长/分区]后，「火的稀释」还剩多少？——火是机制还是混杂？
  B CBI 相对基线 拟合比值~播放的条件中位数曲线，定义「看过不给指数」CBI=实际/预期；
               与全局阈值做判定分歧矩阵——低质密码 v2 的核心算法
  C 洛伦兹+基尼 注意力不平等的形状；Zipf 幂律拟合
  D 价值指纹   17分区×4维互动率向量 → PCA 二维投影：类型效应的几何呈现
  E 信号分歧   6种互动率的 Spearman 矩阵：哪些信号独立（度量不同维度）
  F 网格搜索   7信号子集×3分母=21组公式系统扫描
  G 标题信号学 标题特征组（合集/问号/emoji/剧集切片…）的比值差异 + MWU 检验
  H 保质期     feed层内 视频年龄 与 CBI：互动是累积函数还是衰减函数
  I 手搓检验   CBI 的 Mann-Whitney（手搓 vs 其余）：极化是否统计显著
  J 时间线模拟 feed层应用洁净过滤器：砍掉多少注意力
用法： python engine/deep_analysis.py --data data/samples/ecosystem_20260901_1910_v4.json
"""
import argparse
import json
import math
import os
import re
import sys
import time
from collections import defaultdict

import numpy as np
from scipy import stats as st

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W_BASE = {"favorite": 3.0, "coin": 2.0, "like": 0.3}


def clean(o):
    if isinstance(o, (np.floating, float)):
        return None if (isinstance(o, float) and math.isnan(o)) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


def layer(src):
    return src.split(":")[0]


def f7_of(v):
    s = v["stat"]
    view = s["view"] or 0
    if view <= 0:
        return 0.0, 0
    raw = (s["favorite"] or 0) * W_BASE["favorite"] + (s["coin"] or 0) * W_BASE["coin"] \
        + (s["like"] or 0) * W_BASE["like"]
    return raw / view, view


def rate(v, key):
    view = v["stat"]["view"] or 0
    return ((v["stat"].get(key) or 0) / view) if view > 0 else 0.0


def social_idx(v):
    s = v["stat"]
    view = s["view"] or 0
    return ((s.get("danmaku") or 0) + (s.get("share") or 0) + (s.get("reply") or 0)) / view if view else 0.0


def score_w(v, w, denom):
    s = v["stat"]
    view = s["view"] or 0
    if view <= 0:
        return 0.0
    raw = (s["favorite"] or 0) * w[0] + (s["coin"] or 0) * w[1] + (s["like"] or 0) * w[2]
    d = {"view": view, "sqrt_view": math.sqrt(view), "log10_view": math.log10(max(view, 10))}[denom]
    return raw / d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "analysis", "deep_summary.json"))
    args = ap.parse_args()
    with open(args.data, encoding="utf-8") as f:
        payload = json.load(f)
    videos = payload["videos"]
    collected_at = os.path.getmtime(args.data)

    trusted = [v for v in videos if (v["stat"].get("view") or 0) >= 1000 and v.get("stat_raw_ok", True)]
    for v in trusted:
        v["_f7"], _ = f7_of(v)
        v["_logv"] = math.log10(v["stat"]["view"])
        v["_age"] = max((collected_at - (v.get("pubdate") or collected_at)) / 86400.0, 0.1)
        v["_logage"] = math.log10(v["_age"])
        d = v.get("duration") or 0
        v["_logdur"] = math.log10(d) if d > 0 else None
        v["_dur"] = d
        src = v["source"]
        if src.startswith("ranking:") or src.startswith("newlist:"):
            v["_zone"] = src.split(":", 1)[1]
        else:
            v["_zone"] = v.get("tname") or ""
        m = re.search(r"(\d{4})第", src)
        v["_year"] = int(m.group(1)) if m else (v.get("pubdate") and time.gmtime(v["pubdate"]).tm_year)
        v["_social"] = social_idx(v)
    print(f"[load] trusted {len(trusted)}")

    res = {"meta": {"n_total": len(videos), "n_trusted": len(trusted),
                    "collected_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(collected_at))}}

    # ============ 实验A：偏相关 ============
    def ols_resid(y, X):
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        return y - X @ beta

    f7 = np.array([v["_f7"] for v in trusted])
    logv = np.array([v["_logv"] for v in trusted])
    logage = np.array([v["_logage"] for v in trusted])
    logdur = np.array([v["_logdur"] if v["_logdur"] is not None else 2.0 for v in trusted])

    def partial(y, x, covs):
        ry = ols_resid(y, np.column_stack([np.ones(len(y))] + covs))
        rx = ols_resid(x, np.column_stack([np.ones(len(x))] + covs))
        return float(st.pearsonr(ry, rx)[0])

    raw_r = float(st.pearsonr(f7, logv)[0])
    p_age = partial(f7, logv, [logage])
    p_age_dur = partial(f7, logv, [logage, logdur])
    # ranking 层内再加分区哑变量
    rk = [v for v in trusted if layer(v["source"]) == "ranking"]
    zones = sorted({v["_zone"] for v in rk})
    dummies = np.zeros((len(rk), len(zones)))
    for i, v in enumerate(rk):
        dummies[i, zones.index(v["_zone"])] = 1.0
    rk_f7 = np.array([v["_f7"] for v in rk])
    rk_logv = np.array([v["_logv"] for v in rk])
    rk_covs = [np.array([v["_logage"] for v in rk]),
               np.array([v["_logdur"] if v["_logdur"] is not None else 2.0 for v in rk])]
    p_full = partial(rk_f7, rk_logv, rk_covs + [dummies[:, j] for j in range(1, len(zones))])
    res["partial"] = {
        "raw_pearson": round(raw_r, 3),
        "ctrl_age": round(p_age, 3),
        "ctrl_age_dur": round(p_age_dur, 3),
        "ranking_full_ctrl": round(p_full, 3),
        "ranking_n": len(rk), "n_zones": len(zones),
        "note": "偏相关=控制方括号内变量后的线性关联；解释为关联而非因果",
    }
    print(f"[A 偏相关] raw={raw_r:.3f} +age={p_age:.3f} +age,dur={p_age_dur:.3f} ranking全控制={p_full:.3f}")

    # ============ 实验B：CBI 相对基线 ============
    order = sorted(trusted, key=lambda v: v["_logv"])
    lv_sorted = np.array([v["_logv"] for v in order])
    f7_sorted = np.array([v["_f7"] for v in order])
    grid = np.arange(3.0, 7.25, 0.1)
    p50c, p25c = [], []
    for g in grid:
        win = f7_sorted[(lv_sorted >= g - 0.35) & (lv_sorted <= g + 0.35)]
        if len(win) >= 25:
            p50c.append([round(float(g), 2), round(float(np.percentile(win, 50)), 4)])
            p25c.append([round(float(g), 2), round(float(np.percentile(win, 25)), 4)])
    p50_arr = np.array(p50c)
    expected = np.interp(logv, p50_arr[:, 0], p50_arr[:, 1])
    for v, e in zip(trusted, expected):
        v["_cbi"] = float(v["_f7"] / e) if e > 0 else None

    hot_bad = [v for v in trusted if v["stat"]["view"] >= 50000]
    g_p25 = float(np.percentile(f7, 25))
    n = len(hot_bad)
    g_low = [v["_f7"] < g_p25 for v in hot_bad]
    c_low = [(v["_cbi"] is not None and v["_cbi"] < 0.5) for v in hot_bad]
    both = sum(1 for a, b in zip(g_low, c_low) if a and b)
    gonly = sum(1 for a, b in zip(g_low, c_low) if a and not b)
    conly = sum(1 for a, b in zip(g_low, c_low) if not a and b)
    healthy = n - both - gonly - conly
    chi2, chi2_p = st.chi2_contingency([[both, gonly], [conly, healthy]])[:2]
    res["cbi"] = {
        "p50_curve": p50c, "p25_curve": p25c,
        "g_p25": round(g_p25, 4),
        "confusion": {"n_ge50w": n, "both_low": both, "global_only": gonly,
                      "cbi_only": conly, "healthy": healthy,
                      "global_low_pardoned_by_cbi_pct": round(gonly / max(both + gonly, 1), 3),
                      "chi2_p": float(f"{chi2_p:.3g}")},
    }
    print(f"[B CBI] ≥5w样本 n={n} 全局低质 {both+gonly} 其中 CBI 平反 {gonly}（{gonly/max(both+gonly,1):.0%}）chi2_p={chi2_p:.2g}")

    # ============ 实验C：洛伦兹 + 基尼 + Zipf ============
    def gini(vals):
        s = np.sort(np.array(vals, dtype=float))
        n_ = len(s)
        if n_ == 0 or s.sum() == 0:
            return None
        cum = np.cumsum(s) / s.sum()
        return float(1 - 2 * np.trapezoid(cum, np.linspace(0, 1, n_)))

    lorenz_pts = []
    srt = np.sort(logv)  # 按播放降序的累计份额：直接用 view
    vv = np.sort([v["stat"]["view"] for v in trusted])[::-1]
    cum = np.cumsum(vv) / vv.sum()
    idx = np.linspace(0, len(vv) - 1, 41).astype(int)
    for i in idx:
        lorenz_pts.append([round(i / (len(vv) - 1) * 100, 1), round(float(cum[i] * 100), 1)])
    ranks = np.arange(1, len(vv) + 1)
    mid = (ranks >= 10) & (ranks <= len(vv) // 2)
    z = np.polyfit(np.log10(ranks[mid]), np.log10(vv[mid]), 1)
    res["lorenz"] = {
        "gini_overall": round(gini([v["stat"]["view"] for v in trusted]), 3),
        "gini_ranking": round(gini([v["stat"]["view"] for v in trusted if layer(v["source"]) == "ranking"]), 3),
        "gini_feed": round(gini([v["stat"]["view"] for v in trusted if layer(v["source"]) == "feed"]), 3),
        "top1_pct": round(float(vv[:max(1, len(vv) // 100)].sum() / vv.sum() * 100), 1),
        "top10_pct": round(float(vv[:max(1, len(vv) // 10)].sum() / vv.sum() * 100), 1),
        "curve": lorenz_pts,
        "zipf_slope": round(float(z[0]), 3),
    }
    print(f"[C 洛伦兹] 基尼={res['lorenz']['gini_overall']} top1%占 {res['lorenz']['top1_pct']}% "
          f"top10%占 {res['lorenz']['top10_pct']}% Zipf斜率={res['lorenz']['zipf_slope']}")

    # ============ 实验D：价值指纹 PCA ============
    keys = ["coin_v", "fav_v", "like_v", "dan_v"]
    zn = defaultdict(list)
    for v in trusted:
        if layer(v["source"]) == "ranking":
            zn[v["_zone"]].append(v)
    zones_rows = []
    for zname, grp in zn.items():
        if len(grp) < 8:
            continue
        zones_rows.append({"zone": zname, "n": len(grp),
                           "coin_v": float(np.median([rate(v, "coin") for v in grp])),
                           "fav_v": float(np.median([rate(v, "favorite") for v in grp])),
                           "like_v": float(np.median([rate(v, "like") for v in grp])),
                           "dan_v": float(np.median([rate(v, "danmaku") for v in grp]))})
    M = np.array([[r[k] for k in keys] for r in zones_rows])
    Mz = (M - M.mean(0)) / (M.std(0) + 1e-9)
    C = np.cov(Mz.T)
    evals, evecs = np.linalg.eigh(C)
    o = np.argsort(evals)[::-1]
    pc = Mz @ evecs[:, o[:2]]
    for r, p2 in zip(zones_rows, pc):
        r["pc1"], r["pc2"] = round(float(p2[0]), 2), round(float(p2[1]), 2)
    res["fingerprints"] = {"zones": zones_rows,
                           "var_explained": [round(float(evals[o[0]] / evals.sum()), 3),
                                             round(float(evals[o[1]] / evals.sum()), 3)],
                           "loadings": {k: [round(float(evecs[i, o[0]]), 2), round(float(evecs[i, o[1]]), 2)]
                                        for i, k in enumerate(keys)}}
    print(f"[D 指纹] {len(zones_rows)} 分区 PC1+PC2 方差 {res['fingerprints']['var_explained']}")

    # ============ 实验E：信号分歧矩阵 ============
    sig_defs = [("赞/播", "like"), ("币/播", "coin"), ("藏/播", "favorite"),
                ("弹/播", "danmaku"), ("享/播", "share"), ("评/播", "reply")]
    S = np.array([[rate(v, k) for _, k in sig_defs] for v in trusted])
    rho, pm = st.spearmanr(S)
    res["signal_matrix"] = {"keys": [n for n, _ in sig_defs],
                            "rho": [[round(float(x), 2) for x in row] for row in rho]}
    print("[E 信号矩阵]")

    # ============ 实验F：网格搜索 ============
    subsets = {"L": [0, 0, 1], "C": [0, 1, 0], "F": [1, 0, 0], "LC": [0, 1, 1],
               "FC": [1, 1, 0], "LFC": [1, 1, 1], "基准3/2/0.3": W_BASE and [3, 2, 0.3]}
    grid_rows = []
    social = np.array([v["_social"] for v in trusted])
    layers_all = sorted({layer(v["source"]) for v in trusted})
    for name, w in subsets.items():
        for denom in ("view", "sqrt_view", "log10_view"):
            sc = np.array([score_w(v, w, denom) for v in trusted])
            cl = float(st.spearmanr(sc, logv)[0])
            cs = float(st.spearmanr(sc, social)[0])
            order_idx = np.argsort(sc)
            bottom = [trusted[i] for i in order_idx[:50]]
            bl = defaultdict(int)
            for v in bottom:
                bl[layer(v["source"])] += 1
            non_rank = sum(v for k, v in bl.items() if k != "ranking") / 50.0
            grid_rows.append({"subset": name, "denom": denom,
                              "corr_logview": round(cl, 3), "corr_social": round(cs, 3),
                              "bottom_nonranking": round(non_rank, 2)})
    res["grid"] = grid_rows
    print(f"[F 网格] {len(grid_rows)} 组")

    # ============ 实验G：标题信号学 ============
    feats = [
        ("【】/[]标签栏", lambda t: bool(re.search(r"[【\[]", t))),
        ("合集/一口气", lambda t: ("合集" in t) or ("一口气" in t)),
        ("剧集切片(第N集)", lambda t: bool(re.search(r"第\s*\d+\s*[集话]", t))),
        ("疑问标题(?)", lambda t: ("？" in t) or ("?" in t)),
        ("多感叹号(≥2)", lambda t: (t.count("！") + t.count("!")) >= 2),
        ("含emoji", lambda t: bool(re.search(r"[\U0001F000-\U0001FAFF\u2600-\u27BF]", t))),
        ("空格排版(字 间 空 格)", lambda t: re.search(r"\S \S", t) is not None and len(t) <= 20),
        ("挑战体", lambda t: "挑战" in t),
        ("求互动(三连/关注)", lambda t: bool(re.search(r"三连|一键三连|关注|点赞投币", t))),
        ("长标题(≥25字)", lambda t: len(t) >= 25),
    ]
    title_rows = []
    all_f7 = np.array([v["_f7"] for v in trusted])
    for name, fn in feats:
        grp = [v for v in trusted if fn(v.get("title") or "")]
        rest = [v for v in trusted if not fn(v.get("title") or "")]
        if len(grp) < 15:
            continue
        u, p = st.mannwhitneyu([v["_f7"] for v in grp], [v["_f7"] for v in rest])
        title_rows.append({"feat": name, "n": len(grp),
                           "f7_med": round(float(np.median([v["_f7"] for v in grp])), 4),
                           "rest_med": round(float(np.median([v["_f7"] for v in rest])), 4),
                           "p_mwu": float(f"{p:.2g}")})
    title_rows.sort(key=lambda r: r["f7_med"])
    res["titles"] = title_rows
    print("[G 标题信号]")
    for r in title_rows:
        print(f"   {r['feat']:16s} n={r['n']:4d} 比值中位={r['f7_med']:.4f} vs {r['rest_med']:.4f} p={r['p_mwu']}")

    # ============ 实验H：保质期（层内年龄分析） ============
    fd = [v for v in trusted if layer(v["source"]) == "feed" and v["_cbi"] is not None]
    fresh = sum(1 for v in fd if v["_age"] < 7)
    age_r = float(st.spearmanr([v["_age"] for v in fd], [v["_cbi"] for v in fd])[0]) if len(fd) > 20 else None

    def age_bands_of(grp, defs):
        rows = []
        for lo, hi, name in defs:
            sel = [v for v in grp if lo <= v["_age"] < hi and v["_cbi"] is not None]
            if len(sel) < 5:
                continue
            rows.append({"band": name, "n": len(sel),
                         "cbi_med": round(float(np.median([v["_cbi"] for v in sel])), 3),
                         "view_med": int(np.median([v["stat"]["view"] for v in sel]))})
        return rows

    feed_defs = [(0, 1, "<1天"), (1, 3, "1-3天"), (3, 7, "3-7天"), (7, 30, "1-4周")]
    rank_defs = [(0, 7, "<1周"), (7, 30, "1-4周"), (30, 180, "1-6月"), (180, 3650, ">6月")]
    rk_age = [v for v in trusted if layer(v["source"]) == "ranking"]
    rk_r = float(st.spearmanr([v["_age"] for v in rk_age], [v["_cbi"] for v in rk_age])[0]) if len(rk_age) > 20 else None
    res["age"] = {"feed_fresh_pct": round(fresh / max(len(fd), 1), 3), "n_feed": len(fd),
                  "feed_corr_age_cbi": round(age_r, 3) if age_r is not None else None,
                  "ranking_corr_age_cbi": round(rk_r, 3) if rk_r is not None else None,
                  "bands_feed": age_bands_of(fd, feed_defs),
                  "bands_ranking": age_bands_of(rk_age, rank_defs)}
    print(f"[H 保质期] feed层 <7天占比 {fresh}/{len(fd)}；feed内 age~CBI={age_r:.3f}；ranking内={rk_r:.3f}")

    # ============ 实验I：手搓检验 ============
    hm_re = re.compile(r"手搓|自制|耗时|历时|一个人|独自|个月|年半|三年|两年|爆肝|熬夜做完")
    hm = [v for v in trusted if hm_re.search(v.get("title") or "")]
    rest = [v for v in trusted if not hm_re.search(v.get("title") or "")]
    u1, p_cbi = st.mannwhitneyu([v["_cbi"] for v in hm if v["_cbi"] is not None],
                                [v["_cbi"] for v in rest if v["_cbi"] is not None])
    u2, p_view = st.mannwhitneyu([v["stat"]["view"] for v in hm], [v["stat"]["view"] for v in rest])
    res["handmade"] = {"n": len(hm),
                       "cbi_med": round(float(np.median([v["_cbi"] for v in hm if v["_cbi"]])), 3),
                       "rest_cbi_med": round(float(np.median([v["_cbi"] for v in rest if v["_cbi"]])), 3),
                       "p_cbi": float(f"{p_cbi:.2g}"),
                       "view_med": int(np.median([v["stat"]["view"] for v in hm])),
                       "rest_view_med": int(np.median([v["stat"]["view"] for v in rest])),
                       "p_view": float(f"{p_view:.2g}")}
    print(f"[I 手搓] n={len(hm)} CBI中位 {res['handmade']['cbi_med']} vs {res['handmade']['rest_cbi_med']} p={p_cbi:.2g}；"
          f"播放中位 {res['handmade']['view_med']} vs {res['handmade']['rest_view_med']} p={p_view:.2g}")

    # ============ 实验J：时间线模拟 ============
    def portrait(v):
        dim = v.get("dimension") or {}
        w, h = dim.get("width") or 0, dim.get("height") or 0
        rot = dim.get("rotate") or 0
        if rot in (90, 270):
            w, h = h, w
        return (w and h and w / h < 0.9)

    cut = [v for v in fd if (v["_cbi"] is not None and v["_cbi"] < 0.5) or (v["_dur"] and v["_dur"] <= 75) or portrait(v)]
    kept = [v for v in fd if v not in cut]
    tot_view = sum(v["stat"]["view"] for v in fd)
    res["simulate"] = {
        "feed_n": len(fd), "cut_pct": round(len(cut) / len(fd), 3),
        "cut_view_share": round(sum(v["stat"]["view"] for v in cut) / tot_view, 3),
        "cut_med_view": int(np.median([v["stat"]["view"] for v in cut])) if cut else 0,
        "kept_med_view": int(np.median([v["stat"]["view"] for v in kept])) if kept else 0,
        "reasons": {"低CBI": sum(1 for v in cut if v["_cbi"] is not None and v["_cbi"] < 0.5),
                    "短视频": sum(1 for v in cut if v["_dur"] and v["_dur"] <= 75),
                    "竖屏": sum(1 for v in cut if portrait(v))},
    }
    print(f"[J 模拟] feed层 {len(fd)} 条砍 {len(cut)}（{res['simulate']['cut_pct']:.0%}），"
          f"砍掉的播放份额 {res['simulate']['cut_view_share']:.0%}")

    # ============ 实验 K：时长×质量、时代演化、层间对比 ============
    # K1 时长 vs F7/CBI
    dur_defs = [(0, 60, "<1分钟"), (60, 180, "1-3分钟"), (180, 600, "3-10分钟"),
                (600, 1800, "10-30分钟"), (1800, 86400, "30分钟-1天"), (86400, 10**9, ">1天")]
    dur_rows = []
    for lo, hi, name in dur_defs:
        grp = [v for v in trusted if lo <= (v["_dur"] or 0) < hi and v["_cbi"] is not None]
        if len(grp) < 30:
            continue
        dur_rows.append({"band": name, "n": len(grp),
                         "f7_med": round(float(np.median([v["_f7"] for v in grp])), 4),
                         "cbi_med": round(float(np.median([v["_cbi"] for v in grp])), 3),
                         "view_med": int(np.median([v["stat"]["view"] for v in grp]))})
    # 时长偏相关：控制 年龄 + 层 + 分区（仅 ranking+series 层，样本足够）
    ds = [v for v in trusted if v["_logdur"] is not None and v["_cbi"] is not None
          and layer(v["source"]) in ("ranking", "series", "popular", "precious")]
    ds_zones = sorted({v["_zone"] for v in ds if v["_zone"]})
    dummies_d = np.zeros((len(ds), len(ds_zones)))
    for i, v in enumerate(ds):
        if v["_zone"] in ds_zones:
            dummies_d[i, ds_zones.index(v["_zone"])] = 1.0
    p_dur_full = partial(np.array([v["_f7"] for v in ds]), np.array([v["_logdur"] for v in ds]),
                         [np.array([v["_logage"] for v in ds])] + [dummies_d[:, j] for j in range(1, len(ds_zones))])
    p_dur_raw = float(st.pearsonr([v["_f7"] for v in ds], [v["_logdur"] for v in ds])[0])
    # K2 时代演化（series 层）
    yr_rows = []
    for yr in sorted({v["_year"] for v in trusted if layer(v["source"]) == "series" and v["_year"]}):
        grp = [v for v in trusted if layer(v["source"]) == "series" and v["_year"] == yr]
        if len(grp) < 50:
            continue
        yr_rows.append({"year": yr, "n": len(grp),
                        "f7_med": round(float(np.median([v["_f7"] for v in grp])), 4),
                        "coin_v": round(float(np.median([rate(v, "coin") for v in grp])), 4),
                        "like_v": round(float(np.median([rate(v, "like") for v in grp])), 4),
                        "fav_v": round(float(np.median([rate(v, "favorite") for v in grp])), 4),
                        "view_med": int(np.median([v["stat"]["view"] for v in grp]))})
    # K3 层间对比（同为「火」的不同入选机制）
    layer_rows = []
    for lname, pat in (("每周必看(周精选)", "series"), ("入站必刷(历史经典)", "precious"),
                       ("当前榜单", "ranking"), ("热门频道", "popular"), ("推荐流", "feed")):
        grp = [v for v in trusted if layer(v["source"]) == pat and v["_cbi"] is not None]
        if len(grp) < 30:
            continue
        layer_rows.append({"layer": lname, "n": len(grp),
                           "f7_med": round(float(np.median([v["_f7"] for v in grp])), 4),
                           "cbi_med": round(float(np.median([v["_cbi"] for v in grp])), 3),
                           "view_med": int(np.median([v["stat"]["view"] for v in grp]))})
    res["experiment_k"] = {"dur_bands": dur_rows, "dur_partial_raw": round(p_dur_raw, 3),
                           "dur_partial_ctrl": round(p_dur_full, 3), "n_dur": len(ds),
                           "years": yr_rows, "layers": layer_rows}
    print(f"[K1 时长] raw={p_dur_raw:.3f} 控年龄+分区={p_dur_full:.3f} (n={len(ds)})")
    print(f"[K2 时代] {len(yr_rows)} 个年份组")
    print(f"[K3 层间] {[(r['layer'], r['n']) for r in layer_rows]}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(clean(res), f, ensure_ascii=False, indent=1)
    # CBI 基线曲线单独落盘（config/clean.config.json 的 cbi.baseline_curve 指向它）
    baseline_path = os.path.join(ROOT, "data", "analysis", "cbi_baseline.json")
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(clean({"fit_at": res["meta"]["collected_at"], "n": len(trusted),
                         "p50_curve": p50c, "p25_curve": p25c}), f, ensure_ascii=False, indent=1)
    print(f"[saved] {args.out} + {baseline_path}")


if __name__ == "__main__":
    main()
