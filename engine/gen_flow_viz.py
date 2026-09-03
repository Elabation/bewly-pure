# -*- coding: utf-8 -*-
"""《墨流》v3 —— 严格按算法顺序的流动画（2026-09-03 重采版）

v2 → v3：数据源从旧库硬编码文件切换为重采自动发现（flow_h2_unbiased_summary /
flow_h3_summary / favmine_flowH{2,3} 裁定链产物 / hop_verdict）；
构图 = 算法本身：同心环半径 = 流的跳数，动画时间线 = 数据生成顺序。
诚实注：本轮 flowmap（种子→评论者拓扑）记录缺陷，评论边仅部分入档。
"""
import json
import math
import os
import random
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from cbi_scale import GOOD_TIERS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
OUT = os.path.join(ROOT, "docs", "flow-viz.html")
random.seed(11)

W, H = 1240, 980
CX, CY = W / 2, H / 2
R = {"seed": 66, "u1": 150, "v1": 250, "u2": 348, "v2": 438}


def polar(r, theta, jitter=0.0):
    r = r + random.uniform(-jitter, jitter)
    return round(CX + r * math.cos(theta), 1), round(CY + r * math.sin(theta), 1)


def _flow_raw(hop):
    """该跳的裁定链产物（最旧优先——hop2 的工程链补跑时间戳更新）。"""
    fs = sorted(f for f in os.listdir(MINE)
                if f.startswith(f"favmine_flowH{hop}_") and f.endswith(".json"))
    return json.load(open(os.path.join(MINE, fs[0]), encoding="utf-8")) if fs else {"users": [], "videos": []}


