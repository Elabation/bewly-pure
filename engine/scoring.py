# -*- coding: utf-8 -*-
"""洁净B站 · 评分引擎
公式（全部在 config/clean.config.json 手调）：
    score(比值) = (favorite×w_fav + coin×w_coin + like×w_like) / denominator
    denominator = view | sqrt(view) | log10(view)
分级：
    比值 >= tiers.high   -> high    （高质量）
    比值 >= tiers.normal -> normal  （正常）
    比值 >= tiers.low    -> low     （偏低）
    比值 <  tiers.low    -> junk
    view <  min_view_threshold -> unproven（播放量太低，比率不可信）

用法：
  python engine/scoring.py --data data/samples/sample_xxx.json   # 批量打分
  python engine/scoring.py --bvid BV1xxxx                        # 单视频在线试算
"""
import argparse
import json
import math
import os
import sys
import time
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config(path=None):
    path = path or os.path.join(ROOT, "config", "clean.config.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def effective_wh(dim):
    """考虑 rotate 后的有效宽高。"""
    w, h, r = dim.get("width") or 0, dim.get("height") or 0, dim.get("rotate") or 0
    if r in (90, 270):
        w, h = h, w
    return w, h


def is_portrait(video, cfg):
    """True=竖屏 False=非竖屏 None=未知"""
    f = cfg["filters"]["portrait"]
    if not f.get("enabled", True):
        return False
    w, h = effective_wh(video.get("dimension") or {})
    if not w or not h:
        return None
    return (w / h) < float(f["wh_ratio_min"])


def denominator(view, mode):
    if mode == "sqrt_view":
        return math.sqrt(max(view, 1))
    if mode == "log10_view":
        return math.log10(max(view, 10))
    return max(view, 1)


def tier_of(ratio, view, cfg):
    sc = cfg["scoring"]
    if view < sc["min_view_threshold"]:
        return sc.get("below_min_view_tier", "unproven")
    t = sc["tiers"]
    if ratio >= t["high"]:
        return "high"
    if ratio >= t["normal"]:
        return "normal"
    if ratio >= t["low"]:
        return "low"
    return "junk"


def score_video(video, cfg):
    sc, flt = cfg["scoring"], cfg["filters"]
    w = sc["weights"]
    stat = video.get("stat") or {}
    view = stat.get("view") or 0
    raw = ((stat.get("favorite") or 0) * w["favorite"]
           + (stat.get("coin") or 0) * w["coin"]
           + (stat.get("like") or 0) * w["like"])
    denom = denominator(view, sc.get("denominator_mode", "view"))
    ratio = (raw / denom) if view > 0 else 0.0
    tier = tier_of(ratio, view, cfg)

    reasons = []
    dur = video.get("duration") or 0
    if dur and dur <= flt["short_video_max_duration_sec"]:
        reasons.append(f"短视频({dur}s)")
    p = is_portrait(video, cfg)
    if p is True:
        reasons.append("竖屏")
    if video.get("is_live"):
        reasons.append("直播")
    if flt["min_views"] and view < flt["min_views"]:
        reasons.append(f"播放过低({view})")
    title = video.get("title") or ""
    hit = [k for k in (flt.get("block_keywords") or []) if k and k in title]
    if hit:
        reasons.append("关键词:" + "|".join(hit))
    hide_tiers = list(flt.get("hide_tiers") or [])
    if flt.get("hide_unproven"):
        hide_tiers.append("unproven")
    if tier in hide_tiers:
        reasons.append(f"评分{tier}({ratio:.3f})")

    return {
        "bvid": video.get("bvid"),
        "title": title,
        "tier": tier,
        "ratio": round(ratio, 4),
        "raw_weighted": round(raw, 1),
        "view": view,
        "duration": dur,
        "portrait": p,
        "source": video.get("source"),
        "filtered": bool(reasons),
        "reasons": reasons,
    }


def score_dataset(videos, cfg):
    return [score_video(v, cfg) for v in videos]


def print_summary(rows):
    order = ["high", "normal", "low", "junk", "unproven"]
    c = Counter(r["tier"] for r in rows)
    f = Counter()
    for r in rows:
        for reason in r["reasons"]:
            f[reason.split("(")[0].split(":")[0]] += 1
    print("--- tier 分布 ---")
    for t in order:
        print(f"  {t:9s}: {c.get(t, 0)}")
    print("--- 过滤原因分布（可叠加） ---")
    for k, v in f.most_common():
        print(f"  {k}: {v}")


def main():
    ap = argparse.ArgumentParser(description="洁净B站 评分引擎")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "clean.config.json"))
    ap.add_argument("--data", default=None, help="采集样本 json 路径")
    ap.add_argument("--out", default=None)
    ap.add_argument("--bvid", default=None, help="单视频在线试算")
    args = ap.parse_args()
    cfg = load_config(args.config)

    if args.bvid:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from collect_stats import BiliClient
        cli = BiliClient()
        v = cli.fetch_view(args.bvid)
        print(json.dumps(score_video(v, cfg), ensure_ascii=False, indent=2))
        return

    if not args.data:
        print("需要 --data <样本json> 或 --bvid <BV号>")
        sys.exit(2)

    with open(args.data, encoding="utf-8") as f:
        payload = json.load(f)
    videos = payload["videos"] if isinstance(payload, dict) else payload
    rows = score_dataset(videos, cfg)

    out = args.out or os.path.splitext(args.data)[0] + "_scored.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"meta": {"scored_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "config_version": cfg.get("config_version")},
                   "rows": rows}, f, ensure_ascii=False, indent=2)

    print_summary(rows)
    rows_sorted = sorted(rows, key=lambda r: r["ratio"], reverse=True)
    print("--- 比值最高 10 ---")
    for r in rows_sorted[:10]:
        print(f"  {r['ratio']:.4f} [{r['tier']:8s}] {r['title'][:36]} ({r['bvid']})")
    print("--- 比值最低 10 ---")
    for r in rows_sorted[-10:]:
        print(f"  {r['ratio']:.4f} [{r['tier']:8s}] {r['title'][:36]} ({r['bvid']})")
    print(f"[done] -> {out}")


if __name__ == "__main__":
    main()
