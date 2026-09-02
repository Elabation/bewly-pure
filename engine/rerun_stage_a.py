# -*- coding: utf-8 -*-
"""重采管线 · 阶段 A：臂②(uploader 基线) → 臂①(flow_high) → 臂③(comment_low) → E1 判定

全部教训内化：
  - 种子→用户映射随挖掘落盘（.flowmap.json / seed_type 字段）
  - tier 现算（cbi_scale 单一定义源）
  - fail-fast：任一步非零退出立即终止，不产出残缺数据
  - 账号存活前置检查 + 每轮之间复核
  - 混合模式（主号仅评论区请求）
"""
import json
import os
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENG = os.path.join(ROOT, "engine")
PY = sys.executable


def run(cmd, desc):
    print(f"\n=== [{time.strftime('%H:%M:%S')}] {desc} ===", flush=True)
    r = subprocess.run([PY] + cmd, cwd=ROOT)
    if r.returncode != 0:
        print(f"[ABORT] {desc} 退出码 {r.returncode} —— fail-fast 终止", flush=True)
        sys.exit(1)


def account_alive():
    """轻量登录态检查（1 请求；独立脚本自解析路径，避开中文路径命令行编码坑）。"""
    r = subprocess.run([PY, os.path.join(ENG, "account_check.py")],
                       capture_output=True, text=True, cwd=ROOT)
    return "ALIVE" in (r.stdout or "")


def main():
    if not account_alive():
        print("[ABORT] 账号登录态失效——请重新扫码", flush=True)
        sys.exit(2)
    print("[auth] 账号存活 ✓", flush=True)

    base = ["--per-folder", "20", "--sample-ratio", "0.85", "--interval", "0.45"]

    # 臂②：uploader 基线（150 种子，全部 --users 主路，无评论区种子）
    run(["engine/fav_miner.py", "--users", "150", "--comment-seeds", "0"] + base,
        "臂② uploader 基线（150 种子）")
    if not account_alive():
        print("[ABORT] 臂②后账号失效", flush=True); sys.exit(2)

    # 臂①：神作评论区流引导（主号仅评论区 ~10-15 请求）
    run(["engine/fav_miner.py", "--users", "0", "--comment-seeds", "200", "--arm", "high"] + base,
        "臂① flow_high（200 评论种子）")
    if not account_alive():
        print("[ABORT] 臂①后账号失效", flush=True); sys.exit(2)

    # 臂③：普通视频评论区对照
    run(["engine/fav_miner.py", "--users", "0", "--comment-seeds", "200", "--arm", "low"] + base,
        "臂③ comment_low（200 评论种子）")
    if not account_alive():
        print("[ABORT] 臂③后账号失效", flush=True); sys.exit(2)

    # E1/E2 判定（自动发现臂文件）
    run(["engine/e1_homophily.py"], "E1/E2 三臂判定")

    # 摘要
    print("\n=== 阶段 A 完成 · 产出清单 ===", flush=True)
    for fn in sorted(os.listdir(os.path.join(ROOT, "data", "fav_mine"))):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            meta = json.load(open(os.path.join(ROOT, "data", "fav_mine", fn), encoding="utf-8")).get("meta") or {}
            print(f"  {fn}  arm={meta.get('arm')} users={meta.get('users')} videos={meta.get('videos')}", flush=True)
    print(f"[STAGE-A-DONE] {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)


if __name__ == "__main__":
    main()
