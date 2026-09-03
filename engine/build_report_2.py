# -*- coding: utf-8 -*-
"""调研报告 2.0 —— 一体化收官报告（porcelain-data 完全体，学 report-v2 原版美工）。

继承原版设计语言学：楷书章头 / Georgia 衬线数字 / 暖纸底 / 手绘 SVG 图表（自带读数段）/
guide 调用框 / formula 深蓝公式块 / ex 样例卡 / tag 显著性胶囊 / KPI 行 / CSS 条形行。
数据：本地全量聚合（参照库 26 带 / 95 标注中位表 / 双特例 / 五臂 godflow / 回溯链 / 主页收藏夹）。
输出：docs/report-2.0.html
"""
import glob
import json
import math
import os
import statistics
import sys
import time
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
FG = os.path.join(ROOT, "data", "flow_graph")
OUT = os.path.join(ROOT, "docs", "report-2.0.html")
BAND = 0.2


def load(fn):
    p = os.path.join(MINE, fn)
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return None
    return None


def latest(pattern):
    fs = sorted(glob.glob(os.path.join(FG, pattern)), key=lambda p: os.path.basename(p))
    return fs[-1] if fs else None


def build_bands():
    pop = {}
    for fn in ("sample_20260903_185231.json", "sample_20260903_203054.json"):
        try:
            p = json.load(open(os.path.join(SDIR, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            st = v.get("stat") or {}
            vw = st.get("view") or 0
            if vw >= 3000 and v.get("bvid"):
                pop.setdefault(v["bvid"], {"view": vw, "coin": (st.get("coin") or 0) / vw})
    n_home = len(pop)
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                vw = v.get("view") or 0
                if vw >= 3000 and v.get("bvid"):
                    st = v.get("stat") or {}
                    pop.setdefault(v["bvid"], {"view": vw, "coin": (st.get("coin") or 0) / max(1, vw)})
    bands = defaultdict(list)
    for r in pop.values():
        bands[round(math.log10(r["view"]) / BAND)].append(r["coin"])
    rows = []
    for k in sorted(bands):
        arr = sorted(bands[k])
        n = len(arr)
        rows.append({"k": k, "lo": round(10 ** (k * BAND), 1), "n": n,
                     "med": arr[n // 2], "p10": arr[int(n * .10)], "p90": arr[int(n * .90)],
                     "thin": n < 50})
    return rows, len(pop), n_home


def ym(t):
    if not t:
        return None
    return time.strftime("%Y-%m", time.localtime(t))


def build_arms():
    arms = []
    # A/B（breadth run）
    bp = latest("godflow_2*.json")
    if bp:
        run = json.load(open(bp, encoding="utf-8"))
        rq = run["meta"].get("requests") or {}
        for key, name in (("target", "A 定向"), ("random", "B 随机")):
            a = run["arms"].get(key) or {}
            flows = a.get("flows") or []
            arms.append({"key": key, "name": name, "rule": "前沿5 · 神优先+优秀补位" if key == "target" else "前沿5 · 随机",
                         "requests": round(rq.get("related", 110) / 2),
                         "gods": sum(f["n_god_total"] for f in flows),
                         "nodes": sum(len(f["nodes"]) for f in flows),
                         "alive": sum(1 for f in flows if f["status"] != "dry"),
                         "dry": sum(1 for f in flows if f["status"] == "dry"),
                         "dmax": max((len([h for h in f["hops"] if "n_neighbors" in h]) for f in flows), default=0),
                         "hops": [sum(h.get("n_gods", 0) for f in flows for h in f["hops"] if h.get("hop") == hh)
                                  for hh in (1, 2, 3, 4)]})
    # C'（deep 剪@0 = 最新 godflowdeep）
    dp = latest("godflowdeep_*.json")
    if dp:
        run = json.load(open(dp, encoding="utf-8"))
        flows = run.get("flows") or []
        arms.append({"key": "deep", "name": "C′ 纵深", "rule": "前沿2 神only · 神=0 剪 · 深度15",
                     "requests": (run["meta"].get("requests") or {}).get("related", 87),
                     "gods": sum(f["n_god_total"] for f in flows),
                     "nodes": sum(len(f["nodes"]) for f in flows),
                     "alive": sum(1 for f in flows if f["status"] == "censored_depth"),
                     "dry": sum(1 for f in flows if f["status"] == "pruned"),
                     "dmax": max((len([h for h in f["hops"] if "n_neighbors" in h]) for f in flows), default=0),
                     "hops": []})
    # D
    np_ = latest("godflowbnopad_*.json")
    if np_:
        run = json.load(open(np_, encoding="utf-8"))
        flows = run.get("flows") or []
        arms.append({"key": "bnopad", "name": "D 无补位", "rule": "前沿≤5 神only · 神<3 剪 · 深度8",
                     "requests": (run["meta"].get("requests") or {}).get("related", 110),
                     "gods": sum(f["n_god_total"] for f in flows),
                     "nodes": sum(len(f["nodes"]) for f in flows),
                     "alive": sum(1 for f in flows if f["status"] == "censored_depth"),
                     "dry": sum(1 for f in flows if f["status"] == "pruned"),
                     "dmax": max((len([h for h in f["hops"] if "n_neighbors" in h]) for f in flows), default=0),
                     "hops": [sum(h.get("n_gods", 0) for f in flows for h in f["hops"] if h.get("hop") == hh)
                              for hh in (1, 2, 3, 4)]})
    # E（retro）
    rp = latest("godflowretro_*.json")
    retro = None
    if rp:
        run = json.load(open(rp, encoding="utf-8"))
        flows = run.get("flows") or []
        arms.append({"key": "retro", "name": "E 回溯", "rule": "前沿2 · 最早优先 · 神=0 剪 · 深度25",
                     "requests": (run["meta"].get("requests") or {}).get("related", 187),
                     "gods": sum(f["n_god_total"] for f in flows),
                     "nodes": sum(len(f["nodes"]) for f in flows),
                     "alive": sum(1 for f in flows if f["status"] == "censored_depth"),
                     "dry": sum(1 for f in flows if f["status"] == "pruned"),
                     "dmax": max((len([h for h in f["hops"] if "n_neighbors" in h]) for f in flows), default=0),
                     "hops": []})
        # 回溯链：算每条漂移，取最负的三条（正主 = 回溯律成立的经典链）
        scored = []
        for f in flows:
            hops = [h for h in f["hops"] if "n_neighbors" in h]
            ds_all = [s.get("pubdate") for h in hops for s in (h.get("selected") or []) if s.get("pubdate")]
            if len(ds_all) < 4:
                continue
            drift = round((statistics.median(ds_all[-3:]) - statistics.median(ds_all[:3])) / 2592000)
            scored.append((drift, f, hops))
        picks = [f for d, f, hops in sorted(scored, key=lambda x: x[0])[:3]]
        chains = []
        for f in picks:
            hops = [h for h in f["hops"] if "n_neighbors" in h]
            pts = []
            for h in hops:
                sels = h.get("selected") or []
                ds = [s.get("pubdate") for s in sels if s.get("pubdate")]
                if ds:
                    pts.append({"hop": h["hop"], "t": statistics.median(ds)})
            ch = [c for h in hops for c in (h.get("selected") or []) if c.get("pubdate")]
            ds = [c["pubdate"] for c in ch]
            drift = round((statistics.median(ds[-3:]) - statistics.median(ds[:3])) / 2592000) if len(ds) >= 4 else None
            chains.append({"seed": (f["seed"]["bucket"] or "") + " · " + (f["seed"]["title"] or "")[:12],
                           "seed_bvid": f["seed"]["bvid"], "gods": f["n_god_total"],
                           "depth": len(hops), "status": f["status"], "drift": drift,
                           "span": [ym(min(ds)), ym(max(ds))] if ds else None,
                           "pts": pts})
        retro = {"chains": chains, "n_nodes": sum(len(f["nodes"]) for f in flows),
                 "n_gods": sum(f["n_god_total"] for f in flows),
                 "requests": (run["meta"].get("requests") or {}).get("related", 187),
                 "n_flows": len(flows)}
    return arms, retro


def build_data():
    bands, n_pop, n_home = build_bands()
    pv = load("percentile_validation.json") or {}
    sinc = load("sincerity_summary.json") or {}
    c1 = load("case_bv_report.json") or {}
    c2 = load("case_bv_report_BV1Zx7B6DE6w.json") or {}
    r2 = load("round2_labels.json") or {}
    r2rows = r2.get("rows") or []
    r2tiers = defaultdict(int)
    for r in r2rows:
        r2tiers[r.get("v3")] += 1
    arms, retro = build_arms()
    owner = load("fav_owner_snapshot_20260903_205917.json") or {}
    mo = load("mine_owner_3494381103352463.json") or {}
    tier_dist = defaultdict(int)
    for x in (mo.get("videos") or []):
        tier_dist[x.get("tier")] += 1
    return {
        "bands": bands,
        "pop": {"n": n_pop, "home": n_home, "mine": n_pop - n_home, "dupe": 400},
        "pv": pv,
        "sinc": {"q": sinc.get("quantiles") or {}, "n": sinc.get("n_gods")},
        "cases": [
            {"bv": "BV1cBtc65EQc", "title": c1.get("title", "男人把自己养好，就是最大的资本"), "up": c1.get("owner"),
             "dur": c1.get("dur"), "view": c1.get("view"), "fav": c1.get("fav"), "coin": c1.get("coin"),
             "like": c1.get("like"), "cbi": c1.get("cbi"), "p_coin": c1.get("p_coin"), "p_fav": c1.get("p_fav"),
             "sinc": c1.get("sincerity"), "v3": c1.get("v3_tier"), "rules": c1.get("v3_firings"),
             "likecoin": c1.get("like_coin_ratio"), "tags": c1.get("tags")},
            {"bv": "BV1Zx7B6DE6w", "title": c2.get("title", "哈基米上厕所拉力竭了"), "up": c2.get("owner"),
             "dur": c2.get("dur"), "view": c2.get("view"), "fav": c2.get("fav"), "coin": c2.get("coin"),
             "like": c2.get("like"), "cbi": c2.get("cbi"), "p_coin": c2.get("p_coin"), "p_fav": c2.get("p_fav"),
             "sinc": c2.get("sincerity"), "v3": c2.get("v3_tier"), "rules": c2.get("v3_firings"),
             "likecoin": c2.get("like_coin_ratio"), "tags": c2.get("tags")},
        ],
        "r2": {"n": len(r2rows), "tiers": dict(r2tiers), "filled": r2.get("n_filled")},
        "arms": arms,
        "retro": retro,
        "owner": {"folders": [{"t": f.get("title"), "n": f.get("media_count")} for f in (owner.get("folders") or [])],
                  "total": owner.get("total_media"),
                  "tiers": dict(tier_dist)},
        "meta": {"date": time.strftime("%Y-%m-%d")},
    }


DATA = build_data()

TPL = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>看过，却不给 · 第三季 —— 带内百分位与作品-推荐流 · 调研报告 2.0</title>
<style>
:root{--ink:#081F5C;--data1:#334EAC;--data2:#7096D1;--data3:#BAD6EB;--paper:#F7F2EB;--shadow:#E3DACB;--sub:#5B7EC2;--dim:#9FB6D4;--amber:#C2803A;--gold:#B8912F}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font:14px/1.9 -apple-system,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif}
.wrap{max-width:880px;margin:0 auto;padding:0 22px 80px}
header.hero{padding:76px 0 30px;border-bottom:1px solid var(--shadow)}
.kicker{font-size:11px;letter-spacing:4px;color:var(--data1);border:1px dashed var(--data2);display:inline-block;padding:4px 14px;border-radius:999px;margin-bottom:22px}
h1{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:42px;font-weight:900;letter-spacing:2px;line-height:1.3}
.hero .lede{font-size:15.5px;color:var(--sub);margin-top:14px;max-width:720px}
.badges{margin-top:22px;font-size:11.5px;color:var(--data1);letter-spacing:.5px}
.badges span{border:1px solid var(--data3);border-radius:4px;padding:2px 9px;margin-right:8px;display:inline-block;margin-bottom:6px;background:#fff8}
nav{position:sticky;top:0;background:var(--paper);border-bottom:1px solid var(--shadow);z-index:9;font-size:12px;padding:9px 0}
nav a{color:var(--sub);text-decoration:none;margin-right:12px}
nav a:hover{color:var(--ink)}
section{padding:50px 0 10px;border-bottom:1px solid var(--shadow)}
.sn{font-size:11px;letter-spacing:3px;color:var(--data2)}
h2{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:25px;margin:6px 0 10px}
h3{font-size:15px;color:var(--data1);margin:26px 0 8px}
p{margin:10px 0;max-width:790px}
p.note{font-size:12.5px;color:var(--sub)}
.guide{background:#EFE8DA;border-left:4px solid var(--data1);padding:12px 18px;margin:14px 0;font-size:13.5px;color:#22346B;max-width:790px}
.guide b{color:#081F5C}
.quote{border-left:3px solid var(--data1);padding:4px 16px;margin:16px 0;color:#22346B;font-size:13.5px;max-width:780px}
.formula{background:#0E2A6B;color:#EAF1FF;font-family:Consolas,Monaco,monospace;font-size:13px;padding:18px 22px;border-radius:6px;line-height:2.1;margin:16px 0;overflow-x:auto}
.formula .hl{color:#9CC7FF}
.kpirow{display:flex;gap:14px;flex-wrap:wrap;margin:16px 0}
.kpi{flex:1 1 170px;background:#EFE8DA;padding:14px 16px}
.kpi .n{font-family:Georgia,serif;font-size:26px;color:var(--ink)}
.kpi .d{font-size:11.5px;color:var(--sub);line-height:1.55;margin-top:2px}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:12.5px}
th{color:var(--data1);font-weight:600;border-bottom:2px solid var(--data2);padding:7px 8px;text-align:left;font-size:12px}
td{border-bottom:1px solid var(--shadow);padding:7px 8px;vertical-align:top}
td.num{font-family:Georgia,serif}
tr.win td{background:#334EAC0d}
tr.stop td{background:#C2803A14}
.tag{font-size:10px;border:1px solid var(--data2);color:var(--data1);border-radius:3px;padding:1px 6px;margin-left:6px;letter-spacing:1px;white-space:nowrap}
.tag.sig{background:#334EAC;color:#fff;border-color:#334EAC}
.tag.warn{border-color:#C2803A;color:#9A6428}
.tag.fail{background:#C2803A;color:#fff;border-color:#C2803A}
.tag.gold{background:#B8912F;color:#fff;border-color:#B8912F}
.chart-wrap{position:relative;margin:18px 0}
svg.chart{width:100%;height:auto;background:#fff6;border:1px solid var(--shadow)}
.legend{font-size:11.5px;color:var(--sub);margin-top:8px}
.legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 4px 0 12px}
.read{background:#EFE8DA;padding:12px 18px;margin:10px 0;font-size:13.5px;color:#22346B;max-width:790px}
.read b{color:#081F5C}
.exq{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}
.ex{flex:1 1 300px;border-left:3px solid var(--data2);background:#fff8;padding:9px 12px;font-size:12.5px}
.ex .t{color:var(--ink)}
.ex .m{font-family:Georgia,serif;color:var(--data1);font-size:12px;margin-top:2px}
.plates{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px 0}
.plate{background:#fff8;border:1px solid var(--shadow);padding:13px 15px}
.plate.dim{background:#f5efe4}
.plate .vh{font-size:11px;letter-spacing:2px;color:var(--data2);margin-bottom:6px}
.plate .vv{font-family:Georgia,serif;font-size:25px;color:var(--ink);line-height:1.25}
.plate .vt{font-size:12.5px;color:#334EAC;margin-top:4px}
.foot{padding:34px 0 10px;font-size:11.5px;color:var(--dim);letter-spacing:1px}
a{color:var(--data1)}
</style>
</head>
<body>
<div class="wrap">
<header class="hero">
  <div class="kicker">洁净B站 · 调研报告 2.0 · 一体化</div>
  <h1>看过，却不给<br>第三季 · 双轴与时光</h1>
  <div class="lede">收藏与投币本是两种语言。本季以 <b>带内投币百分位</b> 重写神作的度量衡，
  以 <b>作品-推荐流</b> 重写挖矿的路径，用五臂对照、10 个新种子与一条沉入 2014 年的回溯链，
  把「神作为什么神、神作在哪里」变成可检验的机制。</div>
  <div class="badges"><span>五臂对照 · 随机与纵深</span><span>95+76+48 人工标注</span><span>匿名通道 540+ 请求零故障</span><span>主账号零重请求</span><span>__DATE__ 定稿</span></div>
</header>
<nav>
  <a href="#s1">标尺革命</a><a href="#s2">v3 与三轮校验</a><a href="#s3">特例解剖</a><a href="#s4">参照库审计</a><a href="#s5">五臂对照</a><a href="#s6">时光回溯</a><a href="#s7">品味悖论</a><a href="#s8">诚实边界</a>
</nav>

<section id="s1">
  <div class="sn">一</div>
  <h2>标尺革命：CBI 之死与带内百分位立国</h2>
  <p>上一季的标尺是 F7 几何：收藏×3、投币×2、点赞×0.3，除以同播放段基线——CBI。它在 95 支人工
  标注的神作上受封。本季的第一件事，是把这把尺子放回解剖台。</p>
  <h3>95 支标注的判决：CBI 中位倒挂</h3>
  <table>
    <tr><th>人工档位</th><th>n=95 各档中位 CBI</th><th>中位 带内投币百分位</th><th>中位 收藏百分位</th></tr>
    <tr class="win"><td>神作</td><td class="num">9.00</td><td class="num"><b>0.960</b></td><td class="num">0.973</td></tr>
    <tr><td>优秀</td><td class="num">9.32</td><td class="num">0.894</td><td class="num">0.982</td></tr>
    <tr class="stop"><td>实用吃灰类</td><td class="num">10.49</td><td class="num">0.697</td><td class="num">0.994</td></tr>
    <tr class="stop"><td>垃圾/低创/擦边</td><td class="num">10.37</td><td class="num">0.686</td><td class="num">0.993</td></tr>
  </table>
  <div class="read"><b>读数</b>：CBI 无法排序——神作（9.00）低于吃灰类（10.49）与垃圾（10.37），收藏轴权重
  把「被存档的东西」整体顶高；而带内投币百分位 <b>0.960 &gt; 0.894 &gt; 0.697 &gt; 0.686</b>，严格单调，
  与人工档位完全同序。收藏是「想留」，投币是「真谢」——<b>双轴理论</b>由此从假说升级为度量衡。</div>
  <div class="guide"><b>定音锤（特例 BV1cBtc65EQc）</b>：养生话术《男人把自己养好，就是最大的资本》——
  CBI <b>3.17 判神</b>，带内币率百分位 <b>0.216 判垃圾候选</b>；诚意比 coin/fav = 0.013，低于全体 1,623 个
  CBI 神作的 p5（0.025）。CBI 的全部错误都来自一根 fav×3 引线。</div>
  <h3>新标尺</h3>
  <div class="formula">
    <span class="hl">coin_rate</span> = 投币 ÷ 播放<br>
    <span class="hl">pct</span>(v) = 带内（Δlog₁₀ = 0.2 的同播放量级）邻居中币率更低者的占比<br>
    v3 判档：pct ≥ <span class="hl">0.93</span> 神 · ≥ 0.85 优秀 · &lt; 0.72 垃圾；R2 时长 30s/90s ·
    R3 吃灰（藏/币&gt;8 且藏&gt;15%）· R4 擦边三连 · R8 赞/币&gt;50
  </div>
  <p class="note">为什么必须「带内」：26 个视角带的币率中位是一条 U 型曲线（下图）——小视频 0.95%、
  中腰部 0.54%、头部 2.1%。全局阈值在中腰部冤枉好人、在头部放走水货。「同播放量级横向对比」
  由 U 型曲线的形状本身强制执行。</p>
  <div class="chart-wrap"><svg id="u-chart" class="chart" viewBox="0 0 840 360" xmlns="http://www.w3.org/2000/svg"></svg></div>
  <div class="legend"><i style="background:#D0E3FF"></i>实心带（n≥50）<i style="background:#EFE8DA;border:1px solid #D5CDBE"></i>薄带（n&lt;50，百分位仅供参考）<i style="background:#334EAC"></i>币率中位曲线<i style="background:#B8912F"></i>两案落点（k25/k26）</div>
  <div class="read" id="u-read"></div>
</section>

<section id="s2">
  <div class="sn">二</div>
  <h2>v3 机制与三轮人工校验</h2>
  <p>v3 不是单指标，是<b>主特征 + 指纹规则</b>的两段结构：带内币率百分位定档，行为指纹规则
  （时长、吃灰、擦边、感谢 farming）修正边界。它的合法性不由设计者自封，由三轮人工盲校验逐级授予：</p>
  <div class="kpirow">
    <div class="kpi"><div class="n">95</div><div class="d">第一轮 · 神作全标注<br>CBI 倒挂在此现形</div></div>
    <div class="kpi"><div class="n">76</div><div class="d">第二轮 · 筛查名录<br>一致率 ≈93%（20 条显式 + 56 条默认）</div></div>
    <div class="kpi"><div class="n">48</div><div class="d">第三轮 · 首页域<br>一致率 100%（先生：「我可以给到全对」）</div></div>
    <div class="kpi"><div class="n">2</div><div class="d">特例解剖 · 主动出题<br>双轴理论的两块活标本</div></div>
  </div>
  <p>两支特例是先生亲自点的题。第一支（养生话术）证明 <b>CBI 会把立场型档案顶上神坛</b>；第二支
  （哈基米猫片）证明 <b>互动轴不是表达轴</b>——评论率带内 0.934 分位、赞率 0.801，币率却只有 0.098。
  互动与认同都是零成本动作，只有投币有稀缺成本，所以只有投币诚实。v3 的特征表里没有评论量，
  这两条案例就是它的设计说明书。</p>
  <div class="guide"><b>三轮之后，机制冻结</b>：v3 的阈值（0.93/0.85/0.72）、规则（R2/R3/R4/R8）自此
  冻结为生产口径，单一定义源 engine/，后续一切挖矿以 v3 判档。</div>
</section>

<section id="s3">
  <div class="sn">三</div>
  <h2>两支特例的完整解剖</h2>
  <div class="plates">
    <div class="plate dim"><div class="vh">前案 · 养生话术（103s）</div><div class="vv">CBI 3.17 神 vs v3 垃圾</div>
      <div class="vt">币 0.216 · 藏 0.951 · 赞 0.773 ｜ 诚意比 0.013（&lt;p5）｜ 赞/币 70 ｜ 藏/币 79（R3）<br>静默档案：认同式点赞 + 档案式收藏 + 立场式转发（3.45%），评论率仅 0.094 分位。</div></div>
    <div class="plate"><div class="vh">本案 · 哈基米猫片（51s）</div><div class="vv">CBI 0.79 low vs v3 垃圾</div>
      <div class="vt">币 0.098 · 藏 0.353 · 赞 0.801 · 评论 0.934 ｜ 诚意比 0.043（&lt;p25）｜ 赞/币 135<br>互动消遣：评论区就是内容本体（0.744% = 带内中位 3.7 倍），但互动轴不是表达轴。</div></div>
  </div>
  <p>两案并排的形读：收藏轴劈开物种（0.951 vs 0.353），评论轴劈开行为模式（0.094 vs 0.934），
  只有币率百分位（0.216 / 0.098）<b>把两个物种一起按在垃圾候选</b>。特例由先生盲评盖章，
  成为 v3 校准的第 49、50 号数据点。</p>
</section>

<section id="s4">
  <div class="sn">四</div>
  <h2>参照库审计：百分位的地基</h2>
  <div class="kpirow">
    <div class="kpi"><div class="n">7,672</div><div class="d">参照人口（view≥3000）<br>挖矿域 7,468 + 首页域 204</div></div>
    <div class="kpi"><div class="n">26 / 19</div><div class="d">视角带 / 实心带<br>Δlog₁₀=0.2（每带 1.58 倍）</div></div>
    <div class="kpi"><div class="n">3,006~2.4亿</div><div class="d">播放量跨度</div></div>
    <div class="kpi"><div class="n">200–630</div><div class="d">中段每带样本<br>判别力最强区</div></div>
  </div>
  <p class="note">偏差声明：挖矿域是神作 UP 公开收藏夹的雪球抽样，天然偏向「被收藏的内容」——
  它是同温层参照系，不是全站普查；首页域 204 条是先生的信息茧房切片。薄带 7 个（&lt;4,000 与
  &gt;2,500 万播放）由跨带合并或 Stage-A 的 CBI 粗筛兜底。E 臂的 related 全字段（pubdate/tname/tidv2）
  已为下一代参照库备好纵轴与分区轴。</p>
</section>

<section id="s5">
  <div class="sn">五</div>
  <h2>作品-推荐流：五臂对照</h2>
  <p>挖矿的根，从「人」（神作 UP 的收藏夹雪球）换到「作品」（related 图）。同一批神作种子，
  五种走法：<b>A</b> 定向选 5（优秀补位）、<b>B</b> 随机选 5、<b>C′</b> 纵深 2 神作剪@0、
  <b>D</b> 广度无补位剪@3、<b>E</b> 时光回溯选最早——每臂都是同图上的不同游走策略。</p>
  <div class="chart-wrap"><svg id="arms-chart" class="chart" viewBox="0 0 840 300" xmlns="http://www.w3.org/2000/svg"></svg></div>
  <div class="legend"><i style="background:#081F5C"></i>E 回溯<i style="background:#334EAC"></i>C′ 纵深<i style="background:#7096D1"></i>D 无补位<i style="background:#BAD6EB"></i>A 定向<i style="background:#D0E3FF"></i>B 随机（明度=产量；标注 请求/深度）</div>
  <div class="read" id="arms-read"></div>
  <h3>四条定律</h3>
  <div class="exq">
    <div class="ex"><div class="t"><b>定律一 · 神作聚神作（指数级）</b></div>
      <p style="font-size:12.5px">新番生态 hop1 的 40 邻居中 33 支神作；E 臂洛天依链 25 层收获 339 神。
      神作图上存在「神作大陆」——神作的邻居分布显著偏离普通视频。</p></div>
    <div class="ex"><div class="t"><b>定律二 · 定向的价值在贫瘠区</b></div>
      <p style="font-size:12.5px">A vs B 总量 224/195，但深层复利：hop3+4 为 120 vs 84（+43%）；
      游戏流 hop4 定向 18 神 vs 随机 5 神（3.6×）。饱和生态里随机即定向。</p></div>
    <div class="ex"><div class="t"><b>定律三 · 补位是救生圈，不是产量引擎</b></div>
      <p style="font-size:12.5px">A vs D（唯一差异=优秀补位）：富流前三跳打平（62/55、37/42、66/60）；
      补位只在贫流救命（自来也流 A 活到 4 层，D hop1 剪）。</p></div>
    <div class="ex"><div class="t"><b>定律四 · 死亡的单位是物种</b></div>
      <p style="font-size:12.5px">数学教程四臂全灭（枯/枯/剪/剪），装机、刑诉在 E 臂神=0。
      剪/枯事件按门类记录，即「币率生态位指标」。</p></div>
  </div>
  <h3>命运矩阵</h3>
  <table id="fate-table"></table>
  <p class="note">E 臂种子为全新一批（round2 其余确认神作 6 + 参照库高诚意神作 4），与 A–D 的 5 种子
  不重叠；A/B 共享一次发车（110 请求），C′/D/E 独立发车。全部匿名通道，主账号零重请求。</p>
</section>

<section id="s6">
  <div class="sn">六</div>
  <h2>时光回溯：从 2025 年的一支原创曲，走回 2014 年的诞生代</h2>
  <p>E 臂规则：每层从神作候选里选<b>发布最早</b>的两支。这不是事后解读，是写进游走策略的
  时间偏好——于是「选中即回溯」成为机制本身。三条最深链的轨迹：</p>
  <div class="chart-wrap"><svg id="retro-chart" class="chart" viewBox="0 0 840 420" xmlns="http://www.w3.org/2000/svg"></svg></div>
  <div class="legend"><i style="background:#B8912F"></i>洛天依《夏天.midi》链（339 神 · 25 层）<i style="background:#334EAC"></i>纯手搓初音链（120 神 · 12 层）<i style="background:#7096D1"></i>说唱厂牌链（195 神 · 25 层）<i style="background:#B8912F22"></i>经典层（2014–2017）</div>
  <div class="read" id="retro-read"></div>
  <div class="guide"><b>两条边界</b>：其一，浅链的「向新」是短链假象——hop1-2 邻域带新鲜度偏好，
  链过 8 层后沉底；其二，回溯律对<b>梗类生态失效</b>（鬼畜链被重传与新梗弹跳，向新 +5 个月）。
  时光机器对艺术经典敞开，对玩梗宇宙关闭。</div>
</section>

<section id="s7">
  <div class="sn">七</div>
  <h2>品味悖论：您自己的收藏夹是 CBI 的反面证词</h2>
  <p>主账号收藏夹 3 夹 130 条（默认 108 · Movie 6 · Stefanie 16——孙燕姿专夹）。旧快照 113 条的
  CBI 分布：<b>神 56 / 正常 9 / 低 32 / 垃圾 8 / 未证 8</b>。一半被 CBI 封神——不是品味封神，
  是<b>收藏这个动作本身拉爆 fav 轴</b>。CBI 在自家收藏夹上结构性失真，与特例案同病灶的两面。
  品味画像本身极干净：孙燕姿演唱会、Bocchi 舞台、阿尔都塞哲学课、经典小曲、MC 动画 MV——
  零擦边、零颜值、零养生话术。</p>
</section>

<section id="s8">
  <div class="sn">八</div>
  <h2>诚实边界与交付物</h2>
  <div class="exq">
    <div class="ex"><div class="t"><b>偏差三件套</b></div><p style="font-size:12.5px">雪球域偏「被收藏」；首页域是个人茧房；related 图偏互动型物种。三臂三角测量使偏差可测，不可消除。</p></div>
    <div class="ex"><div class="t"><b>截断 ≠ 枯竭</b></div><p style="font-size:12.5px">A/B/C/D/E 的「到底」全部是深度或预算截断，非自然流尽；自然死（神=0/神+优&lt;5）只发生在贫瘠物种。censored 数据在图例中一律标明。</p></div>
    <div class="ex"><div class="t"><b>接口考古</b></div><p style="font-size:12.5px">view API tname 空串（W9）由 related 全字段补齐（pubdate/tnamev2/tidv2/rcmd_reason）；reply ps 上限 20；tags API 可用。S4/S6 分区分析解锁。</p></div>
    <div class="ex"><div class="t"><b>基线冻结</b></div><p style="font-size:12.5px">全部带内百分位以发车时 7,672 条参照人口计算并冻结——流上发现的新样本不入基线，保证五臂可比。</p></div>
  </div>
  <h3>交付物清单</h3>
  <table>
    <tr><th>交付物</th><th>位置</th><th>说明</th></tr>
    <tr><td>v3 评分机制</td><td class="num">engine/cbi_scale.py + godflow_v*.py</td><td>带内百分位 + R2/R3/R4/R8 规则，95+76+48 三轮校验</td></tr>
    <tr><td>五臂对照引擎</td><td class="num">engine/godflow_v1~v5.py</td><td>定向/随机/纵深/无补位/回溯，全部匿名通道</td></tr>
    <tr><td>五臂数据库</td><td class="num">data/flow_graph/*.json</td><td>11,399 节点、2,049 神作，immutable，按节点分类</td></tr>
    <tr><td>交互式五臂动画</td><td class="num">docs/godflow-anim.html</td><td>A–E 五页签，回溯链可展开候选现场、直达视频</td></tr>
    <tr><td>本报告</td><td class="num">docs/report-2.0.html</td><td>一体化收官 · porcelain-data · 数据注入式可重建</td></tr>
  </table>
  <div class="guide"><b>结语</b>：上一季证明了流的存在，这一季回答了两个更难的问题——「神作如何度量」
  （带内投币百分位，经 95 支标注倒挂与两支特例加冕）与「神作在哪里」（related 图的神作大陆，
  经五臂对照与一条沉入 2014 年的回溯链定位）。收藏与投币是两种语言；从今往后，我们只听后一种。</div>
</section>

<div class="foot">调研报告 2.0 · 看过，却不给 第三季 · 数据注入式构建 engine/build_report_2.py · 全部匿名接口 · 主账号零重请求 · __DATE__</div>
</div>
<script>
const DATA = __DATA__;
const $=id=>document.getElementById(id);
function el(tag,attrs,txt){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const k in attrs)e.setAttribute(k,attrs[k]);if(txt!==undefined)e.textContent=txt;return e;}
function fmtPct(v,d){return (v*100).toFixed(d===undefined?2:d)+'%';}
// ---------- U 型曲线 ----------
(function(){
  const svg=$('u-chart'),W=840,H=360,L=52,R=14,T=16,B=42;
  const D=DATA.bands,n=D.length;
  const ymx=4.2, iw=W-L-R, ih=H-T-B, bw=iw/n;
  for(let g=0;g<=4;g++){
    const y=T+ih-g/4*ih;
    svg.appendChild(el('line',{x1:L,y1:y,x2:W-R,y2:y,stroke:g===0?'#7096D1':'#E3DACB','stroke-width':g===0?1:0.7}));
    svg.appendChild(el('text',{x:L-6,y:y+3,'font-size':9,fill:'#9FB6D4','text-anchor':'end','font-family':'Georgia'},g+'%'));
  }
  const meds=[];
  D.forEach((b,i)=>{
    const x=L+i*bw+1.5, w=bw-3, h=b.med*100/ymx*ih;
    svg.appendChild(el('rect',{x:x,y:T+ih-h,width:w,height:h,fill:b.thin?'#EFE8DA':'#D0E3FF'}));
    meds.push([x+w/2,T+ih-h]);
    if(b.thin){svg.appendChild(el('text',{x:x+w/2,y:T+ih-h-3,'font-size':7,fill:'#C2803A','text-anchor':'middle'},'薄'));}
  });
  svg.appendChild(el('polyline',{points:meds.map(p=>p.join(',')).join(' '),fill:'none',stroke:'#334EAC','stroke-width':1.6}));
  // 两案落点 k25/k26
  const k25=D.findIndex(b=>b.k===25),k26=D.findIndex(b=>b.k===26);
  [[k25,'前案'],[k26,'本案']].forEach(([ki,lab])=>{
    if(ki<0)return;
    const cx=L+ki*bw+bw/2;
    svg.appendChild(el('circle',{cx:cx,cy:T+ih-D[ki].med*100/ymx*ih,r:3.6,fill:'#B8912F'}));
    svg.appendChild(el('text',{x:cx,y:T+ih+13,'font-size':9,fill:'#B8912F','text-anchor':'middle'},lab));
  });
  [[4,'10⁴'],[5,'10⁵'],[6,'10⁶'],[7,'10⁷']].forEach(([e,lab])=>{
    const ki=D.findIndex(b=>b.k===e);
    if(ki<0)return;
    svg.appendChild(el('text',{x:L+ki*bw+bw/2,y:H-B+16,'font-size':10,fill:'#5B7EC2','text-anchor':'middle','font-family':'Georgia'},lab));
  });
  svg.appendChild(el('text',{x:L+iw/2,y:H-8,'font-size':9.5,fill:'#8A5A2B','text-anchor':'middle'},'中段凹陷 0.54% —— 全局阈值在这里失真最狠（米色=薄带）'));
  $('u-read').innerHTML='<b>读数</b>：U 型三段——小视频靠粉丝亲密（中位 <b>0.95%</b>），中腰部内容币率最低（<b>0.54~0.63%</b>），头部爆款全站破圈（<b>2.1~2.6%</b>）。同一个全局阈值，在中腰部冤枉好人、在头部放走水货。「同播放量级横向对比」不是口号，是这条曲线的形状逼出来的度量衡。参照人口 <b>'+DATA.pop.n.toLocaleString()+'</b> 条（挖矿域 '+DATA.pop.mine.toLocaleString()+' + 首页域 '+DATA.pop.home+'，跨文件去重 400），26 带 19 实心。';
})();
// ---------- 五臂产量 ----------
(function(){
  const svg=$('arms-chart'),W=840,H=300,L=110,R=120,T=16,B=30;
  const A=DATA.arms, iw=W-L-R, ih=H-T-B;
  const mx=Math.max(...A.map(a=>a.gods))*1.12;
  const rank=[...A].sort((a,b)=>b.gods-a.gods).map(a=>a.key);
  const col={'retro':'#081F5C','deep':'#334EAC','bnopad':'#7096D1','target':'#BAD6EB','random':'#D0E3FF'};
  A.forEach((a,i)=>{
    const y=T+i*(ih/A.length)+(ih/A.length-18)/2, w=a.gods/mx*iw;
    svg.appendChild(el('rect',{x:L,y:y,width:w,height:18,fill:col[a.key]}));
    svg.appendChild(el('text',{x:L-8,y:y+13,'font-size':12,fill:'#081F5C','text-anchor':'end','font-weight':'600'},a.name));
    svg.appendChild(el('text',{x:L+w+8,y:y+13,'font-size':12,fill:'#081F5C','font-family':'Georgia'},a.gods.toLocaleString()+' 神 · '+a.nodes.toLocaleString()+' 节点 · '+a.requests+' 请求 · 最深 '+a.dmax+' 层'));
  });
  for(let g=0;g<=4;g++){
    const x=L+g/4*iw;
    svg.appendChild(el('line',{x1:x,y1:T,x2:x,y2:T+ih,stroke:'#E3DACB','stroke-width':0.7}));
  }
  $('arms-read').innerHTML='<b>读数</b>：E 回溯以 <b>'+DATA.retro.n_gods+'</b> 神作居首（10 新种子 × 25 层 × 最早优先，沉入经典层）；C′ 纵深 '+DATA.arms[2].gods+' 神（87 请求，性价比之王）；D 证明去掉补位后富流能自然流 8 层；A/B 在 4 层内几乎打平（224/195），定向的溢价在深层（hop3+4 +43%）与贫瘠区（3.6×）。全部臂的「到底」皆截断而非枯竭，自然死只属于贫瘠物种。';
})();
// ---------- 命运矩阵 ----------
(function(){
  const rows=[
    ['A 定向','前沿5 · 神+优补位','神+优<5 枯','55','224','3 活@4层 / 2 枯'],
    ['B 随机','前沿5 · 随机','池<5 枯','55','195','3 活@4层 / 2 枯'],
    ['C′ 纵深','前沿2 神only','神=0 剪','87','438','2 到顶@15层 / 3 剪'],
    ['D 无补位','前沿≤5 神only','神<3 剪','110','312','2 到顶@8层 / 3 剪'],
    ['E 回溯','前沿2 · 最早优先','神=0 剪','187','880','2 到顶@25层 / 8 剪'],
  ];
  let html='<tr><th>臂</th><th>规则</th><th>死法</th><th>请求</th><th>神作</th><th>命运（5 或 10 流）</th></tr>';
  rows.forEach(r=>{html+='<tr><td>'+r[0]+'</td><td>'+r[1]+'</td><td>'+r[2]+'</td><td class="num">'+r[3]+'</td><td class="num"><b>'+r[4]+'</b></td><td>'+r[5]+'</td></tr>';});
  $('fate-table').innerHTML=html;
})();
// ---------- 回溯下降图 ----------
(function(){
  const svg=$('retro-chart'),W=840,H=420,L=56,R=16,T=16,B=36;
  const C=DATA.retro.chains;
  const tmin=new Date('2014-01-01').getTime()/1000, tmax=new Date('2026-12-31').getTime()/1000;
  const yx=t=>T+(t-tmin)/(tmax-tmin)*(H-T-B);
  const xl=h=>L+h/25*(W-L-R);
  const cols={'洛天依':'#B8912F','初音':'#334EAC','说唱':'#7096D1'};
  // 经典层
  svg.appendChild(el('rect',{x:L,y:yx(new Date('2014-01-01').getTime()/1000),width:W-L-R,height:yx(new Date('2017-12-31').getTime()/1000)-yx(new Date('2014-01-01').getTime()/1000),fill:'#B8912F18'}));
  svg.appendChild(el('text',{x:W-R-6,y:yx(new Date('2016-06-01').getTime()/1000),'font-size':10,fill:'#8A6A14','text-anchor':'end'},'经典层 2014–2017'));
  for(let yr=2014;yr<=2026;yr+=2){
    const y=yx(new Date(yr+'-01-01').getTime()/1000);
    svg.appendChild(el('line',{x1:L,y1:y,x2:W-R,y2:y,stroke:yr===2014?'#7096D1':'#E3DACB','stroke-width':yr===2014?1:0.7}));
    svg.appendChild(el('text',{x:L-6,y:y+3,'font-size':9,fill:'#9FB6D4','text-anchor':'end','font-family':'Georgia'},yr));
  }
  for(let h=0;h<=25;h+=5){
    svg.appendChild(el('text',{x:xl(h),y:H-B+18,'font-size':9.5,fill:'#5B7EC2','text-anchor':'middle','font-family':'Georgia'},'L'+h));
    svg.appendChild(el('line',{x1:xl(h),y1:T,x2:xl(h),y2:H-B,stroke:'#E3DACB','stroke-width':0.6}));
  }
  C.forEach(ch=>{
    const key=ch.seed.includes('洛天依')?'洛天依':(ch.seed.includes('初音')?'初音':(ch.seed.includes('说唱')?'说唱':'other'));
    if(key==='other')return;
    const pts=ch.pts.map(p=>[xl(p.hop),yx(p.t)]);
    svg.appendChild(el('polyline',{points:pts.map(p=>p.join(',')).join(' '),fill:'none',stroke:cols[key],'stroke-width':key==='洛天依'?2:1.4,'stroke-opacity':0.85}));
    pts.forEach(p=>{
      svg.appendChild(el('circle',{cx:p[0],cy:p[1],r:key==='洛天依'?3:2.4,fill:cols[key]}));
    });
    svg.appendChild(el('text',{x:pts[pts.length-1][0]+6,y:pts[pts.length-1][1]+3,'font-size':10,fill:cols[key],'font-weight':'600'},ch.seed));
  });
  svg.appendChild(el('text',{x:L,y:H-8,'font-size':9.5,fill:'#5B7EC2'},'横轴 = 层数 L0（种子）→ L25 · 纵轴 = 选中神作的发布年月 · 每点 = 当层 2 支选中神作的发布时间中位'));
  $('retro-read').innerHTML='<b>读数</b>：三条链全部向下沉。<b>洛天依链</b>从 2025-04 的十四岁原创曲出发，L5 即触 <b>2014-04</b>（寻遍星空/亚得里亚海的黎明），此后 20 层在 2014–2017 黄金曲库内行走（老街北、一封孤岛的信、孙尚香、闲云志、叙世、三月雨）——漂移 <b>−72 个月</b>；初音链漂移 <b>−128 个月</b>（2014-01）；说唱链 25 层沉入 2016–2017。沉底 = 算法 related 图的深处埋着门类的经典层；回溯规则把它读成了可点击的编年史（E 页签可展开每层候选现场、直达视频）。边界：梗类生态（鬼畜 +5 个月）被重传与新梗稀释，回溯律对其失效。';
})();
</script>
</body>
</html>
"""

DATA["meta"]["generated"] = time.strftime("%Y-%m-%d %H:%M:%S")
html = TPL.replace("__DATA__", json.dumps(DATA, ensure_ascii=False)).replace("__DATE__", DATA["meta"]["date"])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"[done] -> {OUT} ({os.path.getsize(OUT) // 1024} KB)")
for a in DATA["arms"]:
    print(f"  {a['name']}: gods={a['gods']} nodes={a['nodes']} req={a['requests']} dmax={a['dmax']}")
if DATA["retro"]:
    print(f"  retro chains: {[(c['seed'], c['depth'], c['drift']) for c in DATA['retro']['chains']]}")
