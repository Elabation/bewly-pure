# -*- coding: utf-8 -*-
"""神作货架 v2 —— 分区条一区一页 · 封面卡 · 年代桶 · 乱序重排 · 回退/撤销 · 众包标注。

修订（Elabation 十条 · 2026-09-04）：
  1 封面：player/pic 回填，卡片 16:10 封面
  2 回退按钮：分区历史栈 + 「←」
  3 标注可撤销：逐卡撤销 + 工具条撤销上次
  4 美工：参考高星目录站设计语言（封面网格 + 胶囊筛选 + 分区条 + 悬浮抬升）
  5 年代 3 年一桶，更久远 5 年一桶
  6 分区条：一个分区占一页，不再挤一页
  7/10 乱序宇宙：全站乱序，每次重排随机展示（隐藏 related 挖掘痕迹）
  8 R10 博同情降级：求助/感谢/感动/苦难标题特征过强降一级，并逐出声援之选
  9 新声 = 来自首页爬取的视频（src=home），不再按 24-26 年份划分
"""
import json
import os
import sys
import time
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from god_pool import build_pool, load_backfill, FG  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "god-shelf.html")

pool, meta = build_pool()
bf = load_backfill()
cf_path = os.path.join(FG, "cover_backfill.json")
covers = json.load(open(cf_path, encoding="utf-8")) if os.path.exists(cf_path) else {}
n_cov = 0
for b, r in pool.items():
    x = bf.get(b)
    if x and x.get("pubdate") and not r.get("pubdate"):
        r["pubdate"] = x["pubdate"]
    if x:
        if x.get("owner"):
            r["owner"] = x["owner"]
        st = x.get("stat") or {}
        if st.get("view"):
            vr = max(1, st["view"])
            r["view"] = st["view"]
            r["coin"] = st.get("coin") or 0
            r["fav"] = st.get("fav") or 0
            r["like"] = st.get("like") or 0
            r["coin_rate"] = round(r["coin"] / vr, 5)
            r["fav_rate"] = round(r["fav"] / vr, 5)
            r["like_rate"] = round(r["like"] / vr, 5)
    pic = covers.get(b)
    if pic:
        r["pic"] = pic
        n_cov += 1
rows = sorted(pool.values(), key=lambda r: -(r.get("pct") or 0))
n_cov = sum(1 for r in rows if r.get("pic"))
for r in rows:
    r["year"] = time.localtime(r["pubdate"]).tm_year if r.get("pubdate") else None
n_god = sum(1 for r in rows if r["tier"] == "神作候选")
n_r10 = sum(1 for r in rows if any(str(f).startswith("R10") for f in (r.get("firings") or [])))
years = sorted({r["year"] for r in rows if r["year"]}, reverse=True)
cats = defaultdict(int)
for r in rows:
    cats[r["category"]] += 1
top_cats = [c for c, _ in sorted(cats.items(), key=lambda kv: -kv[1]) if c != "其他"][:12]
n_home = sum(1 for r in rows if r.get("src") == "home")
n_ml = sum(1 for r in rows if r.get("cat_src") == "ml")
n_queue = len(rows) - n_ml
DATA = {"rows": rows, "cats": top_cats,
        "meta": {"date": time.strftime("%Y-%m-%d"), "n_god": n_god, "n_pool": len(rows),
                 "n_cov": n_cov, "n_r10": n_r10, "n_home": n_home, "n_ml": n_ml, "n_queue": n_queue,
                 "yr_min": years[-1] if years else 0, "yr_max": years[0] if years else 0,
                 "pop_n": meta["pop_n"]}}
print(f"[site] 池 {len(rows)}（神 {n_god}）｜ 封面 {n_cov} ｜ R10 降档 {n_r10} ｜ 首页源 {n_home} ｜ ML {n_ml} / 待分类 {n_queue}")

