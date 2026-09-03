# -*- coding: utf-8 -*-
"""诚意比（coin/fav）分布检验——颜值档案假说的定量武器。

假说：真神作 = 收藏（想留）+ 投币（真谢）双高，coin/fav 比显著 > 0；
颜值/擦边档案 = 收藏爆表 + 投币归零，coin/fav ≈ 0.01-0.05。
输出：全体神作的 coin/fav 分布 + 擦边 9 条 + 指定单视频的位置。零请求。
"""
import json
import os
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cbi_scale import tier_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
TARGET = "BV1cBtc65EQc"
ZONE_KW = ["舞蹈", "宅舞", "时尚", "美妆", "颜值"]
TITLE_KW = ["美女", "小姐姐", "擦边", "颜值", "热舞", "宅舞", "跳舞", "黑丝",
            "JK", "jk", "制服", "性感", "变装", "女团", "cos", "Cos", "COS", "纯欲",
            "身材", "御姐", "妹子", "舞蹈", "舞翻", "卡点舞"]


def main():
    god = {}
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                if (v.get("view") or 0) >= 3000 and tier_of(v.get("cbi", 0), v.get("view") or 0) == "high":
                    god[v["bvid"]] = v
    rows = []
    for b, v in god.items():
        st = v.get("stat") or {}
        fav = st.get("favorite", 0) or 0
        coin = st.get("coin", 0) or 0
        if fav <= 0:
            continue
        t = (v.get("title") or "")
        edge = any(k in t for k in TITLE_KW)
        rows.append({"bvid": b, "ratio": coin / max(1, fav), "fav": fav, "coin": coin,
                     "cbi": v.get("cbi"), "edge": edge, "title": t[:28]})
    rows.sort(key=lambda r: r["ratio"])
    n = len(rows)
    qs = {f"p{q}": rows[int(n * q / 100)]["ratio"] for q in (5, 10, 25, 50, 75, 90, 95)}
    edge_rows = [r for r in rows if r["edge"]]
    out = {"n_gods": n, "quantiles": {k: round(v, 3) for k, v in qs.items()},
           "edge_n": len(edge_rows),
           "edge_ratios": sorted(round(r["ratio"], 3) for r in edge_rows),
           "edge_median": round(sorted(r["ratio"] for r in edge_rows)[len(edge_rows) // 2], 3) if edge_rows else None}
    print(f"神作总数（去重）: {n}")
    print(f"coin/fav 分位: {out['quantiles']}")
    lo = sum(1 for r in rows if r["ratio"] < 0.05)
    print(f"诚意比 <0.05 的神作: {lo} 个（{lo/n:.1%}）")
    print(f"擦边标记神作 {len(edge_rows)} 条的诚意比: {out['edge_ratios']}（中位 {out['edge_median']}）")
    tgt = [r for r in rows if r["bvid"] == TARGET]
    if tgt:
        t = tgt[0]
        rank = sum(1 for r in rows if r["ratio"] < t["ratio"]) + 1
        print(f"目标 {TARGET}: 诚意比 {t['ratio']:.3f}（fav {t['fav']:,} / coin {t['coin']}）"
              f" → 全体神作中排第 {rank} 低 / {n}（百分位 {rank/n:.1%}）")
    json.dump(out, open(os.path.join(MINE, "sincerity_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("[done] -> sincerity_summary.json")


if __name__ == "__main__":
    main()
