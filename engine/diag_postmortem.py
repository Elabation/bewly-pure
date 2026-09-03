# -*- coding: utf-8 -*-
"""两项验尸（2026-09-03）：① 工程链探针 41.9% 的样本量与置信度；② flowmap 只见 4 用户之谜。"""
import json
import os
import sys
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fav_mine")


def load(fn):
    return json.load(open(os.path.join(MINE, fn), encoding="utf-8"))


def main():
    # ── ① 工程链探针样本量 ──
    eng = load("flow_h2_summary.json")
    pr = eng.get("probe") or {}
    print("=== 工程链探针体检 ===")
    print(f"probe 用户数={pr.get('n_probe_users')} 合格视频={pr.get('n_qual_probe')} "
          f"探针率={pr.get('probe_rate')} 剪枝增益={pr.get('prune_gain')}")
    # 探针组的二项 95% CI（Wald）
    n = pr.get("n_qual_probe") or 0
    p = pr.get("probe_rate") or 0
    if n:
        import math
        se = math.sqrt(p * (1 - p) / n)
        print(f"探针率 95%CI ≈ [{max(0, p-1.96*se):.3f}, {min(1, p+1.96*se):.3f}]（n={n}，Wald）")
        print(f"主链（剪枝组）0.239 是否在 CI 内: {0.239 >= max(0, p-1.96*se) and 0.239 <= min(1, p+1.96*se)}")

    # ── ② flowmap 之谜 ──
    print("\n=== flowmap 验尸（hop4）===")
    fm4 = load(".flowmap.json").get("hop4") or {}
    h4 = load("favmine_flowH4_20260903_115415.json")
    ledger = {u["user_hash"] for u in h4.get("users") or []}
    vals = Counter()
    for bv, us in fm4.items():
        for u in (us or []):
            vals[u] += 1
    fm_union = set(vals)
    print(f"ledger 唯一用户={len(ledger)} | flowmap union={len(fm_union)} | 交集={len(fm_union & ledger)}")
    print(f"per-seed 名单长度: {sorted((len(us or []) for us in fm4.values()))}")
    print(f"用户→出现的种子数: {dict(vals)}")
    m2h = load(".mid2hash.json")
    rev = {}
    for k, v in m2h.items():
        rev[v] = k
    for u in list(fm_union)[:6]:
        mid = rev.get(u, "?")
        print(f"  {u} → mid={mid[:7]}… 在ledger? {u in ledger}")


if __name__ == "__main__":
    main()
