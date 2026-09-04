# -*- coding: utf-8 -*-
"""每日维护管线——首页多挖 + 货架自动换新（Elabation 2026-09-04 指令）。

流程（约 300 请求 / 4 分钟，全部匿名）：
  1) 首页热门 10 页（popular pn=1..10，约 200 视频）
  2) 新面孔（不在池内）逐个 fetch_view（计数+pubdate+UP+封面）
  3) 落盘 data/fav_mine/favmine_daily_YYYYMMDD.json（raw immutable，god_pool 自动收编）
  4) 今日新神作取 top10 做 L1 related 扩挖 → data/flow_graph/godflowdaily_*.json
  5) 重建货架 build_site.py
日志：data/logs/daily_YYYYMMDD.log
"""
import json
import os
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402
from god_pool import build_pool  # noqa: E402
from v3_rules import v3_tier  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
FG = os.path.join(ROOT, "data", "flow_graph")
LOGD = os.path.join(ROOT, "data", "logs")
os.makedirs(LOGD, exist_ok=True)
DATE = time.strftime("%Y%m%d")
LOG = os.path.join(LOGD, f"daily_{DATE}.log")
POP_PAGES = 10
NEW_CAP = 300
SEEDS = 10


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    cli = BiliClient(interval=0.6)
    log("=== 每日维护开始 ===")
    # 0) 当前池基线
    pool, _ = build_pool()
    known = set(pool.keys())
    log(f"当前池 {len(pool)} 支")

    # 1) 首页热门 10 页
    bvids = []
    for pn in range(1, POP_PAGES + 1):
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/popular",
                             {"ps": 20, "pn": pn}, tries=1)
            for it in (d or {}).get("list") or []:
                b = it.get("bvid")
                if b:
                    bvids.append(b)
        except Exception as e:
            log(f"popular pn={pn} fail: {str(e)[:60]}")
    bvids = list(dict.fromkeys(bvids))
    log(f"首页热门去重 {len(bvids)} 支（{POP_PAGES} 页）")

    # 2) 新面孔 fetch_view
    new_recs = []
    for b in bvids:
        if b in known or len(new_recs) >= NEW_CAP:
            continue
        try:
            v = cli.fetch_view(b)
            st = v.get("stat") or {}
            if (st.get("view") or 0) >= 3000:
                new_recs.append({"bvid": b, "title": v.get("title") or "", "view": st.get("view") or 0,
                                 "duration": v.get("duration") or 0, "pubdate": v.get("pubdate"),
                                 "owner": v.get("owner") or "", "pic": v.get("pic") or "",
                                 "tname": v.get("tname") or "",
                                 "stat": {"coin": st.get("coin") or 0, "favorite": st.get("favorite") or 0,
                                          "like": st.get("like") or 0, "share": st.get("share") or 0,
                                          "reply": st.get("reply") or 0, "danmaku": st.get("danmaku") or 0}})
        except Exception:
            pass
    log(f"新面孔 {len(new_recs)} 支（view>=3000）")

    # 3) 落盘 raw（god_pool 自动收编；同日重跑覆盖当日文件）
    daily_path = os.path.join(MINE, f"favmine_daily_{DATE}.json")
    old = []
    if os.path.exists(daily_path):
        try:
            old = json.load(open(daily_path, encoding="utf-8")).get("videos") or []
        except Exception:
            old = []
    have = {x.get("bvid") for x in old}
    merged = old + [x for x in new_recs if x["bvid"] not in have]
    json.dump({"meta": {"date": DATE, "src": "homepage-daily", "n": len(merged)}, "videos": merged},
              open(daily_path, "w", encoding="utf-8"), ensure_ascii=False)
    log(f"落盘 {daily_path}（累计 {len(merged)}）")

    # 4) 重建池 → 今日新神作 top10 → L1 扩挖
    pool2, _ = build_pool()
    new_keys = [x["bvid"] for x in merged]
    todays_gods = sorted((pool2[b] for b in new_keys if b in pool2 and pool2[b]["tier"] == "神作候选"),
                         key=lambda r: -(r.get("pct") or 0))[:SEEDS]
    log(f"今日新神作 {len(todays_gods)} 支，L1 扩挖...")
    nodes, edges = [], []
    seen = set()
    for r in todays_gods:
        aid = None
        try:
            vv = cli.fetch_view(r["bvid"])
            aid = vv.get("aid") or (vv.get("stat") or {}).get("aid") or vv.get("id")
        except Exception:
            aid = None
        if not aid:
            log(f"seed {r['bvid']} 无 aid，跳过")
            continue
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/archive/related",
                             {"aid": aid, "related": "true"}, tries=1)
            items = d if isinstance(d, list) else []
        except Exception:
            items = []
        parent = r["bvid"]
        seen.add(parent)
        nodes.append({"bvid": r["bvid"], "title": r["title"], "view": r["view"], "dur": r["dur"],
                      "coin_rate": r["coin_rate"], "fav_rate": r["fav_rate"], "like_rate": r["like_rate"],
                      "tier": r["tier"], "category": r["category"], "hop": 0, "parent": None,
                      "pubdate": r.get("pubdate"), "arm": "daily", "flow_seed": r["bvid"], "seed": True})
        for it in items:
            cb = it.get("bvid")
            if not cb or cb in seen:
                continue
            seen.add(cb)
            cst = it.get("stat") or {}
            vr = max(1, cst.get("view") or 0)
            cr, fr, lr = (cst.get("coin") or 0) / vr, (cst.get("favorite") or 0) / vr, (cst.get("like") or 0) / vr
            edges.append({"src": parent, "dst": cb, "hop": 1})
            nodes.append({"bvid": cb, "title": (it.get("title") or "")[:60], "view": cst.get("view") or 0,
                          "dur": it.get("duration") or 0,
                          "coin_rate": round(cr, 5), "fav_rate": round(fr, 5), "like_rate": round(lr, 5),
                          "tier": None, "category": None, "hop": 1, "parent": parent,
                          "pubdate": it.get("pubdate"), "arm": "daily", "flow_seed": r["bvid"]})
    # 重新判档（node 级）
    import math as _m
    from god_pool import _load_pop, BAND as _B  # 复用基线
    pop = _load_pop()
    bands = defaultdict(list)
    for rr in pop.values():
        bands[round(_m.log10(rr["view"]) / 0.2)].append(rr["coin"] / max(1, rr["view"]))
    BANDS = {k: sorted(a) for k, a in bands.items()}
    for n in nodes:
        if n.get("tier") is not None:
            continue
        vw = max(1, n.get("view") or 0)
        cr = n.get("coin_rate") or 0
        arr = BANDS.get(round(_m.log10(vw) / 0.2)) if vw >= 3000 else None
        p = (sum(1 for a in arr if a < cr) / max(1, len(arr) - 1)) if arr else None
        fr, lr = n.get("fav_rate") or 0, n.get("like_rate") or 0
        t, _f = v3_tier(p, n.get("dur") or 0, fr, cr, lr, n.get("title"))
        n["tier"], n["coin_pct"] = t, (round(p, 4) if p is not None else None)
    ngods = sum(1 for n in nodes if n.get("tier") == "神作候选")
    flow_path = os.path.join(FG, f"godflowdaily_{time.strftime('%Y%m%d_%H%M%S')}.json")
    json.dump({"meta": {"date": DATE, "src": "daily-L1", "requests": {"related": len(todays_gods)}},
               "flows": [{"seed": {"bvid": todays_gods[0]["bvid"], "title": todays_gods[0]["title"], "bucket": "daily"} if todays_gods else {},
                          "nodes": nodes, "edges": edges, "n_god_total": ngods}]},
              open(flow_path, "w", encoding="utf-8"), ensure_ascii=False)
    log(f"L1 扩挖落盘：{len(nodes)} 节点 / {ngods} 神（godflowdaily）")

    # 5) 重建货架
    res = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_site.py")],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    log("货架重建: " + (res.stdout or "").strip().splitlines()[-1] if (res.stdout or "").strip() else "货架重建: 无输出")
    if res.returncode != 0:
        log(f"货架重建失败: {(res.stderr or '')[:200]}")
    log("=== 每日维护完成 ===")


if __name__ == "__main__":
    from collections import defaultdict
    main()
