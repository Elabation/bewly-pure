# -*- coding: utf-8 -*-
"""相关推荐探针——匿名通道测试 archive/related 接口（零主账号风险）。

对指定 bvid：fetch_view 拿 aid → related 列表 → 报告条数/字段完整度，
并演示「邻域内币率百分位」vs 全库带内百分位的对照。
用法: python engine/diag_related_probe.py BV1xx [BV2 ...]
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
from collect_stats import BiliClient  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
BAND = 0.2


def band_coin_pct(view, coin_rate):
    """全库带内币率百分位（零请求）。"""
    arr = []
    for fn in ("sample_20260903_185231.json", "sample_20260903_203054.json"):
        try:
            p = json.load(open(os.path.join(SDIR, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            st = v.get("stat") or {}
            vw = st.get("view") or 0
            if vw >= 3000 and round(math.log10(vw) / BAND) == round(math.log10(view) / BAND):
                arr.append((st.get("coin") or 0) / vw)
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                vw = v.get("view") or 0
                if vw >= 3000 and round(math.log10(vw) / BAND) == round(math.log10(view) / BAND):
                    st = v.get("stat") or {}
                    arr.append((st.get("coin") or 0) / max(1, vw))
    arr.sort()
    return sum(1 for a in arr if a < coin_rate) / max(1, len(arr) - 1), len(arr)


def main():
    cli = BiliClient(interval=0.8)
    targets = sys.argv[1:] or ["BV1Zx7B6DE6w", "BV1cBtc65EQc"]
    for bv in targets:
        print(f"\n===== {bv} =====")
        try:
            v = cli.fetch_view(bv)
        except Exception as e:
            print(f"[fail] fetch_view: {e}")
            continue
        aid = v.get("aid") or (v.get("stat") or {}).get("aid") or v.get("id")
        view = (v.get("stat") or {}).get("view") or 0
        coin = (v.get("stat") or {}).get("coin") or 0
        print(f"[self] 《{v.get('title','')[:36]}》aid={aid} view={view:,}")
        rel = []
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/archive/related",
                             {"aid": aid, "related": "true"}, tries=1)
            rel = d if isinstance(d, list) else []
            print(f"[related] 匿名 OK：{len(rel)} 条相关推荐")
        except Exception as e:
            print(f"[related] aid 参数失败: {e}，试 bvid 参数…")
            try:
                d = cli.get_json("https://api.bilibili.com/x/web-interface/archive/related",
                                 {"bvid": bv}, tries=1)
                rel = d if isinstance(d, list) else []
                print(f"[related] bvid 参数 OK：{len(rel)} 条")
            except Exception as e2:
                print(f"[related] 两种参数均失败: {e2}")
                continue
        if not rel:
            continue
        rows = []
        for r in rel:
            st = r.get("stat") or {}
            rv = st.get("view") or 0
            if rv < 1000:
                continue
            rows.append({"bvid": r.get("bvid"), "title": (r.get("title") or "")[:30],
                         "view": rv, "coin_rate": (st.get("coin") or 0) / rv,
                         "fav_rate": (st.get("favorite") or 0) / rv,
                         "like_rate": (st.get("like") or 0) / rv,
                         "dur": r.get("duration") or 0})
        print(f"[related] 有效样本（view>=1000）: {len(rows)}")
        views = sorted(r["view"] for r in rows)
        print(f"[related] 邻域播放量: {views[0]:,} ~ {views[-1]:,}（中位 {views[len(views)//2]:,}）")
        # 邻域内币率百分位
        self_rate = coin / max(1, view)
        nb = sorted(r["coin_rate"] for r in rows)
        nb_pct = sum(1 for a in nb if a < self_rate) / max(1, len(nb) - 1)
        g_pct, g_n = band_coin_pct(view, self_rate)
        print(f"[duel] 本片币率 {self_rate:.3%} ｜ 邻域百分位 {nb_pct:.3f}（n={len(nb)}） ｜ 全库带内 {g_pct:.3f}（n={g_n}）")
        print(f"[top5] 邻域币率最高 5 条:")
        for r in sorted(rows, key=lambda x: -x["coin_rate"])[:5]:
            print(f"   币率 {r['coin_rate']:.3%} · {r['view']:,}播放 · {r['dur']}s · {r['title']}")
        out = os.path.join(MINE, f"related_{bv}.json")
        json.dump({"target": bv, "aid": aid, "n_related": len(rel), "rows": rows},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[done] -> {out}")


if __name__ == "__main__":
    main()
