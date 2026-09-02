# -*- coding: utf-8 -*-
"""重采管线 · 阶段 B：多跳流式挖掘（自适应跳数，按停流准则自动裁定）

停流准则（appreciation-geometry.md §4.5 定型）：
  hop 从 2 起步，每跳结束检查：
    1. 本跳神作率 < 1.3 × 基线（uploader 臂率）→ 增益耗尽，停
    2. 保留率 ρ = 本跳率/上跳率 < 0.5 → 信息过半流失，停
    3. 种子池 < 10（汇流神作数 + CBI 补足后）→ 自然枯竭，停
    4. hop > 6 → 安全上限，停
  否则继续下一跳（种子 = 上一跳产物汇流≥2 优先 + CBI top 补足）。
真剪枝：流强度 = 所评种子 CBI 浓度和（连续信号），挖掘时截断执行。
产出：favmine_flowH{n}_*.json 序列 + flow_h{n}_summary.json + 跳数裁定表 hop_verdict.json
"""
import glob
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
MINE = os.path.join(ROOT, "data", "fav_mine")
PY = sys.executable
MAX_HOP = 6
MIN_SEEDS = 10


def latest(pattern):
    fs = sorted(glob.glob(os.path.join(MINE, pattern)), key=os.path.getmtime)
    return fs[-1] if fs else None


def run(cmd, desc):
    print(f"\n=== [{time.strftime('%H:%M:%S')}] {desc} ===", flush=True)
    r = subprocess.run([PY] + cmd, cwd=ROOT)
    if r.returncode != 0:
        print(f"[ABORT] {desc} 退出码 {r.returncode}", flush=True)
        sys.exit(1)


def main():
    # 臂①最新产物（阶段 A 产出，按 meta.arm=high 识别）
    arm1 = None
    for fn in sorted(glob.glob(os.path.join(MINE, "favmine_*.json"))):
        if "_analysis" in fn or "merged" in fn or "flowH" in fn or "flowE3" in fn:
            continue
        try:
            if json.load(open(fn, encoding="utf-8")).get("meta", {}).get("arm") == "high":
                arm1 = fn
        except Exception:
            continue
    if not arm1:
        print("[ABORT] 未找到臂①产物（meta.arm=high）", flush=True)
        sys.exit(1)
    print(f"[hop2] 臂①源 = {os.path.basename(arm1)}", flush=True)

    # 基线（uploader 臂用户级神作率）——从 e1_homophily_summary.json 读，若无则现场算
    e1p = os.path.join(MINE, "e1_homophily_summary.json")
    base_rate = 0.06
    if os.path.exists(e1p):
        try:
            base_rate = json.load(open(e1p, encoding="utf-8"))["metrics"]["神作率"]["means"]["uploader"]
        except Exception:
            pass
    print(f"[base] uploader 基线神作率 = {base_rate:.3f}", flush=True)

    verdicts = []
    source, hop, prev_rate = arm1, 2, None
    while hop <= MAX_HOP:
        run(["engine/flow_mine.py", "--source", source, "--hop", str(hop),
             "--min-inflow", "2", "--top-cbi-fill", "20",
             "--max-gods", "18", "--max-users", "80", "--interval", "0.45"],
            f"第 {hop} 跳流式挖掘")
        summ = json.load(open(os.path.join(MINE, f"flow_h{hop}_summary.json"), encoding="utf-8"))
        rate = summ["hop2_high_rate"]
        rho = (rate / prev_rate) if prev_rate else None
        n_seeds = len(summ.get("seeds") or [])
        stop, reason = False, ""
        if rate < 1.3 * base_rate:
            stop, reason = True, f"边际神作率 {rate:.3f} < 1.3×基线 {1.3*base_rate:.3f}"
        elif rho is not None and rho < 0.5:
            stop, reason = True, f"保留率 ρ={rho:.2f} < 0.5（信息过半流失）"
        elif n_seeds < MIN_SEEDS:
            stop, reason = True, f"种子池 {n_seeds} < {MIN_SEEDS}（自然枯竭）"
        verdicts.append({"hop": hop, "rate": rate, "rho": round(rho, 3) if rho else None,
                         "n_seeds": n_seeds, "stop": stop, "reason": reason,
                         "efficiency": summ["alpha_cutoffs"]["0.5"]["efficiency"]})
        print(f"[verdict] hop{hop}: rate={rate:.3f} ρ={rho} seeds={n_seeds} "
              f"→ {'停: ' + reason if stop else '继续'}", flush=True)
        if stop:
            break
        # 下一跳源 = 本跳产物
        source = latest(f"favmine_flowH{hop}_*.json")
        prev_rate = rate
        hop += 1

    out = {"base_rate": base_rate, "verdicts": verdicts,
           "final_hops": len(verdicts),
           "conclusion": f"共流 {len(verdicts)} 跳（含第一跳共 {len(verdicts)+1} 层节点），"
                         f"终跳神作率 {verdicts[-1]['rate']:.3f}"}
    json.dump(out, open(os.path.join(MINE, "hop_verdict.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n=== 跳数裁定 ===\n{json.dumps(out, ensure_ascii=False, indent=2)}", flush=True)
    print("[STAGE-B-DONE]", flush=True)


if __name__ == "__main__":
    main()
