# -*- coding: utf-8 -*-
"""V1 人工核对清单生成器（2026-09-03 新库版）——读本轮 ag_depth_summary 的 AG 独捞样例，
生成 docs/v1-checklist.md：每条含 BV 链接/标题/年代/AG/CBI/方向 + 三档判定填空。
人工流程：逐条打开视频观看 → 在「我的判定」填 真神作/普通/垃圾 → 交回统计（对比旧轮 83%）。
注：engine/v1_verify.py 是旧轮的 agent 初判记录，本脚本只出清单不做判定。
用法： python engine/v1_checklist.py [--n 12]
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
OUT = os.path.join(ROOT, "docs", "v1-checklist.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    args = ap.parse_args()

    ag = json.load(open(os.path.join(MINE, "ag_depth_summary.json"), encoding="utf-8"))
    ex = (ag.get("v2") or {}).get("ag_only_examples") or []
    rows = ex[:args.n]
    if not rows:
        print("[v1] ag_depth_summary 无样例")
        sys.exit(1)

    lines = [
        "# V1 人工核对清单 —— AG 独捞样例（2026-09-03 重采版）",
        "",
        "> 目标：检验「AG 深度判据独捞的视频」里真货的比例（设计预期 ≥60%，旧轮 83%）。",
        "> 观看每条视频后，在「我的判定」填：真神作 / 普通 / 垃圾（可选备注：好在哪 / 差在哪）。",
        "",
        f"样例数：{len(rows)}（抽取自 ag_depth_summary.v2.ag_only_examples）",
        "",
    ]
    for i, s in enumerate(rows, 1):
        bv = s.get("bvid") or "?"
        title = (s.get("title") or "?").replace("|", "／")
        lines.append(f"## {i}. {title}")
        lines.append("")
        lines.append(f"- 链接：https://www.bilibili.com/video/{bv}")
        lines.append(f"- 年代：{s.get('year', '?')}　AG={s.get('ag', '?')}　CBI={s.get('cbi', '?')}　"
                     f"方向={s.get('u', '?')}")
        lines.append("- 我的判定：＿＿＿＿＿（真神作 / 普通 / 垃圾）")
        lines.append("- 备注：")
        lines.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[v1] {len(rows)} 条样例 -> {OUT}")


if __name__ == "__main__":
    main()