def build_data():
    fm = json.load(open(os.path.join(MINE, ".flowmap.json"), encoding="utf-8"))
    s2 = json.load(open(os.path.join(MINE, "flow_h2_unbiased_summary.json"), encoding="utf-8"))
    s3 = json.load(open(os.path.join(MINE, "flow_h3_summary.json"), encoding="utf-8"))
    verdict = json.load(open(os.path.join(MINE, "hop_verdict.json"), encoding="utf-8"))
    f2 = _flow_raw(2)
    f3 = _flow_raw(3)

    def qual(videos):
        return [v for v in videos if (v.get("view") or 0) >= 3000]

    v1_all = qual(f2.get("videos") or [])
    v2_all = qual(f3.get("videos") or [])
    # ── 第一环布局：流第 2 跳（源 = 臂①收获神作；种子清单来自裁定链摘要，
    #    评论边拓扑因 flowmap 缺陷仅部分入档——诚实注）──
    seeds1 = [s["bvid"] for s in (s2.get("seeds") or [])]
    seed_cbi = {s["bvid"]: s.get("cbi") or 0 for s in (s2.get("seeds") or [])}
    # 用户神作率（叙事顺序：高品味先亮）
    v1_by_user = defaultdict(list)
    for v in v1_all:
        v1_by_user[v.get("from_user")].append(v)
    u1_rate = {u: sum(1 for v in vs if v["tier"] == "high") / len(vs)
               for u, vs in v1_by_user.items() if len(vs) >= 5}
    u1_list = sorted(u1_rate, key=lambda u: -u1_rate[u])

    nodes, edges = [], []
    for i, s in enumerate(seeds1):
        xx, yy = polar(R["seed"], i / len(seeds1) * 2 * math.pi - math.pi / 2)
        nodes.append({"id": s, "hop": 1, "t": "seed", "x": xx, "y": yy, "r": 6,
                      "c": round(seed_cbi.get(s, 0), 1)})
    for i, u in enumerate(u1_list):
        th = i / len(u1_list) * 2 * math.pi - math.pi / 2 + 0.02
        uxx, uyy = polar(R["u1"], th)
        nodes.append({"id": u, "hop": 1, "t": "user", "x": uxx, "y": uyy, "r": 4.5,
                      "rate": round(u1_rate[u], 2)})
    # 第一跳视频：汇流度（v1 内的入度）
    inflow1 = defaultdict(set)
    for v in v1_all:
        inflow1[v["bvid"]].add(v.get("from_user"))
    v1_in = {b: len(us) for b, us in inflow1.items()}
    user_sector = {u: i / len(u1_list) * 2 * math.pi - math.pi / 2 for i, u in enumerate(u1_list)}
    shown1 = {v["bvid"] for v in v1_all if v["tier"] in ("high", "good")}
    for v in v1_all:
        if v["bvid"] not in shown1 or v.get("from_user") not in user_sector:
            continue
        th = user_sector[v["from_user"]] + (random.random() - 0.5) * 0.32
        x, y = polar(R["v1"], th, 32)
        nodes.append({"id": v["bvid"], "hop": 1, "t": "video", "x": x, "y": y,
                      "r": 2.5 + v1_in.get(v["bvid"], 0) * 1.6, "tier": v["tier"],
                      "c": round(v.get("cbi", 0), 2), "title": (v.get("title") or "")[:24]})
    for u, vs in v1_by_user.items():
        for v in vs:
            if v["bvid"] in shown1:
                edges.append({"s": u, "t": v["bvid"], "kind": "collect", "hop": 1, "tier": v["tier"]})
    # 评论边：仅 flowmap 已入档者（本轮拓扑大部分缺失——诚实注见判定面板）
    for s, us in (fm.get("hop2") or {}).items():
        for u in us:
            if u in u1_rate:
                edges.append({"s": s, "t": u, "kind": "comment", "hop": 1})
    # ── 第二环：流第 3 跳（种子 = 第 2 跳收获的神作）──
    seeds2 = [s["bvid"] for s in (s3.get("seeds") or [])]
    v2_by_user = defaultdict(list)
    for v in v2_all:
        v2_by_user[v.get("from_user")].append(v)
    u2_rate = {u: sum(1 for v in vs if v["tier"] == "high") / len(vs)
               for u, vs in v2_by_user.items() if len(vs) >= 5}
    u2_list = sorted([u for u in u2_rate], key=lambda u: -u2_rate[u])
    for i, s in enumerate(seeds2):
        seed_node = next((n for n in nodes if n["id"] == s), None)
        if seed_node:  # 第二跳种子同时是第一跳视频 → 强化标记
            seed_node["t"] = "seed2"; seed_node["r"] = 7
        else:
            sxx, syy = polar(R["seed"], 1.2 + i)
            nodes.append({"id": s, "hop": 2, "t": "seed2", "x": sxx, "y": syy, "r": 7})
    for i, u in enumerate(u2_list):
        th = i / len(u2_list) * 2 * math.pi + 0.16
        wxx, wyy = polar(R["u2"], th)
        nodes.append({"id": u, "hop": 2, "t": "user", "x": wxx, "y": wyy, "r": 4.5,
                      "rate": round(u2_rate[u], 2), "hop2": 1})
    inflow2 = defaultdict(set)
    for v in v2_all:
        inflow2[v["bvid"]].add(v.get("from_user"))
    v2_sector = {u: i / max(1, len(u2_list)) * 2 * math.pi + 0.16 for i, u in enumerate(u2_list)}
    shown2 = {v["bvid"] for v in v2_all if v["tier"] in ("high", "good")}
    for v in v2_all:
        if v["bvid"] not in shown2 or v.get("from_user") not in v2_sector:
            continue
        th = v2_sector[v["from_user"]] + (random.random() - 0.5) * 0.3
        x, y = polar(R["v2"], th, 36)
        nodes.append({"id": v["bvid"], "hop": 2, "t": "video", "x": x, "y": y,
                      "r": 2.5 + len(inflow2.get(v["bvid"], set())) * 1.6, "tier": v["tier"],
                      "c": round(v.get("cbi", 0), 2), "title": (v.get("title") or "")[:24], "hop2": 1})
    for u, vs in v2_by_user.items():
        for v in vs:
            if v["bvid"] in shown2:
                edges.append({"s": u, "t": v["bvid"], "kind": "collect", "hop": 2, "tier": v["tier"]})
    mist = [{"x": round(CX + (random.random() - .5) * 2 * 470, 1),
             "y": round(CY + (random.random() - .5) * 2 * 640, 1)}
            for _ in (v1_all + v2_all)]
    curve = [0.253] + [v["rate"] for v in (verdict.get("verdicts") or [])]
    return {"W": W, "H": H, "nodes": nodes, "edges": edges, "mist": mist,
            "meta": {"n_seed1": len(seeds1), "n_u1": len(u1_list), "n_seed2": len(seeds2),
                     "n_u2": len(u2_list), "curve": curve,
                     "base": 0.069, "final_hops": verdict.get("final_hops")}}


