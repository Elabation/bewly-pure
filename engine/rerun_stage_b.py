# -*- coding: utf-8 -*-
"""重采管线 · 阶段 B：多跳流式挖掘（自适应跳数，Elabation 修订停流准则）

准则修订（2026-09-03，Elabation 指正）：剪枝不影响本轮神作率、只影响下一轮候选池——
跳间神作率可比的前提 = 每跳简单随机抽样候选（--draw random）+ 随机种子补足（--fill random）。
  hop 从 2 起步，每跳结束检查（用户级神作率，如实记载）：
    1. 跳间相对下滑 > 5%（ρ = 本跳/上跳 < 0.95）→ 信号传递失真，停
    2. 本跳 < 第一跳的 80% → 绝对底线击穿，停
    3. 种子池 < 10（自然枯竭）→ 停
    4. hop > 6 → 安全上限，停
  上涨更好。CBI 浓度剪枝为工程策略，单独用预算效率评估，不混入神作率叙事。
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
RHO_FLOOR = 0.95     # 跳间相对下滑 ≤ 5%
ABS_FLOOR = 0.80     # 不低于第一跳的 80%


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

    # 第一跳率：臂①产物自身全量挖掘的神作率（阶段 A analyze 输出或现场算）
    a1 = json.load(open(arm1, encoding="utf-8"))
    q1 = [v for v in a1.get("videos") or [] if (v.get("view") or 0) >= 3000]
    from cbi_scale import tier_of, SCALE
    hop1_rate = (sum(1 for v in q1 if tier_of(v.get("cbi", 0), v.get("view") or 0) == "high")
                 / max(1, len(q1)))
    print(f"[hop1] 第一跳神作率 = {hop1_rate:.3f}（绝对底线 {ABS_FLOOR*hop1_rate:.3f}）", flush=True)

    verdicts = []
    source, hop, prev_rate = arm1, 2, None
    while hop <= MAX_HOP:
        run(["engine/flow_mine.py", "--source", source, "--hop", str(hop),
             "--min-inflow", "2", "--top-cbi-fill", "18", "--fill", "random",
             "--draw", "random",
             "--max-gods", "18", "--max-users", "80", "--interval", "0.45"],
            f"第 {hop} 跳流式挖掘（随机抽样候选+随机补足——无偏统计链）")
        summ = json.load(open(os.path.join(MINE, f"flow_h{hop}_summary.json"), encoding="utf-8"))
        rate = summ["hop2_high_rate"]
        rho = (rate / prev_rate) if prev_rate else None
        n_seeds = len(summ.get("seeds") or [])
        stop, reason = False, ""
        if rho is not None and rho < RHO_FLOOR:
            stop, reason = True, f"跳间相对下滑 {100*(1-rho):.1f}% > 5%（信号传递失真）"
        elif rate < ABS_FLOOR * hop1_rate:
            stop, reason = True, (f"本跳 {rate:.3f} < 第一跳的 80%"
                                  f"（{ABS_FLOOR*hop1_rate:.3f}）——绝对底线击穿")
        elif n_seeds < MIN_SEEDS:
            stop, reason = True, f"种子池 {n_seeds} < {MIN_SEEDS}（自然枯竭）"
        verdicts.append({"hop": hop, "rate": rate, "rho": round(rho, 3) if rho else None,
                         "n_seeds": n_seeds, "stop": stop, "reason": reason,
                         "vs_hop1": round(rate / hop1_rate, 3),
                         "efficiency": (summ.get("alpha_cutoffs") or {}).get("0.5", {}).get("efficiency")})
        print(f"[verdict] hop{hop}: rate={rate:.3f} ρ={rho} seeds={n_seeds} "
              f"→ {'停: ' + reason if stop else '继续'}", flush=True)
        if stop:
            break
        source = latest(f"favmine_flowH{hop}_*.json")
        prev_rate = rate
        hop += 1

    out = {"hop1_rate": round(hop1_rate, 3), "protocol": "draw=random fill=random（无偏链）",
           "criteria": {"rho_floor": RHO_FLOOR, "abs_floor": ABS_FLOOR,
                        "min_seeds": MIN_SEEDS, "max_hop": MAX_HOP},
           "verdicts": verdicts, "final_hops": len(verdicts),
           "conclusion": f"统计链共流 {len(verdicts)} 跳（含第一跳共 {len(verdicts)+1} 层节点），"
                         f"终跳神作率 {verdicts[-1]['rate']:.3f}"}
    json.dump(out, open(os.path.join(MINE, "hop_verdict.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n=== 跳数裁定 ===\n{json.dumps(out, ensure_ascii=False, indent=2)}", flush=True)
    print("[STAGE-B-DONE]", flush=True)


if __name__ == "__main__":
    main()
