# -*- coding: utf-8 -*-
"""参照库盘点——带内投币百分位的参照人口全貌（零请求）。

输出：总量 / 域拆分 / 文件来源 / 视角带分布表（每带 n、币率中位、p10/p90）/ 薄带预警 / 去重损耗。
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
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
BAND = 0.2

pop = {}
src_file = defaultdict(int)      # bvid -> 首个来源文件（统计用）
domain = defaultdict(int)
raw_total = 0                    # 过滤前条数
dupe = 0

# 首页域
for fn in ("sample_20260903_185231.json", "sample_20260903_203054.json"):
    try:
        p = json.load(open(os.path.join(SDIR, fn), encoding="utf-8"))
    except Exception:
        continue
    for v in (p.get("videos") or []):
        raw_total += 1
        st = v.get("stat") or {}
        view = st.get("view") or 0
        if view < 3000 or not v.get("bvid"):
            continue
        b = v["bvid"]
        if b in pop:
            dupe += 1
            continue
        pop[b] = {"view": view, "coin": (st.get("coin") or 0) / view, "src": "home"}
        domain["home"] += 1
        src_file[fn] += 1

# 挖矿域（原始 favmine_*.json，排除 analysis/merged）
for fn in sorted(os.listdir(MINE)):
    if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
        try:
            p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
        except Exception:
            continue
        n_in = 0
        for v in (p.get("videos") or []):
            raw_total += 1
            if (v.get("view") or 0) >= 3000 and v.get("bvid"):
                st = v.get("stat") or {}
                view = max(1, v.get("view") or 1)
                b = v["bvid"]
                if b in pop:
                    dupe += 1
                    continue
                pop[b] = {"view": view, "coin": (st.get("coin") or 0) / view, "src": "mine"}
                domain["mine"] += 1
                n_in += 1
        src_file[fn] += n_in

# 视角带分布
bands = defaultdict(list)
for r in pop.values():
    bands[round(math.log10(r["view"]) / BAND)].append(r["coin"])

print(f"参照人口合计: {len(pop)} 条（首页域 {domain['home']} + 挖矿域 {domain['mine']}，跨文件去重 {dupe} 条）")
print(f"过滤口径: view>=3000；过滤前读入 {raw_total} 行")
views = [r["view"] for r in pop.values()]
print(f"播放量跨度: {min(views):,} ~ {max(views):,}\n")
print(f"{'带 k':>4} {'播放量级':>16} {'n':>6} {'占比':>7} {'币率中位':>9} {'p10':>7} {'p90':>7} {'薄带':>4}")
ks = sorted(bands)
for k in ks:
    arr = sorted(bands[k])
    n = len(arr)
    lo, hi = 10 ** (k * BAND), 10 ** ((k + 1) * BAND)
    med = arr[n // 2]
    p10 = arr[int(n * 0.10)]
    p90 = arr[int(n * 0.90)]
    thin = "⚠" if n < 50 else ""
    print(f"{k:>4} {f'10^{k*BAND:.1f}~10^{(k+1)*BAND:.1f}':>16} {n:>6} {n/len(pop):>6.1%} {med:>9.4%} {p10:>7.4%} {p90:>7.4%} {thin:>4}")
big = sum(1 for k in ks if len(bands[k]) >= 50)
print(f"\n带数: {len(ks)}（n>=50 的实心带 {big}，薄带 {len(ks)-big}）")
print("\n来源文件拆分（入队在先者计）:")
for fn, c in sorted(src_file.items(), key=lambda x: -x[1]):
    print(f"   {c:>5}  {fn}")
