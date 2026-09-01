# -*- coding: utf-8 -*-
"""离线模拟过滤器判定逻辑（与 extension/content.js / config/clean.config.json v2 逐条对齐）
目的：上线前验证过滤率/误杀率。判定顺序：
  同步层：短视频75s(R1) / 标题签名正则(R7) —— 样本无 goto/live 字段，直播不计
  异步层：竖屏(R1) -> 低播放<1000(R1) -> 官方区白名单(R4) -> CBI<0.5(R2, view>=5w)
          -> 全局 tier 兜底(3k~5w) -> 乞讨正则(R8 打标)
用法： python engine/simulate_userscript.py [--data data/samples/ecosystem_v5_20260901_2050_fix.json]
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

# 与 userscript CONFIG 完全一致
CURVE = [4.5,0.2065,4.6,0.1745,4.7,0.1376,4.8,0.1247,4.9,0.1154,5.0,0.1057,5.1,0.0919,5.2,0.083,5.3,0.0742,5.4,0.0687,5.5,0.0605,5.6,0.0577,5.7,0.0557,5.8,0.058,5.9,0.0616,6.0,0.0664,6.1,0.0706,6.2,0.0779,6.3,0.082,6.4,0.0839,6.5,0.0848,6.6,0.0861,6.7,0.0861,6.8,0.0861,6.9,0.0852,7.0,0.0849,7.1,0.0854,7.2,0.0863]
WEIGHTS = {"favorite": 3.0, "coin": 2.0, "like": 0.3}
MIN_VIEW_THRESHOLD = 3000
TIERS = {"high": 0.107, "normal": 0.064, "low": 0.042}
SHORT_MAX = 75
PORTRAIT_MIN = 0.9
MIN_VIEWS = 1000
CBI_MIN_VIEW = 50000
CBI_THRESHOLD = 0.5
BLOCK_KEYWORDS = [r"第[0-9一二三四五六七八九十百]+[集话]", r"挑战[^，。！？\s]{1,12}(？|\?|成功的可能性|能成吗)"]
ZONE_WHITELIST = ["电影", "电视剧", "纪录片"]
BEGGAR_PATTERNS = [r"投币.{0,6}更新", r"三连.{0,6}更新", r"点赞过.{0,6}更新"]
HIDE_TIERS = ["junk"]  # v2：只隐藏最低档；low 打标不隐藏（R2：不冤枉规模稀释）


def f7_of(stat):
    v = stat.get("view") or 0
    raw = (stat.get("favorite") or 0) * WEIGHTS["favorite"] + (stat.get("coin") or 0) * WEIGHTS["coin"] + (stat.get("like") or 0) * WEIGHTS["like"]
    return raw / v if v > 0 else 0.0


def baseline_cbi(logv):
    c = CURVE
    if logv <= c[0]:
        return c[1]
    if logv >= c[-2]:
        return c[-1]
    for i in range(0, len(c) - 2, 2):
        if c[i] <= logv <= c[i + 2]:
            t = (logv - c[i]) / (c[i + 2] - c[i])
            return c[i + 1] + t * (c[i + 3] - c[i + 1])
    return c[-1]


def tier_of(ratio, view):
    if view < MIN_VIEW_THRESHOLD:
        return "unproven"
    t = TIERS
    return "high" if ratio >= t["high"] else "normal" if ratio >= t["normal"] else "low" if ratio >= t["low"] else "junk"


def matches_any(title, patterns):
    return any(re.search(p, title) for p in patterns)


def verdict(v):
    """复刻 asyncVerdict，返回 (hide, reasons, cbi, beggar, tier)"""
    stat = v["stat"]
    view = stat.get("view") or 0
    f7 = f7_of(stat)
    tier = tier_of(f7, view)
    reasons, cbi, beggar = [], None, False

    dim = v.get("dimension") or {}
    w, h = dim.get("width") or 0, dim.get("height") or 0
    rot = dim.get("rotate") or 0
    if rot in (90, 270):
        w, h = h, w
    if w and h and w / h < PORTRAIT_MIN:
        reasons.append("竖屏")
    if view < MIN_VIEWS:
        reasons.append(f"低播放({view})")

    tname = v.get("tname") or ""
    whitelisted = any(z in tname for z in ZONE_WHITELIST)

    if view >= CBI_MIN_VIEW and not whitelisted:
        cbi = f7 / baseline_cbi(math.log10(view))
        if cbi < CBI_THRESHOLD:
            tier = "junk"
            reasons.append(f"看过不给(CBI {cbi:.2f})")

    title = v.get("title") or ""
    if view >= CBI_MIN_VIEW:
        if cbi is not None and cbi < CBI_THRESHOLD:
            pass
        elif not whitelisted and tier in HIDE_TIERS:
            reasons.append(f"低分({tier})")
    elif not whitelisted and tier in HIDE_TIERS:
        reasons.append(f"低分({tier})")

    if matches_any(title, BEGGAR_PATTERNS):
        beggar = True
        reasons.append("乞讨标")

    hide = any(not r.startswith("乞讨标") for r in reasons)
    return hide, reasons, cbi, beggar, tier, f7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(ROOT, "data", "samples", "ecosystem_v5_20260901_2050_fix.json"))
    args = ap.parse_args()
    with open(args.data, encoding="utf-8") as f:
        payload = json.load(f)
    videos = payload["videos"]

    by_layer = defaultdict(lambda: {"n": 0, "cut": 0, "cut_view": 0, "all_view": 0, "reasons": defaultdict(int), "cbi_low": 0, "tier_low": 0, "portrait": 0, "short": 0, "sign": 0, "minview": 0, "beggar": 0, "whitelist": 0})
    cut_examples, gem_kept = defaultdict(list), []
    for v in videos:
        src = (v.get("source") or "?").split(":")[0]
        d = by_layer[src]
        d["n"] += 1
        view = v["stat"].get("view") or 0
        d["all_view"] += view
        # 同步层（feed 场景 item 无 duration 的按 0 处理；样本有 duration）
        dur = v.get("duration") or 0
        if dur and dur <= SHORT_MAX:
            d["cut"] += 1; d["short"] += 1; d["cut_view"] += view; d["reasons"]["短视频"] += 1
            if len(cut_examples["短视频"]) < 5:
                cut_examples["短视频"].append((view, v.get("title", "")[:28]))
            continue
        if matches_any(v.get("title") or "", BLOCK_KEYWORDS):
            d["cut"] += 1; d["sign"] += 1; d["cut_view"] += view; d["reasons"]["签名"] += 1
            if len(cut_examples["签名"]) < 5:
                cut_examples["签名"].append((view, v.get("title", "")[:28]))
            continue
        hide, reasons, cbi, beggar, tier, f7 = verdict(v)
        if beggar:
            d["beggar"] += 1
        if hide:
            d["cut"] += 1
            d["cut_view"] += view
            key = reasons[0].split("(")[0]
            d["reasons"][key] += 1
            if key == "看过不给":
                d["cbi_low"] += 1
            elif key == "低分":
                d["tier_low"] += 1
            elif key == "竖屏":
                d["portrait"] += 1
            elif key == "低播放":
                d["minview"] += 1
            if len(cut_examples[key]) < 5:
                cut_examples[key].append((view, (v.get("title") or "")[:28]))
        else:
            if cbi is not None and cbi >= 2.0 and view >= CBI_MIN_VIEW:
                gem_kept.append((view, f7, cbi, (v.get("title") or "")[:30]))

    print(f"{'层':<10}{'n':>6}{'砍':>6}{'砍%':>7}{'播放份额%':>9}  原因分布")
    for src, d in sorted(by_layer.items(), key=lambda x: -x[1]["n"]):
        share = d["cut_view"] / d["all_view"] * 100 if d["all_view"] else 0
        rd = " ".join(f"{k}:{v_}" for k, v_ in sorted(d["reasons"].items(), key=lambda x: -x[1]))
        print(f"{src:<10}{d['n']:>6}{d['cut']:>6}{d['cut']/d['n']*100:>6.1f}%{share:>8.1f}%  {rd}")

    print("\n=== 各原因样例 ===")
    for key, exs in cut_examples.items():
        print(f"[{key}]")
        for vw, t in exs[:4]:
            print(f"   {vw:>10,} {t}")
    print(f"\n=== CBI≥2 的健康大热门被保留 {len(gem_kept)} 条，样例 ===")
    gem_kept.sort(key=lambda x: -x[2])
    for vw, f7, cbi, t in gem_kept[:5]:
        print(f"   CBI {cbi:.2f} F7 {f7:.3f} {vw:>10,} {t}")


if __name__ == "__main__":
    main()
