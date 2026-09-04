# -*- coding: utf-8 -*-
"""统计深挖八件套（favmine 版）——「统计学的魅力时刻」

输入：merged 全库（阶段 A/B 产出后由编排器调用）；输出：deep_mining_summary.json。
全部零请求、纯统计、手写无 scipy。口径：cbi_scale 单一定义源，tier 现算。

  S1 三连绑定松紧史   —— 五维行为相关矩阵随年代漂移（用户习惯结构演化）
  S2 CBI 分布形态学   —— 各年代偏度/双峰性：神作是右尾延伸还是水位上移
  S3 幸存者偏差量化   —— 对照组 vs 挖掘组：收藏行为的选择效应强度
  S4 考古价值指数     —— 分区×年代：哪类内容的老视频相对更神
  S5 宝藏 UP 主识别   —— 同一作者多部作品被收藏（需 owner 字段，缺失则跳过）
  S6 抗衰老类型学     —— CBI 随年龄的半衰期按分区对比
  S7 AG×CBI 联合分布  —— 二维密度四象限（依赖 ag_depth_summary.json）
  S8 流耦合摘要       —— E1/E2/E3 判定数字的汇编（依赖既有 summary）
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
sys.path.insert(0, os.path.join(ROOT, "engine"))
from cbi_scale import SCALE, GOOD_TIERS, tier_of  # noqa: E402

MINE = os.path.join(ROOT, "data", "fav_mine")
BEHAV = ("coin", "fav", "like", "danmaku", "share")
BEHAV_KEY = {"coin": "coin", "fav": "favorite", "like": "like", "danmaku": "danmaku", "share": "share"}


def pearson(xs, ys):
    n = len(xs)
    if n < 10:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return round(num / den, 4) if den else None


def skewness(xs):
    n = len(xs)
    if n < 30:
        return None
    m = sum(xs) / n
    s = math.sqrt(sum((x - m) ** 2 for x in xs) / n)
    if not s:
        return None
    return round(sum(((x - m) / s) ** 3 for x in xs) / n, 4)


def main():
    merged = latest_merged()
    if not merged:
        print("[ABORT] 无 merged 全库——先跑 fav_miner --analyze ALL", flush=True)
        sys.exit(1)
    payload = json.load(open(merged, encoding="utf-8"))
    for v in payload["videos"]:
        v["tier"] = tier_of(v.get("cbi", 0), v.get("view") or 0)
    mined = [v for v in payload["videos"] if (v.get("view") or 0) >= 3000]
    print(f"[load] merged={os.path.basename(merged)} 合格视频 {len(mined)}", flush=True)
    out = {"merged": os.path.basename(merged), "n_qual": len(mined)}

    # ── S1 三连绑定松紧史 ──
    by_year = defaultdict(list)
    for v in mined:
        y = v.get("year")
        if isinstance(y, str) and y.isdigit():
            by_year[int(y)].append(v)
    s1 = {}
    for y in sorted(by_year):
        vs = by_year[y]
        if len(vs) < 80:
            continue
        rates = {b: [max(1e-6, (v["stat"] or {}).get(BEHAV_KEY[b]) or 0) / v["view"] for v in vs]
                 for b in BEHAV}
        s1[str(y)] = {"n": len(vs),
                      **{f"{a}-{b}": pearson(rates[a], rates[b])
                         for i, a in enumerate(BEHAV) for b in BEHAV[i + 1:]}}
    out["S1_coin_fav_by_year"] = {y: d.get("coin-fav") for y, d in s1.items()}
    out["S1_full"] = s1

    # ── S2 CBI 分布形态学 ──
    s2 = {}
    for y in sorted(by_year):
        vs = by_year[y]
        if len(vs) < 80:
            continue
        cbis = [v["cbi"] for v in vs]
        s2[str(y)] = {"n": len(vs), "mean": round(sum(cbis) / len(cbis), 3),
                      "skew": skewness(cbis),
                      "p90": round(sorted(cbis)[int(len(cbis) * .9)], 2),
                      "high_rate": round(sum(1 for v in vs if v["tier"] == "high") / len(vs), 3)}
    out["S2_cbi_morphology"] = s2

    # ── S3 幸存者偏差（对照 vs 挖掘组，同 view 段配比）──
    ctrl = []
    for fn in ("favmine_20260902_190815.json",):
        pass  # 对照组在重采库中暂缺——使用臂② uploader 低样本代理或留空
    ctrl_payload = None
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "merged" not in fn and "_analysis" not in fn:
            meta = json.load(open(os.path.join(MINE, fn), encoding="utf-8")).get("meta") or {}
            if meta.get("arm") == "all" and meta.get("hop") is None:
                ctrl_payload = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
                break
    s3 = {}
    if ctrl_payload:
        ctrl = [v for v in ctrl_payload.get("videos") or [] if (v.get("view") or 0) >= 3000]
        for lo, hi in ((3000, 30000), (30000, 300000), (300000, 10 ** 9)):
            a = [v["cbi"] for v in mined if lo <= v["view"] < hi]
            b = [v["cbi"] for v in ctrl if lo <= v["view"] < hi]
            if len(a) >= 50 and len(b) >= 20:
                s3[f"view_{lo}-{hi}"] = {
                    "mined_mean": round(sum(a) / len(a), 3), "ctrl_mean": round(sum(b) / len(b), 3),
                    "mined_high": round(sum(1 for v in a if v >= SCALE["high"]) / len(a), 3),
                    "ctrl_high": round(sum(1 for v in b if v >= SCALE["high"]) / len(b), 3),
                    "selection_gap": round(sum(a) / len(a) - sum(b) / len(b), 3)}
    out["S3_survivorship"] = {"note": "对照组 = uploader 臂（收藏即选择效应的对照组）" if s3 else "缺",
                              "bands": s3}

    # ── S4 考古价值指数（分区×年代）──
    zone_year = defaultdict(lambda: [0, 0, 0])  # tname -> [n, high, cbi_sum]
    for v in mined:
        z = v.get("tname") or "?"
        d = zone_year[z]
        d[0] += 1; d[1] += v["tier"] == "high"; d[2] += v["cbi"]
    old_year = {y for y in by_year if y <= 2021}
    s4 = []
    for z, (n, h, cs) in zone_year.items():
        if n < 40:
            continue
        vs = [v for v in mined if v.get("tname") == z]
        old = [v for v in vs if v.get("year") in old_year or not isinstance(v.get("year"), str)]
        new = [v for v in vs if v.get("year") not in old_year]
        if len(old) < 15 or len(new) < 15:
            continue
        ro = sum(1 for v in old if v["tier"] == "high") / len(old)
        rn = sum(1 for v in new if v["tier"] == "high") / len(new)
        s4.append({"zone": z, "n": n, "old_high": round(ro, 3), "new_high": round(rn, 3),
                   "archaeo_index": round(ro / max(rn, 0.02), 2)})
    s4.sort(key=lambda d: -d["archaeo_index"])
    out["S4_archaeo_top"] = s4[:10]

    # ── S5 宝藏 UP 主识别 ──
    by_up = defaultdict(lambda: [0, 0, set()])
    for v in mined:
        if v.get("up"):
            d = by_up[v["up"]]
            d[0] += 1; d[1] += v["tier"] == "high"
            if v["tier"] == "high":
                d[2].add(v["bvid"])
    s5 = sorted(({"up": u[-6:], "videos": d[0], "high": d[1],
                  "high_rate": round(d[1] / d[0], 3)} for u, d in by_up.items() if d[0] >= 5),
                key=lambda x: (-x["high"], -x["videos"]))[:12]
    out["S5_treasure_ups"] = s5

    # ── S6 抗衰老类型学（分区内 CBI ~ log 年龄 斜率）──
    now = json.load(open(merged, encoding="utf-8")).get("meta", {}).get("mined_at")
    s6 = []
    for z, (n, _, _) in zone_year.items():
        if n < 60:
            continue
        pts = []
        for v in mined:
            if v.get("tname") != z or not v.get("pubdate"):
                continue
            age_days = max(1.0, (time.time() - v["pubdate"]) / 86400.0)
            pts.append((math.log10(age_days), v["cbi"]))
        if len(pts) < 60:
            continue
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        r = pearson(xs, ys)
        s6.append({"zone": z, "cbi_vs_logage_r": r, "n": len(pts)})
    s6 = [d for d in s6 if d["cbi_vs_logage_r"] is not None]
    s6.sort(key=lambda d: d["cbi_vs_logage_r"])
    out["S6_aging"] = {"most_anti_aging": s6[:5], "fastest_decaying": s6[-5:]}

    # ── S7 AG×CBI 联合分布 ──
    agp = os.path.join(MINE, "ag_depth_summary.json")
    if os.path.exists(agp):
        try:
            ag = json.load(open(agp, encoding="utf-8"))
            quad = ag.get("v2") or {}
            out["S7_ag_cbi"] = {"ag_only_rate": quad.get("ag_only_rate"),
                                "cbi_only_rate": quad.get("cbi_only_rate"),
                                "both_rate": quad.get("both_rate")}
        except Exception:
            pass

    # ── S8 流耦合摘要 ──
    s8 = {}
    for fn, key in (("e1_homophily_summary.json", "e1"), ("hop_verdict.json", "hops")):
        p = os.path.join(MINE, fn)
        if os.path.exists(p):
            s8[key] = json.load(open(p, encoding="utf-8"))
    out["S8_flow"] = s8

    outp = os.path.join(MINE, "deep_mining_summary.json")
    json.dump(out, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[done] S1 years={len(s1)} S2 years={len(s2)} S3 bands={len(s3)} "
          f"S4 zones={len(s4)} S5 ups={len(s5)} S6 zones={len(s6)}\n[done] -> {outp}", flush=True)


def latest_merged():
    fs = sorted((f for f in glob.glob(os.path.join(MINE, "favmine_merged_*.json"))
                 if "_analysis" not in os.path.basename(f)), key=os.path.getmtime)
    return fs[-1] if fs else None


import glob  # noqa: E402
import time  # noqa: E402

if __name__ == "__main__":
    main()
