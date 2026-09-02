# -*- coding: utf-8 -*-
"""感谢几何 · AG-Folium 离线原型（验证 V4/V5）

年代叶状基线：baseline_y(t) = 每年代 y 内 log10(view) 桶(0.25宽) 的 F7 中位数曲线。
对照：全局单基线（不分年代，同桶宽）。

  V4 排名翻转：叶基线 vs 单基线各自给 Top-20（2019-2022 段内），翻转率 ≥ 8%？
  V5 残差：叶内对数空间 MSE ≤ 全局基线 MSE 的 90%？
  副产物：年代行为档案（每年代 coin/fav/like 每播放率中位数）——「感谢习惯迁移」
用法： python engine/ag_folium.py
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
from fav_miner import f7_of, load_merged_mine  # noqa: E402

BUCKET = 0.25
MIN_LEAF_N = 30  # 独立成叶的最低样本数（文档 §3）
MIN_BUCKET_N = 6  # 桶内中位数最低点数


def bucket_of(v):
    return round(math.log10(max(v, 10)) / BUCKET)


def build():
    merged = load_merged_mine(os.path.join(ROOT, "data", "fav_mine"))
    rows = []
    for v in merged["videos"]:
        if (v.get("stat") or {}).get("view", 0) < 3000 or not v.get("year") or v["year"] == "?":
            continue
        st = v["stat"]
        rows.append({"bvid": v["bvid"], "year": int(v["year"]), "view": st["view"],
                     "f7": f7_of(st),
                     "coin_r": (st.get("coin") or 0) / st["view"],
                     "fav_r": (st.get("favorite") or 0) / st["view"],
                     "like_r": (st.get("like") or 0) / st["view"]})
    return rows


def curve(points, key=lambda p: p["f7"]):
    """log-view 桶 → 中位数曲线。"""
    b = defaultdict(list)
    for p in points:
        b[bucket_of(p["view"])].append(key(p))
    return {k: sorted(vs)[len(vs) // 2] for k, vs in b.items() if len(vs) >= MIN_BUCKET_N}


def curve_mse(points, curve):
    errs = []
    for p in points:
        c = curve.get(bucket_of(p["view"]))
        if c is not None:
            errs.append((math.log(max(p["f7"], 1e-6)) - math.log(max(c, 1e-6))) ** 2)
    return sum(errs) / len(errs) if errs else None


def main():
    rows = build()
    print(f"[rows] {len(rows)} videos with year+stat")
    by_year = defaultdict(list)
    for p in rows:
        by_year[p["year"]].append(p)
    leaves = {y: ps for y, ps in by_year.items() if len(ps) >= MIN_LEAF_N}
    print(f"[leaves] n>=30 的年代: {sorted(leaves)}")
    interp_years = sorted(y for y, ps in by_year.items() if len(ps) < MIN_LEAF_N)
    print(f"[interp] 插值年份（不独立成叶）: {interp_years}")

    global_curve = curve(rows)
    leaf_curves = {y: curve(ps) for y, ps in leaves.items()}

    # 年代行为档案
    profile = {}
    for y in sorted(by_year):
        ps = by_year[y]
        med = lambda k: sorted(p[k] for p in ps)[len(ps) // 2]
        profile[y] = {"n": len(ps),
                      "coin_r_med": round(med("coin_r"), 5),
                      "fav_r_med": round(med("fav_r"), 5),
                      "like_r_med": round(med("like_r"), 5),
                      "f7_med": round(med("f7"), 4)}

    # V4：2019-2022 段 Top-20 翻转
    seg = [p for p in rows if 2019 <= p["year"] <= 2022]
    # 叶基线 CBI（仅用所属叶；插值年份用全局）
    def leaf_cbi(p):
        cv = leaf_curves.get(p["year"])
        c = (cv or global_curve).get(bucket_of(p["view"]))
        return p["f7"] / c if c else 0
    def global_cbi(p):
        c = global_curve.get(bucket_of(p["view"]))
        return p["f7"] / c if c else 0
    top_leaf = set(p["bvid"] for p in sorted(seg, key=leaf_cbi, reverse=True)[:20])
    top_glob = set(p["bvid"] for p in sorted(seg, key=global_cbi, reverse=True)[:20])
    flips = len(top_leaf.symmetric_difference(top_glob))
    v4 = {"seg_n": len(seg), "flip_count": flips, "flip_rate": round(flips / 20, 3),
          "pass": flips / 20 >= 0.08}

    # V5：残差
    mse_leaf, mse_glob, n_mse = [], [], 0
    for y, ps in leaves.items():
        cv = leaf_curves[y]
        e_l = curve_mse(ps, cv)
        e_g = curve_mse(ps, global_curve)
        if e_l is not None and e_g is not None:
            mse_leaf.append(e_l * len(ps))
            mse_glob.append(e_g * len(ps))
            n_mse += len(ps)
    mse_l = sum(mse_leaf) / n_mse if n_mse else None
    mse_g = sum(mse_glob) / n_mse if n_mse else None
    v5 = {"mse_leaf": round(mse_l, 6) if mse_l else None,
          "mse_global": round(mse_g, 6) if mse_g else None,
          "ratio": round(mse_l / mse_g, 3) if mse_l and mse_g else None,
          "pass": (mse_l / mse_g <= 0.9) if mse_l and mse_g else None}

    out = {"meta": {"n": len(rows), "leaves": sorted(leaves), "interp": interp_years},
           "year_behavior_profile": profile,
           "v4": v4, "v5": v5,
           "leaf_curves": {str(y): {str(k): round(v, 5) for k, v in cv.items()}
                           for y, cv in leaf_curves.items()},
           "global_curve": {str(k): round(v, 5) for k, v in global_curve.items()}}
    outp = os.path.join(ROOT, "data", "fav_mine", "ag_folium_summary.json")
    json.dump(out, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("=== V4 排名翻转（2019-2022 Top-20）===")
    print(f"  翻转 {flips}/20 = {flips/20:.0%}  {'✓' if v4['pass'] else '✗'}")
    print("=== V5 残差（对数 MSE）===")
    print(f"  叶 {v5['mse_leaf']} vs 全局 {v5['mse_global']}  ratio={v5['ratio']}  "
          f"{'✓' if v5['pass'] else '✗'}")
    print("--- 年代行为档案（每播放率中位数）---")
    for y in sorted(profile):
        r = profile[y]
        print(f"  {y}: n={r['n']:4d}  coin={r['coin_r_med']:.4f}  fav={r['fav_r_med']:.4f}  "
              f"like={r['like_r_med']:.4f}  F7={r['f7_med']:.4f}")
    print(f"[done] -> {outp}")


if __name__ == "__main__":
    main()
