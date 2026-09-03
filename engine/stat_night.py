# -*- coding: utf-8 -*-
"""统计学家夜班 · 第二轮（2026-09-03 午后）——零请求纯本地。

N1 汇流质量梯度：入度≥2 的神作 vs 单收藏者神作的 CBI 对比
   ——首次实证 §4.6「汇流度即无监督置信度加权」
N2 层间冲积分析：臂①→hop2→hop3→hop4 各层新增视频占比（流的发现/重复比，W9 预算设计输入）
N3 擦边神作的收藏者分布：9 条 god 级候选的入度与收藏者数（个人子报告加菜：
   社区共验 vs 个人 quirks）
N4 汇流结构 top10：最被多源同指的视频（W9 宝藏候选雏形）
输出：data/fav_mine/stat_night_summary.json
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

RAW_FILES = {
    "arm1": "favmine_20260903_102226.json",
    "hop2": "favmine_flowH2_20260903_113231.json",
    "hop3": "favmine_flowH3_20260903_114437.json",
    "hop4": "favmine_flowH4_20260903_115415.json",
    "eng": "favmine_flowH2_20260903_120735.json",
}
ZONE_KW = ["舞蹈", "宅舞", "时尚", "美妆", "颜值"]
TITLE_KW = ["美女", "小姐姐", "擦边", "颜值", "热舞", "宅舞", "跳舞", "黑丝",
            "JK", "jk", "制服", "性感", "变装", "女团", "cos", "Cos", "COS", "纯欲",
            "身材", "御姐", "妹子", "舞蹈", "舞翻", "卡点舞"]


def load(fn):
    return json.load(open(os.path.join(MINE, fn), encoding="utf-8"))


def mwu_u(x, y):
    n1, n2 = len(x), len(y)
    if n1 < 5 or n2 < 5:
        return None, None
    allv = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks, i = [0.0] * len(allv), 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        avg = (i + j - 1) / 2 + 1
        for t in range(i, j):
            ranks[t] = avg
        i = j
    r1 = sum(r for r, (_, g) in zip(ranks, allv) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    sig = (n1 * n2 * (n1 + n2 + 1) / 12) ** 0.5
    z = (u1 - mu) / sig if sig else 0.0
    return round(z, 3), 0.5 * math_erfc(z / 2 ** 0.5)


def math_erfc(x):
    import math
    return math.erfc(x)


def main():
    payloads = {k: load(v) for k, v in RAW_FILES.items()}

    # 原始边集（跨全部档案）：bvid -> {collectors}, 及 bvid -> 记录（tier/cbi/title）
    edges = defaultdict(set)
    rec = {}
    for tag, p in payloads.items():
        for v in (p.get("videos") or []):
            if (v.get("view") or 0) >= 3000 and v.get("from_user") and v.get("bvid"):
                edges[v["bvid"]].add(v["from_user"])
                rec[v["bvid"]] = v

    # ── N1 汇流质量梯度 ──
    conf_god = [rec[b]["cbi"] for b, us in edges.items()
                if len(us) >= 2 and tier_of(rec[b].get("cbi", 0), rec[b].get("view") or 0) == "high"]
    single_god = [rec[b]["cbi"] for b, us in edges.items()
                  if len(us) == 1 and tier_of(rec[b].get("cbi", 0), rec[b].get("view") or 0) == "high"]
    z, p = mwu_u(conf_god, single_god)
    n1 = {"conf_n": len(conf_god), "conf_mean": round(sum(conf_god) / max(1, len(conf_god)), 3),
          "single_n": len(single_god), "single_mean": round(sum(single_god) / max(1, len(single_god)), 3),
          "mwu_z": z, "p_one": p}
    print(f"[N1] 汇流神作 CBI {n1['conf_mean']}（n={n1['conf_n']}） vs 单收藏神作 "
          f"{n1['single_mean']}（n={n1['single_n']}） z={z} p={p}")

    # ── N2 层间冲积 ──
    layers = {}
    order = ["arm1", "hop2", "hop3", "hop4"]
    seen = set()
    n2 = []
    for tag in order:
        bv = {v["bvid"] for v in (payloads[tag].get("videos") or []) if (v.get("view") or 0) >= 3000}
        new = bv - seen
        n2.append({"layer": tag, "total": len(bv), "new": len(new),
                   "novelty": round(len(new) / max(1, len(bv)), 3)})
        seen |= bv
        print(f"[N2] {tag}: 层内 {len(bv)} | 新增 {len(new)} | 新鲜率 {n2[-1]['novelty']:.1%}")
    # 累计池的层间复用（上一跳收获被下一跳回收的比例）
    for a, b in (("arm1", "hop2"), ("hop2", "hop3"), ("hop3", "hop4")):
        sa = {v["bvid"] for v in (payloads[a].get("videos") or []) if (v.get("view") or 0) >= 3000}
        sb = {v["bvid"] for v in (payloads[b].get("videos") or []) if (v.get("view") or 0) >= 3000}
        inter = sa & sb
        print(f"[N2] {a}∩{b}: {len(inter)} 条（{b} 层对 {a} 层收获的回收率 "
              f"{len(inter)/max(1,len(sb)):.1%}）")

    # ── N3 擦边神作的收藏者分布 ──
    cand_gods = []
    for b, v in rec.items():
        t = (v.get("title") or "")
        if any(k in t for k in TITLE_KW) and v.get("tier") == "high":
            cand_gods.append((b, v, len(edges.get(b, set()))))
    cand_gods.sort(key=lambda x: -(x[1].get("cbi") or 0))
    n3 = [{"bvid": b, "title": (v.get("title") or "")[:30], "cbi": v.get("cbi"),
           "inflow": k, "view": v.get("view")} for b, v, k in cand_gods]
    print(f"[N3] 擦边 god 级候选 {len(n3)} 条的收藏者数：{[(r['cbi'], r['inflow']) for r in n3]}")

    # ── N4 汇流 top10 ──
    top = sorted(((b, len(us)) for b, us in edges.items() if len(us) >= 2),
                 key=lambda x: -x[1])[:10]
    n4 = [{"bvid": b, "inflow": k, "tier": rec[b].get("tier"),
           "cbi": rec[b].get("cbi"), "title": (rec[b].get("title") or "")[:34]}
          for b, k in top if b in rec]
    print("[N4] 汇流 top10（W9 宝藏候选）：")
    for r in n4:
        print(f"    入度{r['inflow']} [{r['tier']}] CBI{r['cbi']} {r['title']}")

    out = {"N1_confluence_quality": n1, "N2_layer_alluvial": n2, "N3_edge_gods": n3, "N4_top_confluence": n4}
    json.dump(out, open(os.path.join(MINE, "stat_night_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("[done] -> data/fav_mine/stat_night_summary.json")


if __name__ == "__main__":
    main()