TPL = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>墨流 v3 · 按算法顺序流动</title>
<style>
  :root{--paper:#f7f5f0;--ink:#1c2430;--blue:#35507a;--gold:#b8912f;--silver:#5b7ba0;--faint:#8b94a3;--blue2:#7fa3d0}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--paper);color:var(--ink);font-family:'Lanxi-叮叮','Source Han Serif SC','Noto Serif SC',serif;
       display:flex;flex-direction:column;align-items:center;padding:24px 10px;min-height:100vh}
  h1{font-size:25px;letter-spacing:6px}
  .sub{font-size:12.5px;color:var(--faint);letter-spacing:1.5px;margin:4px 0 12px}
  #stage{background:linear-gradient(180deg,#fbfaf6,#f3f1ea);border:1px solid #d8d3c8;border-radius:10px;
         box-shadow:0 2px 24px rgba(28,36,48,.06);overflow:hidden}
  svg{display:block}
  .bar{display:flex;gap:16px;align-items:center;margin-top:12px;font-size:13px}
  button{background:var(--ink);color:var(--paper);border:0;border-radius:6px;padding:7px 18px;letter-spacing:3px;cursor:pointer}
  #panel{margin-top:14px;max-width:920px;text-align:center;font-size:14px;line-height:1.9;opacity:0;transition:opacity 1.2s}
  #panel.show{opacity:1}
  #panel b{color:var(--gold)}
  .legend{display:flex;gap:16px;font-size:12px;color:var(--faint);margin-top:8px;flex-wrap:wrap;justify-content:center}
  .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;vertical-align:middle}
  .sceneTag{position:fixed;left:18px;top:16px;font-size:13px;color:var(--blue);letter-spacing:2px;opacity:.85}
  @media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>
<div class="sceneTag" id="tag"></div>
<h1>墨 流 v3</h1>
<div class="sub">同心环 = 流的跳数 · 动画顺序 = 算法顺序 —— 全部数据来自重采臂① → 流第2跳 → 流第3跳真实记录（无偏统计链）</div>
<div id="stage"><svg id="svg" width="__W__" height="__H__" viewBox="0 0 __W__ __H__"></svg></div>
<div class="bar">
  <button onclick="location.reload()">重 播</button>
  <span style="color:var(--faint)">环1：臂①收获神作 → 新评论区 → 收藏　|　环2：第三跳种子 → 新用户 → 新收藏（hop4 触发停流）</span>
</div>
<div class="legend">
  <span><span class="dot" style="background:var(--gold)"></span>神作≥3</span>
  <span><span class="dot" style="background:var(--silver)"></span>优秀≥2</span>
  <span><span class="dot" style="background:var(--blue)"></span>流2用户</span>
  <span><span class="dot" style="background:var(--blue2)"></span>流3用户</span>
  <span>实线=收藏边　点的大小=汇流度　（评论边拓扑因 flowmap 缺陷未完整入档，见判定面板诚实注）</span>
</div>
<div id="panel">
  第一层（臂①）神作命中 <b>25.3%</b> → 流2 <b>24.6%</b>（ρ=0.973）→ 流3 <b>29.6%</b>（ρ=1.203）→ 流4 21.6%（ρ=0.730，相对下滑 27% 停）<br>
  基线（臂②）<b>6.9%</b>：E1 3.79×（p=3.0×10⁻⁶）· E2 1.49×（p=0.0128）—— 无偏裁定：<b>流 3 跳</b>，hop4 仍为基线 3.1×（衰减≠死亡）；浓度剪枝叙事撤回（工程链 0.57×）<br>
  诚实注：评论边拓扑因 flowmap 记录缺陷未完整入档（代码已修，本轮不可恢复）；hop4 跌幅含贡献用户聚簇方差
