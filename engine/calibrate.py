# -*- coding: utf-8 -*-
"""洁净B站 · 权重/阈值校准
读取采集样本，统计 (收藏×w1 + 投币×w2 + 点赞×w3)/播放 比值的分布，
按分位数建议 tiers 阈值，输出校准报告 md + 可直接粘贴的配置片段。

用法：
  python engine/calibrate.py --data data/samples/sample_xxx.json
"""
import argparse
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict

import scoring

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pct(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (vx * vy) if vx and vy else None


def ratio_of(video, cfg):
    w = cfg["scoring"]["weights"]
    stat = video.get("stat") or {}
    view = stat.get("view") or 0
    if view <= 0:
        return None, 0
    raw = ((stat.get("favorite") or 0) * w["favorite"]
           + (stat.get("coin") or 0) * w["coin"]
           + (stat.get("like") or 0) * w["like"])
    denom = scoring.denominator(view, cfg["scoring"].get("denominator_mode", "view"))
    return raw / denom, view


def main():
    ap = argparse.ArgumentParser(description="洁净B站 阈值校准")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "clean.config.json"))
    ap.add_argument("--data", required=True, help="采集样本 json 路径")
    args = ap.parse_args()
    cfg = scoring.load_config(args.config)
    w = cfg["scoring"]["weights"]

    with open(args.data, encoding="utf-8") as f:
        payload = json.load(f)
    videos = payload["videos"] if isinstance(payload, dict) else payload
    src_dist = Counter(v.get("source", "?") for v in videos)

    # 全量比值（不截断，先看分布）
    all_pairs = []
    for v in videos:
        r, view = ratio_of(v, cfg)
        if r is not None:
            all_pairs.append((v, r))
    min_view = cfg["scoring"]["min_view_threshold"]
    trusted = [(v, r) for v, r in all_pairs if (v.get("stat") or {}).get("view", 0) >= min_view]
    vals = sorted(r for _, r in trusted)

    stats = {f"P{p}": round(pct(vals, p), 4) for p in (5, 10, 25, 50, 75, 80, 90, 95)}
    stats["mean"] = round(sum(vals) / len(vals), 4) if vals else 0.0

    # 分组对比
    groups = defaultdict(list)
    for v, r in trusted:
        p = scoring.is_portrait(v, cfg)
        if p is True:
            groups["竖屏"].append(r)
        elif p is False:
            groups["横屏"].append(r)
        dur = v.get("duration") or 0
        if dur <= cfg["filters"]["short_video_max_duration_sec"]:
            groups["短视频"].append(r)
        else:
            groups["长视频"].append(r)
    group_med = {k: round(pct(sorted(v), 50), 4) for k, v in groups.items() if v}

    # 比值 vs 播放量（log）相关性：预期负相关（大播放稀释比率）
    r_corr = pearson([math.log10(max((v.get("stat") or {}).get("view", 1), 10)) for v, _ in trusted],
                     [r for _, r in trusted])

    # feed 子集（最接近真实刷到的分布）
    feed_pairs = [(v, r) for v, r in trusted if v.get("source") == "feed"]
    feed_vals = sorted(r for _, r in feed_pairs)
    feed_stats = {f"P{p}": round(pct(feed_vals, p), 4) for p in (25, 50, 80)} if feed_vals else {}

    # 建议：feed 子集优先（无则用全量）
    base = feed_vals or vals
    suggest = {
        "high": round(pct(base, 80), 4),
        "normal": round(pct(base, 50), 4),
        "low": round(pct(base, 25), 4),
    }
    suggest_block = json.dumps({
        "scoring": {"weights": w, "min_view_threshold": min_view,
                    "tiers": suggest, "denominator_mode": cfg["scoring"]["denominator_mode"]}
    }, ensure_ascii=False, indent=2)

    # 报告
    stamp = time.strftime("%Y%m%d_%H%M")
    out = os.path.join(os.path.dirname(os.path.abspath(args.data)), f"calibration-report_{stamp}.md")
    lines = [
        "# 洁净B站 · 首轮校准报告",
        f"- 时间：{time.strftime('%Y-%m-%d %H:%M')}",
        f"- 样本：{len(videos)} 个（来源分布 {dict(src_dist)}），比值可信样本（播放≥{min_view}）：{len(trusted)}",
        f"- 公式：`(收藏×{w['favorite']} + 投币×{w['coin']} + 点赞×{w['like']}) / {cfg['scoring']['denominator_mode']}`",
        "",
        "## 比值分布（trusted）",
        "| 统计值 | 数值 |", "|---|---|",
    ]
    lines += [f"| {k} | {v} |" for k, v in stats.items()]
    lines += ["", "## 分组中位数对比"] + ([f"- {k}: {v}" for k, v in group_med.items()] or ["- （无分组数据）"])
    if r_corr is not None:
        lines += ["", f"## 比值 vs log10(播放) 相关性：r = {r_corr:.3f}",
                  "（负相关说明播放量越大概率稀释比值；若明显，可把 denominator_mode 换成 sqrt_view）"]
    if feed_stats:
        lines += ["", f"## feed 子集分布（n={len(feed_vals)}，最接近真实刷到）",
                  f"- P25={feed_stats['P25']}  P50={feed_stats['P50']}  P80={feed_stats['P80']}"]
    lines += [
        "",
        "## 建议配置（粘贴回 config/clean.config.json 的 scoring 段）",
        "```json",
        suggest_block,
        "```",
        "",
        "## 注意事项",
        "- ranking/popular 来源天然偏高质，分布会整体偏右；feed 子集更接近真实首页。",
        "- 本次 feed 为**未登录态**样本；后续可用登录态（cdp-browser 抓包）复采复校。",
        "- 阈值是起点不是终点：按自己体感调 tiers，刷到不喜欢的就把它那档比值往下压。",
    ]
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[calibrate] n={len(trusted)} trusted / {len(all_pairs)} total")
    print(f"[calibrate] distribution: {stats}")
    print(f"[calibrate] group medians: {group_med}")
    print(f"[calibrate] corr(ratio, log10 view) = {r_corr if r_corr is None else round(r_corr, 3)}")
    print(f"[calibrate] suggested tiers: {suggest}")
    print(f"[done] report -> {out}")


if __name__ == "__main__":
    main()
