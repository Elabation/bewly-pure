# -*- coding: utf-8 -*-
"""重采管线 · 阶段 C：统计深挖 → 动画 v3 → 报告填充 → GitHub 推送

前置：阶段 A（三臂+E1 判定）与阶段 B（多跳+裁定表）已完成。
全部步骤 fail-fast；推送含数据档案（匿名后）+ summary + 报告。
"""
import os
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
PY = sys.executable


def run(cmd, desc):
    print(f"\n=== [{time.strftime('%H:%M:%S')}] {desc} ===", flush=True)
    r = subprocess.run([PY] + cmd, cwd=ROOT)
    if r.returncode != 0:
        print(f"[ABORT] {desc} 退出码 {r.returncode}", flush=True)
        sys.exit(1)


def main():
    run(["engine/fav_miner.py", "--analyze", "ALL"], "合并全库 + 分析（新口径）")
    run(["engine/ag_depth.py"], "AG-Depth 重算（新库）")
    run(["engine/ag_folium.py"], "AG-Folium 重算（新库）")
    run(["engine/deep_mining.py"], "统计深挖八件套")
    run(["engine/gen_flow_viz.py"], "《墨流》动画 v3（新数据）")
    run(["engine/build_report_v2.py"], "W7 报告填充")

    # 推送：代码 + 报告 + 动画 + 数据档案 + summary
    files = ["engine/collect_stats.py", "engine/fav_miner.py", "engine/flow_mine.py",
             "engine/cbi_scale.py", "engine/e1_homophily.py", "engine/deep_mining.py",
             "engine/build_report_v2.py", "engine/gen_flow_viz.py",
             "engine/ag_depth.py", "engine/ag_folium.py",
             "docs/appreciation-geometry.md", "docs/flow-viz.html", "docs/report-v2.html"]
    for fn in sorted(os.listdir(MINE)):
        if fn.endswith(".json") and ("favmine_" in fn or "_summary" in fn or "verdict" in fn):
            if "_trash" in fn:
                continue
            files.append(f"data/fav_mine/{fn}")
    print(f"[push] 共 {len(files)} 个文件", flush=True)
    run(["engine/push_repo.py"] + files, "GitHub 推送（断网保险）")
    print("[STAGE-C-DONE] 全链完成", flush=True)


if __name__ == "__main__":
    main()