</div>
<script>
const D = __DATA__;
const svg = document.getElementById('svg'), NS = 'http://www.w3.org/2000/svg';
const el = (t,a)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);return e};
const nd = Object.fromEntries(D.nodes.map(n=>[n.id+'|'+n.hop,n]));
const C = {seed:'#b8912f',seed2:'#b8912f',user:'#35507a',video:'#8b94a3'};
const VC = {high:'#b8912f',good:'#5b7ba0'};
function k(id,hop){return nd[id+'|'+hop]}
function build(){
  svg.innerHTML='';
  const gM=el('g',{opacity:0}); D.mist.forEach(m=>gM.appendChild(el('circle',{cx:m.x,cy:m.y,r:1.3,fill:'#c9c4ba',opacity:.45})));
  svg.appendChild(gM);
  const gE=el('g',{}), gN=el('g',{}), gP=el('g',{});
  D.edges.forEach((e,i)=>{
    const a=k(e.s,e.kind==='comment'?(e.hop===1?1:2):(e.s.includes('BV')?1:1));
    const sn=D.nodes.find(n=>n.id===e.s), tn=D.nodes.find(n=>n.id===e.t);
    if(!sn||!tn)return;
    const isC=e.kind==='comment';
    const ln=el('line',{x1:sn.x,y1:sn.y,x2:tn.x,y2:tn.y,pathLength:1,
      stroke:isC?(e.hop===2?'#7fa3d0':'#35507a'):(e.tier==='high'?'#b8912f':'#35507a'),
      'stroke-width':isC?.8:(e.tier==='high'?1:.55),
      'stroke-dasharray':isC?'3 3':'1','stroke-dashoffset':isC?0:1,opacity:0});
    const dl=isC?(e.hop===1?2.2+Math.random()*2.6:10.2+Math.random()*2.8)
               :(e.hop===1?5+Math.random()*3.6:13+Math.random()*3.6);
    ln.style.transition=`opacity .9s ease ${dl}s, stroke-dashoffset .9s ease ${dl}s`;
    gE.appendChild(ln);
  });
  svg.appendChild(gE);
  D.nodes.forEach((n,i)=>{
    let c=n.t==='seed'?C.seed:n.t==='seed2'?C.seed2:n.t==='user'?(n.hop2?'#7fa3d0':'#35507a'):(VC[n.tier]||C.video);
    let dl=n.t==='seed'?i*.18:n.t==='seed2'?9.6:n.hop2?(10.6+(i%60)*.05):(3.4+(i%36)*.07);
    const c1=el('circle',{cx:n.x,cy:n.y,r:n.r,fill:c,opacity:0});
    c1.style.transition=`opacity .9s ease ${dl}s`;
    gN.appendChild(c1);
  });
  svg.appendChild(gN);
  // 汇流脉冲（两跳视频 r 大者）
  let pi=0;
  D.nodes.filter(n=>n.t==='video'&&n.r>=6).forEach(n=>{
    const c=el('circle',{cx:n.x,cy:n.y,r:n.r,fill:'none',stroke:n.hop2?'#7fa3d0':'#b8912f','stroke-width':1.3,opacity:0});
    c.style.transition=`opacity .8s ease ${n.hop2?15.5:8.6}s`;
    c.appendChild(el('animate',{attributeName:'r',from:n.r,to:n.r+9,dur:'2.4s',repeatCount:'indefinite',begin:(n.hop2?16:9)+'s'}));
    gP.appendChild(c); pi++;
  });
  svg.appendChild(gP);
}
const TAGS=[[0,'① 种子：臂①收获的汇流/补足神作'],[2.2,'② 流2：神作评论区抓人（虚线=评论边·已入档部分）'],[5,'③ 流2：挖收藏夹（实线=收藏边）'],[8.6,'④ 汇流：被多人独立收藏的视频开始脉冲'],[9.6,'⑤ 流3：新种子 → 新评论区'],[13,'⑥ 流3：新用户的新收藏'],[17.5,'⑦ 判定：无偏裁定 3 跳 —— hop4 相对下滑 27% 停流']];
let ti=0;
function tickTag(){
  const t=(performance.now()-t0)/1000;
  while(ti<TAGS.length&&t>=TAGS[ti][0]){document.getElementById('tag').textContent=TAGS[ti][1];ti++;}
  if(ti<TAGS.length)requestAnimationFrame(tickTag);
}
let t0=performance.now();
build();
requestAnimationFrame(()=>requestAnimationFrame(()=>{
  svg.querySelectorAll('circle').forEach(c=>c.style.opacity=.95);
  svg.querySelectorAll('line').forEach(l=>{if(l.getAttribute('stroke-dasharray')==='1')l.style.strokeDashoffset=0;l.style.opacity=l.getAttribute('stroke-dasharray')==='3 3'?.75:.6;});
  svg.querySelectorAll('g')[0].style.transition='opacity 2s ease 7s';
  svg.querySelectorAll('g')[0].style.opacity=1;
  t0=performance.now();requestAnimationFrame(tickTag);
  setTimeout(()=>document.getElementById('panel').classList.add('show'),17500);
}));
</script>
</body>
</html>
"""


def main():
    d = build_data()
    html = TPL.replace("__DATA__", json.dumps(d, ensure_ascii=False)) \
              .replace("__W__", str(W)).replace("__H__", str(H))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    kinds = defaultdict(int)
    for e in d["edges"]:
        kinds[f"{e['kind']}{e['hop']}"] += 1
    print(f"[viz2] nodes={len(d['nodes'])} edges={dict(kinds)} -> {OUT}")


if __name__ == "__main__":
    main()
