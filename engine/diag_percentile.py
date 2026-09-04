# -*- coding: utf-8 -*-
"""同播放量带内百分位 vs CBI 的档位分离力对决（Elabation 同层横比假说验证）

参照人口：全部原始档案 + 首页样本（view≥3000，~7600 条）
检验：Elabation 95 条人判四档，分别用 (a) CBI (b) 带内投币率百分位 (c) 带内收藏率百分位
做 神作vs垃圾 / 神作vs吃灰 的 MWU——百分位若胜出，同层横比机制成立。零请求。
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cbi_scale import tier_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
BAND = 0.2  # log10(view) 带宽


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
    return round(z, 3), 0.5 * math.erfc(z / 2 ** 0.5)


def main():
    # ── 参照人口：全部原始档案 + 首页样本 ──
    pop = {}
    M = os.path.join(MINE)
    for fn in os.listdir(M):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(M, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                if (v.get("view") or 0) >= 3000 and v.get("bvid"):
                    st = v.get("stat") or {}
                    view = max(1, v.get("view") or 1)
                    pop[v["bvid"]] = {"view": view,
                                      "coin": st.get("coin", 0) / view,
                                      "fav": st.get("favorite", 0) / view,
                                      "like": st.get("like", 0) / view}
    hs = json.load(open(os.path.join(SDIR, "sample_20260903_185231.json"), encoding="utf-8"))
    for v in (hs.get("videos") or []):
        st = v.get("stat") or {}
        view = st.get("view") or 0  # collect_stats 样本：view 在 stat 里层
        if view >= 3000 and v.get("bvid"):
            pop.setdefault(v["bvid"], {"view": view,
                                       "coin": st.get("coin", 0) / view,
                                       "fav": st.get("favorite", 0) / view,
                                       "like": st.get("like", 0) / view})
    print(f"[pop] 参照人口 {len(pop)} 条（原始档案 + 首页样本）")

    # ── 分带：log10(view) 带 → 带内投币率/收藏率百分位 ──
    bands = defaultdict(lambda: {"coin": [], "fav": [], "bvid": []})
    for b, r in pop.items():
        k = round(math.log10(r["view"]) / BAND)
        bands[k]["coin"].append((r["coin"], b))
        bands[k]["fav"].append((r["fav"], b))
    pct = {}  # bvid -> (coin_pct, fav_pct)
    for k, d in bands.items():
        d["coin"].sort()
        d["fav"].sort()
        nc, nf = len(d["coin"]), len(d["fav"])
        for i, (cv, b) in enumerate(d["coin"]):
            pct.setdefault(b, [None, None])[0] = i / max(1, nc - 1)
        for i, (fv, b) in enumerate(d["fav"]):
            pct.setdefault(b, [None, None])[1] = i / max(1, nf - 1)
    print(f"[pop] log带数 {len(bands)}（带宽 {BAND} dex）")

    # ── 95 条标注：查表 ──
    labels = json.load(open(os.path.join(MINE, "elabation_flow_labels.json"), encoding="utf-8"))["labels"]
    NEG = ("不可能神作", "神作还有待考虑", "够不到神作", "门槛要更高", "不可能是神作", "很难神")

    def group(v):
        if any(k in v for k in ("低创", "垃圾", "狗屎", "擦边", "恶心", "自慰", "引流")):
            return "垃圾/低创/擦边"
        if ("神作" in v) and not any(k in v for k in NEG):
            return "神作"
        if any(k in v for k in ("吃灰", "教学", "教程", "实用", "跟练")):
            return "实用吃灰类"
        if any(k in v for k in ("优秀", "值得", "高质", "精良")):
            return "优秀"
        return "不典型/存疑"

    graded = []
    for j in labels:
        r = pop.get(j["bvid"])
        if not r or j["bvid"] not in pct:
            continue
        cbi_p = None  # CBI 的带内百分位（同样算，公平对比）
        graded.append({"group": group(j["verdict"]), "bvid": j["bvid"], "cbi": j["cbi"],
                       "coin_pct": pct[j["bvid"]][0], "fav_pct": pct[j["bvid"]][1]})
    print(f"[lab] 入表标注 {len(graded)}/{len(labels)}")

    tiers = ("神作", "优秀", "实用吃灰类", "垃圾/低创/擦边")
    cols = {"CBI": lambda g: g["cbi"], "投币百分位": lambda g: g["coin_pct"], "收藏百分位": lambda g: g["fav_pct"]}
    print("\n=== 各档中位对照（三特征）===")
    print(f"{'档':<14}{'n':>4}{'CBI中位':>9}{'投币百分位':>10}{'收藏百分位':>10}")
    med = {}
    for t in tiers:
        gs = [g for g in graded if g["group"] == t]
        if not gs:
            continue
        med[t] = {c: sorted(f(g) for g in gs)[len(gs) // 2] for c, f in cols.items()}
        print(f"{t:<14}{len(gs):>4}{med[t]['CBI']:>9.2f}{med[t]['投币百分位']:>10.2f}{med[t]['收藏百分位']:>10.2f}")

    print("\n=== 分离力对决：MWU p 值（越小越能分）===")
    print(f"{'对比':<22}{'CBI p':>10}{'投币百分位 p':>12}{'收藏百分位 p':>12}")
    for a, b in (("神作", "垃圾/低创/擦边"), ("神作", "实用吃灰类"), ("神作", "优秀"), ("优秀", "垃圾/低创/擦边")):
        ga = [g for g in graded if g["group"] == a]
        gb = [g for g in graded if g["group"] == b]
        if not ga or not gb:
            continue
        line = f"{a} vs {b:<10}"
        for cname, f in cols.items():
            _, p = mwu_u([f(g) for g in ga], [f(g) for g in gb])
            line += f"{p if p is not None else float('nan'):>12.4f}"
        print(line)

    out = {"n_pop": len(pop), "n_bands": len(bands), "n_graded": len(graded),
           "medians": med}
    json.dump(out, open(os.path.join(MINE, "percentile_validation.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n[done] -> percentile_validation.json")


if __name__ == "__main__":
    main()