TPL = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>神作货架 · 带内百分位甄选</title>
<style>
:root{--ink:#081F5C;--data1:#334EAC;--data2:#7096D1;--data3:#BAD6EB;--paper:#F7F2EB;--shadow:#E3DACB;--sub:#5B7EC2;--dim:#9FB6D4;--gold:#B8912F;--card:#fffdf9}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font:14px/1.8 -apple-system,'PingFang SC','Microsoft YaHei',sans-serif}
.wrap{max-width:1360px;margin:0 auto;padding:0 20px 70px}
header{padding:46px 0 18px;border-bottom:1px solid var(--shadow)}
.kicker{font-size:11px;letter-spacing:4px;color:var(--data1);border:1px dashed var(--data2);display:inline-block;padding:4px 14px;border-radius:999px;margin-bottom:16px}
h1{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:34px;font-weight:900;letter-spacing:2px}
.lede{font-size:13.5px;color:var(--sub);margin-top:8px;max-width:820px}
.kpirow{display:flex;gap:12px;flex-wrap:wrap;margin-top:16px}
.kpi{background:#EFE8DA;padding:9px 14px;flex:1 1 150px;border-radius:6px}
.kpi .n{font-family:Georgia,serif;font-size:22px;color:var(--ink)}
.kpi .d{font-size:11px;color:var(--sub);line-height:1.5}
.secbar{position:sticky;top:0;background:color-mix(in srgb,var(--paper) 88%,transparent);backdrop-filter:blur(8px);z-index:30;border-bottom:1px solid var(--shadow);padding:9px 0 8px;display:flex;gap:7px;overflow-x:auto}
.secbar button{background:transparent;border:1px solid var(--data3);color:#334EAC;padding:4px 13px;font-size:12.3px;cursor:pointer;border-radius:999px;font-family:inherit;white-space:nowrap}
.secbar button.on{background:#081F5C;color:#F7F2EB;border-color:#081F5C}
.secbar button:hover{border-color:#334EAC}
.toolbar{position:sticky;top:44px;background:color-mix(in srgb,var(--paper) 88%,transparent);backdrop-filter:blur(8px);z-index:25;padding:8px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center;border-bottom:1px solid var(--shadow)}
.toolbar input,.toolbar select{background:#fffdf9;border:1px solid var(--data2);color:var(--ink);padding:6px 10px;font-size:12.5px;border-radius:6px;font-family:inherit}
.toolbar input{flex:1 1 220px;min-width:160px}
.toolbar button{background:#fffdf9;border:1px solid var(--data2);color:#334EAC;padding:5px 12px;font-size:12px;cursor:pointer;border-radius:6px;font-family:inherit}
.toolbar button.on{background:#081F5C;color:#F7F2EB;border-color:#081F5C}
.annbar{font-size:11.5px;color:#5B7EC2;margin-left:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px;margin:18px 0}
.card{background:var(--card);border:1px solid var(--shadow);border-radius:10px;overflow:hidden;transition:transform .18s,box-shadow .18s;position:relative}
.card:hover{transform:translateY(-3px);box-shadow:0 10px 24px #081f5c1a}
.cover{position:relative;aspect-ratio:16/10;background:linear-gradient(135deg,#D8E4F5,#EFE8DA);overflow:hidden}
.cover img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .3s}
.card:hover .cover img{transform:scale(1.05)}
.cover .pct{position:absolute;right:8px;top:8px;background:#081F5CE6;color:#F7F2EB;font-family:Georgia,serif;font-size:13px;padding:2px 8px;border-radius:999px}
.card.god .cover .pct{background:#B8912FE6}
.cover .notier{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:Georgia,serif;font-size:30px;color:#9FB6D4}
.cover .annmark{position:absolute;left:8px;top:8px;background:#B8912F;color:#fff;font-size:9.5px;padding:1px 7px;border-radius:999px}
.body{padding:9px 11px 11px}
.badges{display:flex;gap:5px;margin-bottom:5px;flex-wrap:wrap}
.badge{font-size:9.5px;border:1px solid var(--data2);color:var(--data1);border-radius:3px;padding:0 5px;white-space:nowrap}
.badge.god{background:#B8912F;color:#fff;border-color:#B8912F}
.badge.r10{border-color:#C2803A;color:#9A6428}
.badge.home{border-color:#2F6B3A;color:#2F6B3A}
.t{font-size:12.8px;line-height:1.55;height:40px;overflow:hidden;margin-bottom:5px}
.t a{color:var(--ink);text-decoration:none;font-weight:600}
.t a:hover{color:var(--data1);text-decoration:underline}
.m{font-size:10.8px;color:var(--sub);line-height:1.7}
.m .yr{font-family:Georgia,serif;color:#334EAC}
.m .cr{font-family:Georgia,serif;color:#8A6A14}
.tools{margin-top:7px;display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.tools button{background:#EFE8DA;border:none;color:#334EAC;font-size:10.5px;padding:2px 9px;cursor:pointer;border-radius:3px;font-family:inherit}
.tools button.undo{color:#9A6428}
.annbox{display:none;margin-top:8px;border-top:1px dashed var(--shadow);padding-top:8px}
.annbox.open{display:block}
.annbox select,.annbox input{width:100%;border:1px solid var(--data2);background:#fffdf9;color:var(--ink);font-size:11.5px;padding:3px 6px;margin-bottom:5px;font-family:inherit}
.annbox .btns{display:flex;gap:6px}
.annbox .btns button{flex:1;background:#081F5C;color:#F7F2EB;border:none;font-size:11px;padding:4px 0;cursor:pointer;font-family:inherit}
.annbox .btns button.err{background:#C2803A}
.pagen{display:flex;gap:8px;justify-content:center;align-items:center;margin:18px 0}
.pagen button{background:#fffdf9;border:1px solid var(--data2);color:#334EAC;padding:6px 16px;font-size:12.5px;cursor:pointer;border-radius:6px;font-family:inherit}
.sec-title{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:22px;font-weight:800;letter-spacing:1px;margin:20px 0 4px}
.sec-sub{font-size:12px;color:var(--sub);margin-bottom:6px}
.empty{padding:60px;text-align:center;color:var(--sub)}
.foot{padding:30px 0 10px;font-size:11.5px;color:var(--dim);letter-spacing:1px;border-top:1px solid var(--shadow);margin-top:40px}
.foot p{margin:6px 0;max-width:980px}
a{color:var(--data1)}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="kicker">神作货架 v2 · 带内投币百分位甄选 · 开放标注 · 分区浏览</div>
  <h1>神作货架</h1>
  <div class="lede">不猜你喜欢什么，只陈列「投币真谢」过的作品。related 图五臂遍历采集，带内投币百分位 + R2/R3/R4/R9/R10 规则甄选；
  支持搜索、年代分区、乱序重排、众包标注（门类修正 / 盖章 / 纠错，可撤销、可导出）。</div>
  <div class="kpirow">
    <div class="kpi"><div class="n" id="k-god"></div><div class="d">在架神作（pct≥0.93）</div></div>
    <div class="kpi"><div class="n" id="k-all"></div><div class="d">含优秀候选全池</div></div>
    <div class="kpi"><div class="n" id="k-cov"></div><div class="d">封面覆盖</div></div>
    <div class="kpi"><div class="n" id="k-yr"></div><div class="d">年代跨度</div></div>
    <div class="kpi"><div class="n" id="k-r10"></div><div class="d">R10 博同情降档</div></div>
    <div class="kpi"><div class="n" id="k-ml"></div><div class="d">ML 自动分类（置信≥0.65）</div></div>
    <div class="kpi"><div class="n" id="k-queue"></div><div class="d">待分类 · 求助</div></div>
    <div class="kpi"><div class="n" id="k-ann"></div><div class="d">我的标注（本地）</div></div>
  </div>
</header>
<div class="secbar" id="secbar"></div>
<div class="toolbar">
  <button id="backBtn" style="display:none" onclick="goBack()">← 回退</button>
  <input id="q" placeholder="搜索标题 / UP / 门类…">
  <select id="cat"><option value="all">全部门类</option></select>
  <select id="sort">
    <option value="pct">按品质（百分位）</option>
    <option value="new">按最新发布</option>
    <option value="coin">按投币绝对值</option>
    <option value="view">按播放</option>
    <option value="shout">按声援度（币/藏）</option>
  </select>
  <button id="t-god" class="on" onclick="setTier('god')">仅神作</button>
  <button id="t-all" onclick="setTier('all')">含优秀</button>
  <button onclick="reshuffle()" title="重掷一次全站顺序">乱序重排</button>
  <button onclick="undoLast()" title="撤销上一次标注">撤销上次标注</button>
  <button onclick="exportAnn()">导出标注</button>
  <label style="background:#fffdf9;border:1px solid var(--data2);color:#334EAC;padding:5px 12px;font-size:12px;cursor:pointer;border-radius:6px">导入<input type="file" id="imp" accept=".json" style="display:none"></label>
  <span class="annbar" id="annbar"></span>
</div>
<div class="sec-title" id="sec-title"></div>
<div class="sec-sub" id="sec-sub"></div>
<div class="grid" id="grid"></div>
<div class="pagen"><button id="more" onclick="moreGrid()">加载更多</button></div>
<div class="foot">
  <p><b>方法论</b>：候选池 = 参照库 + related 图五臂遍历（定向/随机/纵深/无补位/时光回溯）合并去重；判档 = 带内投币百分位（Δlog₁₀=0.2 排位）+ 行为指纹（R2 时长 / R3 吃灰 / R4 擦边 / R9 声援提档：币&gt;赞或币&gt;藏直升一档 / R10 博同情降档：求助·众筹·苦难类标题特征过强降一级并逐出声援之选）。百分位基线 7,672 条冻结。</p>
  <p><b>训练-监督闭环</b>：分类由标题 n-gram 朴素贝叶斯自动完成（官方分区种子训练，留出集 71%，高置信精确率 77%）。置信度 ≥0.65 自动上架，其余进「待分类」等你帮忙。你的门类修正导出 JSON 交回 → 重训模型 → 换架，闭环完成。</p>
  <p><b>补货管线</b>：首页爬取 → 新种子 L1 图遍历（一铲 11+ 神）→ 高密度物种 C′/E 纵深 → build_site.py 一键换架。</p>
  <p>数据日期 __DATE__ · 全部匿名通道 · 主账号零重请求 · 封面与视频版权归原作者所有</p>
</div>
</div>
<script>
const DATA = __DATA__;
const POOL = DATA.rows;
const CATS = DATA.cats.concat(['其他']);
const $=id=>document.getElementById(id);
const esc=s=>(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const fmtW=v=>v>=10000?(v/10000>=100?Math.round(v/10000)+'万':(v/10000).toFixed(1)+'万'):String(v);
const ym=t=>{if(!t)return '—';const d=new Date(t*1000);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0');};
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
let ann={};try{ann=JSON.parse(localStorage.getItem('godshelf_ann')||'{}')}catch(e){ann={}}
let annHistory=[];
let state={sec:'best',q:'',cat:'all',sort:'pct',tier:'god',shown:60,seed:Math.floor(Math.random()*1e9)};
const SECTIONS=[
 {id:'best',name:'镇店之宝',sub:'带内百分位顶格的神作，全站最高殿堂'},
 {id:'mix',name:'精选混合',sub:'百分位与声援度混合 curated——降低同质化的一页'},
 {id:'home',name:'新声 · 来自首页',sub:'由首页爬取入选的新面孔（src=home）'},
 {id:'shout',name:'声援之选',sub:'币大于藏且未触发 R10 博同情降档的视频'},
 {id:'queue',name:'待分类',sub:'机器置信度不足——请帮忙把它们放上正确的货架'},
 {id:'shuffle',name:'乱序宇宙',sub:'全站乱序，每次重排随机展示——切断图游走的可见线索'},
 {id:'e2024',name:'2024–2026',sub:'近三年（三年一桶）'},
 {id:'e2021',name:'2021–2023',sub:'三年一桶'},
 {id:'e2018',name:'2018–2020',sub:'三年一桶'},
 {id:'e2013',name:'2013–2017',sub:'更久远五年一桶'},
 {id:'eold',name:'2012 及以前',sub:'货架最深处的沉积层'},
 {id:'all',name:'全部浏览',sub:'全池無过滤浏览'},
];
function secArr(id){
  let arr=POOL.filter(r=>state.tier==='god'?r.tier==='神作候选':true);
  if(id==='home') arr=arr.filter(r=>r.src==='home');
  if(id==='shout') arr=arr.filter(r=>r.coin_rate>r.fav_rate && !isR10(r));
  if(id==='queue') arr=arr.filter(r=>r.cat_src!=='ml');
  if(id==='e2024') arr=arr.filter(r=>r.year&&r.year>=2024);
  if(id==='e2021') arr=arr.filter(r=>r.year&&r.year>=2021&&r.year<=2023);
  if(id==='e2018') arr=arr.filter(r=>r.year&&r.year>=2018&&r.year<=2020);
  if(id==='e2013') arr=arr.filter(r=>r.year&&r.year>=2013&&r.year<=2017);
  if(id==='eold') arr=arr.filter(r=>r.year&&r.year<=2012);
  if(id==='best') arr=[...arr].sort((a,b)=>(b.pct||0)-(a.pct||0));
  if(id==='mix'){
    const g=[...arr].sort((a,b)=>(b.pct||0)-(a.pct||0)).slice(0,Math.ceil(arr.length*0.25));
    const s=[...arr].filter(r=>r.coin_rate>r.fav_rate).sort((a,b)=>(b.coin_rate/Math.max(1e-5,b.fav_rate))-(a.coin_rate/Math.max(1e-5,a.fav_rate))).slice(0,120);
    const nw=[...arr].filter(r=>r.pubdate).sort((a,b)=>b.pubdate-a.pubdate).slice(0,120);
    const seen=new Set(),out=[];
    for(const r of [...nw,...g,...s]){if(!seen.has(r.bvid)){seen.add(r.bvid);out.push(r);}}
    arr=out;
  }
  if(id==='shuffle'){
    const rnd=mulberry32(state.seed);
    arr=[...arr];
    for(let i=arr.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[arr[i],arr[j]]=[arr[j],arr[i]];}
  }
  const s=state.sort;
  if(id!=='shuffle') arr.sort((a,b)=>{
    if(s==='pct')return (b.pct||0)-(a.pct||0);
    if(s==='new')return (b.pubdate||0)-(a.pubdate||0);
    if(s==='coin')return (b.coin||0)-(a.coin||0);
    if(s==='view')return (b.view||0)-(a.view||0);
    if(s==='shout')return (b.coin_rate/Math.max(1e-5,b.fav_rate))-(a.coin_rate/Math.max(1e-5,a.fav_rate));
    return 0;
  });
  return arr;
}
function isR10(r){return (r.firings||[]).some(f=>String(f).startsWith('R10'));}
function applyFilters(arr){
  const q=state.q.trim().toLowerCase();
  if(state.cat!=='all')arr=arr.filter(r=>r.category===state.cat);
  if(q){arr=arr.filter(r=>((r.title||'')+' '+(r.owner||'')+' '+r.category).toLowerCase().includes(q));}
  return arr;
}
function cardHTML(r){
  const god=r.tier==='神作候选';
  const a=ann[r.bvid]||{};
  const catNow=a.cat||r.category;
  const r10=isR10(r);
  return `<div class="card${god?' god':''}">
    <div class="cover">${r.pic?`<img loading="lazy" referrerpolicy="no-referrer" src="${esc(r.pic)}" onerror="this.style.display='none'">`:'<div class="notier">'+Math.round((r.pct||0)*100)+'</div>'}
      <span class="pct">${Math.round((r.pct||0)*100)}</span>
      ${a.stamp?'<span class="annmark">'+(a.stamp==='god'?'已盖章':'已纠错')+'</span>':''}</div>
    <div class="body">
      <div class="badges"><span class="badge${god?' god':''}">${god?'神作':'优秀'}</span>
        ${r10?'<span class="badge r10">R10 已降档</span>':''}
        ${r.src==='home'?'<span class="badge home">首页新声</span>':''}
        <span class="badge">${esc(r.category)}</span>${r.cat_src!==`ml`?`<span class="badge" style="border-color:#C2803A;color:#9A6428">待分类</span>`:``}</div>
      <div class="t"><a href="https://www.bilibili.com/video/${r.bvid}" target="_blank" rel="noopener">${esc(r.title)}</a></div>
      <div class="m"><span class="yr">${r.year||'年代待考'}</span> · ${fmtW(r.view)}播放 · <span class="cr">币率 ${(r.coin_rate*100).toFixed(2)}%</span>${r.owner?' · '+esc(r.owner.slice(0,12)):''}</div>
      <div class="tools"><button onclick="toggleAnn('${r.bvid}')">标注 ▾</button>
        ${a.stamp||a.cat||a.note?`<button class="undo" onclick="clearAnn('${r.bvid}')">撤销标注</button>`:''}</div>
      <div class="annbox" id="ann-${r.bvid}">
        <select onchange="setAnn('${r.bvid}','cat',this.value)">${CATS.map(c=>`<option ${c===catNow?'selected':''}>${c}</option>`).join('')}</select>
        <input placeholder="一句话备注（可选）" value="${esc(a.note||'')}" onchange="setAnn('${r.bvid}','note',this.value)">
        <div class="btns"><button onclick="setAnn('${r.bvid}','stamp','god')">盖章神作</button><button class="err" onclick="setAnn('${r.bvid}','stamp','err')">纠错</button></div>
      </div>
    </div></div>`;
}
function toggleAnn(b){const el=$('ann-'+b);if(el)el.classList.toggle('open');}
function save(){localStorage.setItem('godshelf_ann',JSON.stringify(ann));$('k-ann').textContent=Object.keys(ann).length;}
function pushHist(b,prev){annHistory.push({b,prev:JSON.stringify(prev)});if(annHistory.length>100)annHistory.shift();}
function setAnn(b,k,v){
  pushHist(b,ann[b]||null);
  ann[b]=Object.assign(ann[b]||{},{[k]:v,ts:Date.now()});
  if(k==='stamp'&&v==='err'&&!ann[b].cat){/* 纠错时门类留空待补 */}
  save();render();
}
function clearAnn(b){pushHist(b,ann[b]||null);delete ann[b];save();render();}
function undoLast(){
  const last=annHistory.pop();
  if(!last){alert('没有可撤销的标注了');return;}
  if(last.prev){ann[last.b]=JSON.parse(last.prev);}else{delete ann[last.b];}
  save();render();
}
function reshuffle(){state.seed=Math.floor(Math.random()*1e9);state.shuffleOn=true;render();}
function exportAnn(){
  const blob=new Blob([JSON.stringify({exported:Date.now(),ann},null,1)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='godshelf_annotations.json';a.click();
}
$('imp').addEventListener('change',ev=>{
  const f=ev.target.files[0];if(!f)return;
  const rd=new FileReader();
  rd.onload=()=>{try{const d=JSON.parse(rd.result);const im=d.ann||d;let n=0;
    for(const b in im){ann[b]=Object.assign(ann[b]||{},im[b]);n++;}
    save();render();alert('已导入 '+n+' 条标注');
  }catch(e){alert('导入失败：'+e);}};
  rd.readAsText(f);
});
let qtimer=null;
$('q').addEventListener('input',e=>{state.q=e.target.value;clearTimeout(qtimer);qtimer=setTimeout(render,150);});
$('cat').addEventListener('change',e=>{state.cat=e.target.value;render();});
$('sort').addEventListener('change',e=>{state.sort=e.target.value;render();});
function setTier(t){state.tier=t;$('t-god').classList.toggle('on',t==='god');$('t-all').classList.toggle('on',t==='all');render();}
function go(sec){if(state.sec!==sec)history.pushState({sec:state.sec},'');state.sec=sec;state.shown=60;state.shuffleOn=(sec==='shuffle');render();}
function goBack(){const prev=history.state&&history.state.sec;if(prev){state.sec=prev;history.replaceState(null,'');state.shown=60;render();}else if(SECTIONS.some(s=>s.id===state.sec)){render();}}
window.addEventListener('popstate',e=>{if(e.state&&e.state.sec){state.sec=e.state.sec;render();}});
function render(){
  const sec=SECTIONS.find(s=>s.id===state.sec)||SECTIONS[0];
  $('sec-title').textContent=sec.name;
  $('sec-sub').textContent=sec.sub;
  $('backBtn').style.display=history.length>1?'inline-block':'none';
  document.querySelectorAll('#secbar button').forEach(b=>b.classList.toggle('on',b.dataset.sec===state.sec));
  let arr=secArr(state.sec);
  const q=state.q.trim().toLowerCase();
  if(state.cat!=='all'||q){arr=applyFilters(arr);}
  if(state.shuffleOn){const rnd=mulberry32(state.seed);for(let i=arr.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[arr[i],arr[j]]=[arr[j],arr[i]];}}
  $('sec-sub').textContent=sec.sub+' ｜ 本区 '+arr.length+' 支'+(state.shuffleOn?'（乱序）':'');
  $('grid').innerHTML=arr.slice(0,state.shown).map(cardHTML).join('')||'<div class="empty">这一区暂时空空如也。</div>';
  $('more').style.display=arr.length>state.shown?'inline-block':'none';
}
function moreGrid(){state.shown+=60;render();}
function renderSecbar(){
  $('secbar').innerHTML=SECTIONS.map(s=>`<button data-sec="${s.id}" class="${s.id===state.sec?'on':''}" onclick="go('${s.id}')">${s.name}</button>`).join('');
}
// init
$('k-god').textContent=DATA.meta.n_god;
$('k-all').textContent=DATA.meta.n_pool;
$('k-cov').textContent=DATA.meta.n_cov;
$('k-yr').textContent=(DATA.meta.yr_min||'—')+'–'+(DATA.meta.yr_max||'—');
$('k-r10').textContent=DATA.meta.n_r10;
$('k-ml').textContent=DATA.meta.n_ml;
$('k-queue').textContent=DATA.meta.n_queue;
$('k-ann').textContent=Object.keys(ann).length;
CATS.forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;$('cat').appendChild(o);});
renderSecbar();
render();
</script>
</body>
</html>
"""

html = TPL.replace("__DATA__", json.dumps(DATA, ensure_ascii=False)).replace("__DATE__", DATA["meta"]["date"])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"[done] -> {OUT} ({os.path.getsize(OUT) // 1024} KB)")
