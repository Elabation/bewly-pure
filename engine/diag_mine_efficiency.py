# -*- coding: utf-8 -*-
"""挖矿效率审计（零请求）——为「大家都能用的推荐网页」确定最高效的神作挖掘方案。

口径：
  · 产量 = tier==神作候选 的已发现视频（含跨臂重复，另算去重边际）
  · 成本 = related 请求数（stats 随 related 自带，本地筛分免费）
  · 效率 = 神/请求；边际 = 该臂独有神 / 该臂请求
"""
import glob
import json
import os
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FG = r"D:\work_space\b站插件项目\bilibili-clean\data\flow_graph"


def latest(pattern):
    fs = sorted(glob.glob(os.path.join(FG, pattern)), key=lambda p: os.path.basename(p))
    return fs[-1] if fs else None


ARMS = []  # (key, name, requests, flows)
bp = latest("godflow_2*.json")
if bp:
    run = json.load(open(bp, encoding="utf-8"))
    rq = (run["meta"].get("requests") or {}).get("related", 110) / 2
    for key, name in (("target", "A定向"), ("random", "B随机")):
        ARMS.append((key, name, rq, run["arms"][key]["flows"]))
dp = latest("godflowdeep_*.json")
if dp:
    run = json.load(open(dp, encoding="utf-8"))
    ARMS.append(("deep", "C′纵深", (run["meta"].get("requests") or {}).get("related", 87), run["flows"]))
np_ = latest("godflowbnopad_*.json")
if np_:
    run = json.load(open(np_, encoding="utf-8"))
    ARMS.append(("bnopad", "D无补位", (run["meta"].get("requests") or {}).get("related", 110), run["flows"]))
rp = latest("godflowretro_*.json")
if rp:
    run = json.load(open(rp, encoding="utf-8"))
    ARMS.append(("retro", "E回溯", (run["meta"].get("requests") or {}).get("related", 187), run["flows"]))

arm_gods = {}
info = {}
for key, name, req, flows in ARMS:
    gods, nodes = {}, 0
    hop_gods, hop_reqs = defaultdict(int), defaultdict(int)
    for f in flows:
        for n in f["nodes"]:
            nodes += 1
            if n.get("tier") == "神作候选":
                gods[n["bvid"]] = n
        frontier = 1
        for h in f["hops"]:
            if "n_neighbors" not in h:
                continue
            hop_gods[h["hop"]] += h.get("n_gods", 0)
            hop_reqs[h["hop"]] += frontier
            frontier = max(1, len(h.get("selected") or []))
    arm_gods[key] = set(gods)
    pct_hi = sum(1 for g in gods.values() if (g.get("coin_pct") or 0) >= 0.98)
    cats = defaultdict(int)
    for g in gods.values():
        cats[g.get("category") or "其他"] += 1
    top_cats = sorted(cats.items(), key=lambda kv: -kv[1])[:4]
    info[key] = {"name": name, "req": req, "gods": len(gods), "nodes": nodes,
                 "gpr": len(gods) / req, "pct_hi": pct_hi,
                 "cats": top_cats, "hop_gods": dict(hop_gods), "hop_reqs": dict(hop_reqs),
                 "n_flows": len(flows)}

print("==== 一 · 各臂总效率 ====")
for key in ("target", "random", "deep", "bnopad", "retro"):
    d = info[key]
    uniq = len(arm_gods[key] - set().union(*(v for k, v in arm_gods.items() if k != key))) if len(ARMS) > 1 else len(arm_gods[key])
    print(f"{d['name']}: {d['gods']} 神 / {d['req']} 请求 = {d['gpr']:.2f} 神/请求 ｜ 独有 {uniq}（边际 {uniq/d['req']:.2f}）"
          f" ｜ pct≥0.98 高位神 {d['pct_hi']} ｜ 顶门类 {d['cats']}")

print("\n==== 二 · 跨臂重复度（同一视频被几臂发现） ====")
allg = defaultdict(set)
for key, gods in arm_gods.items():
    for b in gods:
        allg[b].add(key)
cnt = defaultdict(int)
for b, arms in allg.items():
    cnt[len(arms)] += 1
print(f"神作去重总数 {len(allg)}：" + " ｜ ".join(f"{k}臂共同发现 {v} 个" for k, v in sorted(cnt.items())))
union_req = sum(d["req"] for d in info.values())
print(f"五臂合计请求 {union_req:.0f}，去重神 {len(allg)}，综合效率 {len(allg)/union_req:.2f} 神/请求")

print("\n==== 三 · 逐跳衰减（神/请求 by hop） ====")
for key in ("target", "random", "deep", "bnopad", "retro"):
    d = info[key]
    parts = []
    for h in sorted(d["hop_gods"]):
        reqs = d["hop_reqs"].get(h, 0)
        if reqs:
            parts.append(f"L{h}:{d['hop_gods'][h]/reqs:.1f}")
    print(f"{d['name']}: " + "  ".join(parts))

print("\n==== 四 · 单流效率 TOP（ species 视角） ====")
flow_rows = []
for key, name, req, flows in ARMS:
    for f in flows:
        hops = [h for h in f["hops"] if "n_neighbors" in h]
        freq = len(hops) and sum(max(1, len((f['hops'][i-1].get('selected') or [])) if i > 0 else 1) for i, h in enumerate(f["hops"]) if "n_neighbors" in h)
        g = f["n_god_total"]
        if freq:
            flow_rows.append((g / freq, name, (f["seed"].get("bucket") or ""), (f["seed"].get("title") or "")[:14], g, freq))
flow_rows.sort(reverse=True)
for r in flow_rows[:8]:
    print(f"{r[0]:.1f} 神/req  {r[1]} · {r[2]} · {r[3]}  ({r[4]}神/{r[5]}req)")

out = {"arms": {k: {kk: vv for kk, vv in d.items() if kk not in ("hop_gods", "hop_reqs")} for k, d in info.items()},
       "dedup_gods": len(allg), "overlap_hist": dict(cnt), "union_req": union_req}
json.dump(out, open(os.path.join(FG.rsplit("flow_graph", 1)[0], "fav_mine", "mine_efficiency_summary.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n[done] -> mine_efficiency_summary.json")
