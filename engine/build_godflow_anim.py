# -*- coding: utf-8 -*-
"""godflow 动画生成器 v3——三臂版。

A/B 臂（breadth run）: 5 流 5 列，逐跳网格节点带，前沿金环，枯章。
C 臂（deep run）:      深度×时间缎带——纵轴=层数，横轴=pubdate，金色链=神作纵深链，剪章=剪枝。
用法: python engine/build_godflow_anim.py [breadth_json] [deep_json]
输出: docs/personal/godflow-anim.html
"""
import glob
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "personal", "godflow-anim.html")

b_path = sys.argv[1] if len(sys.argv) > 1 else sorted(
    glob.glob(os.path.join(ROOT, "data", "flow_graph", "godflow_2*.json")), key=lambda p: p.replace("\\", "/"))[-1]
d_paths = sorted(glob.glob(os.path.join(ROOT, "data", "flow_graph", "godflowdeep_*.json")))
d_path = (sys.argv[2] if len(sys.argv) > 2 else (d_paths[-1] if d_paths else None))
bn_paths = sorted(glob.glob(os.path.join(ROOT, "data", "flow_graph", "godflowbnopad_*.json")))
bn_path = (sys.argv[3] if len(sys.argv) > 3 else (bn_paths[-1] if bn_paths else None))
rt_paths = sorted(glob.glob(os.path.join(ROOT, "data", "flow_graph", "godflowretro_*.json")))
rt_path = (sys.argv[4] if len(sys.argv) > 4 else (rt_paths[-1] if rt_paths else None))
breadth = json.load(open(b_path, encoding="utf-8"))
deep = json.load(open(d_path, encoding="utf-8")) if d_path else None
bnopad = json.load(open(bn_path, encoding="utf-8")) if bn_path else None
retro = json.load(open(rt_path, encoding="utf-8")) if rt_path else None
print(f"[anim] breadth = {b_path}")
print(f"[anim] deep    = {d_path}")
print(f"[anim] bnopad  = {bn_path}")
print(f"[anim] retro   = {rt_path}")

TPL = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>作品-推荐流 · 神作起流图遍历 · 动画演示</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#F7F2EB;color:#081F5C;font:14px/1.8 -apple-system,'PingFang SC','Microsoft YaHei',sans-serif}
.wrap{max-width:1300px;margin:0 auto;padding:26px 20px 60px}
.kick{display:inline-block;font-size:10.5px;letter-spacing:3px;color:#334EAC;border:1px dashed #7096D1;padding:3px 13px;border-radius:999px;margin-bottom:14px}
h1{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:26px;font-weight:900;letter-spacing:2px}
.lede{font-size:13px;color:#5B7EC2;margin:6px 0 16px}
.bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
button{background:#fffdf9;border:1px solid #7096D1;color:#334EAC;padding:5px 14px;font-size:12.5px;cursor:pointer;border-radius:3px;font-family:inherit}
button.on{background:#081F5C;color:#F7F2EB;border-color:#081F5C}
button:hover{background:#EFE8DA}
.hud{font-family:Georgia,serif;font-size:12.5px;color:#334EAC;display:flex;gap:16px;flex-wrap:wrap}
.hud b{color:#081F5C}
canvas{background:#F7F2EB;border:1px solid #E3DACB;display:block}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:#5B7EC2;margin:8px 0 4px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px;vertical-align:-1px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:16px}
.panel{background:#fffdf9;border:1px solid #E3DACB;padding:13px 15px}
.panel h3{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:15px;margin-bottom:8px;letter-spacing:1px}
table{border-collapse:collapse;width:100%;font-size:12px;background:transparent}
th{color:#334EAC;font-weight:600;border-bottom:1.5px solid #7096D1;padding:4px 7px;text-align:left;font-size:10.5px}
td{border-bottom:1px solid #E3DACB;padding:4.5px 7px;vertical-align:top}
td.num{font-family:Georgia,serif;white-space:nowrap}
.src{font-size:9.5px;color:#9DB6D8;letter-spacing:1.5px;text-transform:uppercase;margin-top:26px;border-top:1px solid #E3DACB;padding-top:9px}
.ku{color:#8A5A2B;font-weight:700}
.note{font-size:11px;color:#5B7EC2;margin-top:6px}
#retroView .flowBtn{display:block;width:100%;text-align:left;background:transparent;border:none;border-bottom:1px solid #E3DACB;padding:7px 9px;cursor:pointer;font-size:11.5px;color:#334EAC}
#retroView .flowBtn:hover{background:#EFE8DA}
#retroView .flowBtn.on{background:#081F5C;color:#F7F2EB}
#retroView .flowBtn .st{font-family:Georgia,serif;font-size:10px;color:#7096D1;display:block}
#retroView .flowBtn.on .st{color:#BAD6EB}
#retroView .rmeta{font-size:11.5px;color:#5B7EC2;border-bottom:1px solid #E3DACB;padding-bottom:8px;margin-bottom:6px}
#retroView .rmeta b{color:#081F5C}
#retroView .layer{border-bottom:1px solid #E3DACB;padding:7px 4px}
#retroView .layer .lt{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
#retroView .lnum{font-family:Georgia,serif;font-size:11px;color:#7096D1;width:34px;flex:0 0 auto}
#retroView .ldate{font-family:Georgia,serif;font-size:12.5px;color:#081F5C;width:64px;flex:0 0 auto}
#retroView .ltitle{flex:1 1 auto;min-width:200px}
#retroView .ltitle a{color:#8A6A14;font-weight:700;text-decoration:none;font-size:13px}
#retroView .ltitle a:hover{text-decoration:underline}
#retroView .lpct{font-family:Georgia,serif;font-size:11px;color:#334EAC;flex:0 0 auto}
#retroView .cbtn{background:transparent;border:1px solid #7096D1;color:#334EAC;font-size:10.5px;padding:1px 8px;cursor:pointer;border-radius:3px;flex:0 0 auto}
#retroView .cands{margin:5px 0 2px 44px;display:none}
#retroView .cands.open{display:block}
#retroView .cand{font-size:11.5px;color:#334EAC;padding:2.5px 0;border-bottom:1px dashed #EFE8DA}
#retroView .cand a{color:#334EAC;text-decoration:none}
#retroView .cand a:hover{text-decoration:underline}
#retroView .cand .cd{font-family:Georgia,serif;color:#7096D1;margin-right:7px}
#retroView .cand .picked{color:#8A6A14;font-weight:700}
#retroView .ku2{color:#8A5A2B;font-weight:700;font-size:12px;padding:8px 4px}
</style></head><body><div class="wrap">
<div class="kick">作品-推荐流 · godflow · 五臂对照 · 匿名通道 · 主账号零请求</div>
<h1>神作起流：定向 · 随机 · 纵深 · 回溯</h1>
<div class="lede">同一批评测口径。A 臂定向选 5（不足用优秀补位）；B 臂随机选 5；C 臂纵深——每层走至多 2 个神作、神=0 才剪；D 臂广度无补位——神作有几只用几只（≤5）、神&lt;3 剪；E 臂时光回溯——10 个新种子，神冗余时选发布最早的，专挖门类的经典层。</div>
<div class="bar">
  <button id="btnTarget" class="on" onclick="setArm('target')">A · 定向流</button>
  <button id="btnRandom" onclick="setArm('random')">B · 随机对照</button>
  <button id="btnDeep" onclick="setArm('deep')">C · 纵深流</button>
  <button id="btnBnopad" onclick="setArm('bnopad')">D · 无补位广度</button>
  <button id="btnRetro" onclick="setArm('retro')">E · 时光回溯</button>
  <button id="btnPlay" onclick="togglePlay()">暂停</button>
  <button onclick="setSpeed(1)">1x</button><button onclick="setSpeed(2)">2x</button><button onclick="setSpeed(4)">4x</button>
  <span class="hud" id="hud"></span>
</div>
<canvas id="cv" width="1260" height="740"></canvas>
<div id="retroView" style="display:none;grid-template-columns:250px 1fr;gap:14px;margin-bottom:8px">
  <div class="panel" style="padding:8px;max-height:720px;overflow:auto" id="retroSide"></div>
  <div class="panel" style="max-height:720px;overflow:auto" id="retroMain"></div>
</div>
<div class="legend" id="legendRow">
  <span><i class="dot" style="background:#B8912F"></i>神作</span>
  <span><i class="dot" style="background:#334EAC"></i>优秀（过渡节点）</span>
  <span><i class="dot" style="background:#7096D1"></i>一般</span>
  <span><i class="dot" style="background:#BAD6EB"></i>垃圾</span>
  <span><i class="dot" style="background:#E3DACB"></i>未证/无带</span>
  <span><i class="dot" style="background:none;border:1.5px solid #B8912F"></i>前沿选中</span>
  <span class="ku">枯 = 流尽 ｜ 剪 = 断流（纵深神=0 / 广度神&lt;3）</span>
</div>
<div class="grid2">
  <div class="panel"><h3>各流命运</h3><div id="fates"></div></div>
  <div class="panel"><h3>对照账本</h3><div id="yieldp"></div><div id="cmp"></div></div>
</div>
<div class="src">godflow · seeds = round2 user-confirmed gods · archive/related anonymous · breadth: __BFILE__ ｜ deep: __DFILE__ ｜ bnopad: __BNFILE__</div>
</div>
<script>
const RUN = __DATA__;
const TIERS = {"神作候选":"#B8912F","优秀候选":"#334EAC","一般候选":"#7096D1","垃圾候选":"#BAD6EB"};
const tierColor = t => TIERS[t] || "#E3DACB";
const tierR = t => t==="神作候选"?4.4:(t==="优秀候选"?3.2:(t==="一般候选"?2.5:2));
const cv=document.getElementById('cv'), ctx=cv.getContext('2d');
// DPR 感知：背板 = 逻辑尺寸 × devicePixelRatio，逻辑坐标系恒为 1260×740（修高分屏发糊）
const DPR=Math.min(window.devicePixelRatio||1,2);
const LW=1260, LH=740;
function fitCanvas(){
  const cw=(cv.parentElement?cv.parentElement.clientWidth:1260);
  const s=Math.min(1,cw/LW);
  cv.style.width=(LW*s)+'px';
  cv.style.height=(LH*s)+'px';
  cv.width=Math.round(LW*DPR);
  cv.height=Math.round(LH*DPR);
  ctx.setTransform(DPR*s,0,0,DPR*s,0,0);
}
window.addEventListener('resize',fitCanvas);
let arm='target', playing=true, speed=1, clock=0, last=performance.now();
const HOP_MS=2800;
function setArm(a){arm=a;
  ['Target','Random','Deep','Bnopad','Retro'].forEach(k=>{
    const key=k==='Bnopad'?'bnopad':(k==='Retro'?'retro':k.toLowerCase());
    document.getElementById('btn'+k).classList.toggle('on',a===key);});
  const isRetro=(a==='retro');
  document.getElementById('cv').style.display=isRetro?'none':'block';
  document.getElementById('legendRow').style.display=isRetro?'none':'flex';
  document.getElementById('retroView').style.display=isRetro?'grid':'none';
  renderTables();
  if(isRetro)renderRetro();
}
function togglePlay(){playing=!playing;document.getElementById('btnPlay').textContent=playing?'暂停':'播放';}
function setSpeed(s){speed=s;}
const fmtYM = t => {const d=new Date(t*1000);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0');};
// ---------- A/B 布局准备 ----------
function prepB(run){
  return run.flows.map(f=>{
    const byHop={};
    for(const n of f.nodes){const h=n.hop||0;(byHop[h]=byHop[h]||[]).push(n);}
    const hops=Object.keys(byHop).map(Number).sort((a,b)=>a-b);
    const edgesBySrc={};
    for(const e of f.edges){(edgesBySrc[e.src]=edgesBySrc[e.src]||[]).push(e.dst);}
    const nodeById={};
    for(const n of f.nodes){nodeById[n.bvid]=n;}
    const W=LW, n=run.flows.length, colW=W/n;
    const x0=n>1?fi():0, x1=0;
    function fi(){return run.flows.indexOf(f)*colW+16;}
    const gx0=run.flows.indexOf(f)*colW+16, gx1=(run.flows.indexOf(f)+1)*colW-16, gw=gx1-gx0;
    const rows={};
    const pitch = hops.length<=4?132:Math.floor(620/Math.max(1,hops.length-1));
    hops.forEach((h,ri)=>{
      const arr=byHop[h], nrows=Math.min(6,Math.max(2,Math.round(arr.length/34)+1));
      const cols=Math.ceil(arr.length/nrows), cw=gw/cols, ch=Math.max(6,Math.min(22,(pitch-10)/nrows));
      rows[h]={y:52+(h===0?0:14)+ri*pitch,arr,cols,cw,ch,nrows};
      arr.forEach((node,i)=>{
        node._x=gx0+(i%cols)*cw+cw/2;
        node._y=rows[h].y+Math.floor(i/cols)*ch+Math.min(11,ch/2);
      });
    });
    return {f,byHop,hops,edgesBySrc,nodeById,geom:{x0:gx0,x1:gx1,w:gw,cx:gx0+gw/2},rows};
  });
}
// ---------- C 布局准备：深度行 × pubdate 横轴 ----------
function prepD(run){
  if(!run)return [];
  const n=run.flows.length, colW=LW/n;
  return run.flows.map((f,fi)=>{
    const byHop={};
    for(const nd of f.nodes){const h=nd.hop||0;(byHop[h]=byHop[h]||[]).push(nd);}
    const hops=Object.keys(byHop).map(Number).sort((a,b)=>a-b);
    const gx0=fi*colW+18, gx1=(fi+1)*colW-18, gw=gx1-gx0;
    // 链 pubdate 跨度
    const chainPD=f.chain.filter(c=>c.pubdate).map(c=>c.pubdate);
    const tmin=Math.min(...chainPD), tmax=Math.max(...chainPD);
    const rows={};
    hops.forEach((h,ri)=>{
      const arr=byHop[h];
      rows[h]={y:64+ri*52,arr};
      arr.forEach(nd=>{
        nd._t = nd.pubdate || null;
        nd._x = nd._t ? gx0+gw*((nd._t-tmin)/Math.max(1,(tmax-tmin))) : gx0+gw*0.5;
        nd._y = rows[h].y;
      });
    });
    // 链节点坐标
    f.chain.forEach(c=>{const nd=f.nodes.find(x=>x.bvid===c.bvid); c._x=nd?nd._x:gx0+gw/2; c._y=rows[c.hop]?rows[c.hop].y:0;});
    return {f,byHop,hops,geom:{x0:gx0,x1:gx1,w:gw,cx:gx0+gw/2,tmin,tmax},rows};
  });
}
const PREP={target:prepB(RUN.breadth.arms.target),random:prepB(RUN.breadth.arms.random),
            deep:RUN.deep?prepD(RUN.deep):[],
            bnopad:RUN.bnopad?prepB(RUN.bnopad):[]};
// ---------- 绘制：A/B ----------
function drawB(P){
  const maxHops=Math.max(...P.map(p=>p.hops.length));
  const hopIdx=Math.min(Math.floor(clock/HOP_MS),maxHops-1);
  const phase=(clock/HOP_MS)%1;
  let nodes=0,gods=0,goods=0;
  P.forEach(p=>{
    const g=p.geom;
    ctx.textAlign='center';
    ctx.fillStyle='#081F5C';ctx.font='600 12px sans-serif';
    ctx.fillText((p.f.seed.bucket||'')+' ｜ '+(p.f.status==='dry'?'枯':p.f.status==='censored_depth'?'截断':p.f.status),g.cx,20);
    ctx.fillStyle='#5B7EC2';ctx.font='10px sans-serif';
    ctx.fillText((p.f.seed.title||'').slice(0,15),g.cx,36);
    p.hops.forEach(h=>{
      const r=p.rows[h];
      if(h===hopIdx){ctx.fillStyle='#081f5c07';ctx.fillRect(g.x0-8,r.y-10,g.w+16,Math.min(130,r.nrows*r.ch+16));}
      ctx.fillStyle='#9DB6D8';ctx.font='9px Georgia';ctx.textAlign='left';
      ctx.fillText('hop'+h,g.x0-13,r.y+4);
    });
    const active=h=>h<=hopIdx;
    p.hops.forEach(h=>{
      if(!active(h))return;
      const hd=fHop(p.f,h);
      const sel=new Set(hd?hd.selected||[]:[]);
      const parents=p.byHop[h].filter(n=>p.edgesBySrc[n.bvid]);
      const a0=h<hopIdx?1:Math.min(1,Math.max(0,(phase-0.55)/0.4));
      parents.forEach(par=>{
        (p.edgesBySrc[par.bvid]||[]).forEach(dst=>{
          const ch=p.nodeById[dst];
          if(!ch||!active(ch.hop))return;
          const isSel=sel.has(dst)&&ch.hop===h+1;
          const isDisc=(ch.tier==='神作候选'||ch.tier==='优秀候选');
          if(!(isSel||isDisc))return;
          ctx.strokeStyle=isSel?('rgba(184,145,47,'+(0.55*a0)+')'):'rgba(51,78,172,'+(0.10*a0)+')';
          ctx.lineWidth=isSel?1.2:0.6;
          ctx.beginPath();ctx.moveTo(par._x,par._y);ctx.lineTo(ch._x,ch._y);ctx.stroke();
        });
      });
    });
    p.hops.forEach(h=>{
      if(!active(h))return;
      const r=p.rows[h];
      const hd=fHop(p.f,h);
      const sel=new Set(hd?hd.selected||[]:[]);
      r.arr.forEach((n,i)=>{
        const spawn=h<hopIdx?1:Math.min(1,phase*2.6-i/(r.arr.length*0.9));
        if(spawn<=0)return;
        ctx.globalAlpha=(h===hopIdx?0.25+0.75*spawn:0.9);
        ctx.fillStyle=tierColor(n.tier);
        ctx.beginPath();ctx.arc(n._x,n._y,tierR(n.tier),0,7);ctx.fill();
        if(h===hopIdx&&sel.has(n.bvid)&&phase>0.5){
          const pu=0.5+0.5*Math.sin(phase*22);
          ctx.strokeStyle='#B8912F';ctx.lineWidth=1.5;ctx.globalAlpha=1;
          ctx.beginPath();ctx.arc(n._x,n._y,tierR(n.tier)+3.2+pu*1.4,0,7);ctx.stroke();
        }
        ctx.globalAlpha=1;
      });
    });
    if(p.f.status==='dry'||p.f.status==='pruned'){
      const hr=p.rows[p.hops[p.hops.length-1]];
      stamp(g.cx,hr.y+58,p.f.status==='pruned'?'剪':'枯');
    }
    nodes+=p.f.nodes.length;gods+=p.f.n_god_total;goods+=p.f.n_good_total||0;
  });
  const rq=(arm==='bnopad'&&RUN.bnopad?RUN.bnopad:RUN.breadth).meta.requests;
  document.getElementById('hud').innerHTML=
    '<b>hop</b> '+(hopIdx+1)+'/'+maxHops+' · <b>节点</b> '+nodes+' · <b>神作</b> '+gods+' · <b>优秀</b> '+goods+
    ' · <b>请求</b> '+(rq.related+(rq.tags||0));
  return maxHops;
}
function fHop(f,h){return f.hops.find(x=>x.hop===h&&x.n_neighbors!==undefined);}
function stamp(x,y,ch){
  ctx.save();ctx.translate(x,y);ctx.rotate(-0.14);
  ctx.strokeStyle='rgba(138,90,43,0.75)';ctx.lineWidth=1.6;ctx.strokeRect(-24,-18,48,36);
  ctx.fillStyle='#8A5A2B';ctx.font='700 22px "Kaiti SC","STKaiti","KaiTi",serif';ctx.textAlign='center';
  ctx.fillText(ch,0,8);ctx.restore();
}
// ---------- 绘制：C 纵深 ----------
function drawD(P){
  const maxHops=Math.max(...P.map(p=>p.hops.length));
  const hopIdx=Math.min(Math.floor(clock/HOP_MS),maxHops-1);
  const phase=(clock/HOP_MS)%1;
  let nodes=0,gods=0,deepMax=0;
  P.forEach(p=>{
    const g=p.geom;
    ctx.textAlign='center';
    ctx.fillStyle='#081F5C';ctx.font='600 12px sans-serif';
    ctx.fillText((p.f.seed.bucket||'')+' ｜ '+(p.f.status==='pruned'?'剪':p.f.status==='censored_depth'?'到底':'…'),g.cx,20);
    ctx.fillStyle='#5B7EC2';ctx.font='10px sans-serif';
    ctx.fillText((p.f.seed.title||'').slice(0,15),g.cx,36);
    // 时间轴刻度
    ctx.fillStyle='#9DB6D8';ctx.font='9px Georgia';
    ctx.fillText(fmtYM(p.geom.tmin),g.x0,50);ctx.textAlign='right';ctx.fillText(fmtYM(p.geom.tmax),g.x1,50);ctx.textAlign='center';
    p.hops.forEach(h=>{
      const r=p.rows[h];
      ctx.strokeStyle='#E3DACB';ctx.lineWidth=0.6;
      ctx.beginPath();ctx.moveTo(g.x0,r.y);ctx.lineTo(g.x1,r.y);ctx.stroke();
      ctx.fillStyle=h<=hopIdx?'#7096D1':'#D8CFC0';ctx.font='9px Georgia';ctx.textAlign='left';
      ctx.fillText('L'+h,g.x0-15,r.y+3);
    });
    const active=h=>h<=hopIdx;
    // 灰邻居
    p.hops.forEach(h=>{
      if(!active(h))return;
      const r=p.rows[h];
      r.arr.forEach((n,i)=>{
        const spawn=h<hopIdx?1:Math.min(1,phase*2.6-i/(r.arr.length*0.9));
        if(spawn<=0)return;
        ctx.globalAlpha=(h===hopIdx?0.2+0.5*spawn:0.55);
        ctx.fillStyle=tierColor(n.tier);
        ctx.beginPath();ctx.arc(n._x,n._y,n.tier==='神作候选'?3.4:2,0,7);ctx.fill();
        ctx.globalAlpha=1;
      });
    });
    // 神作纵深链
    const chn=p.f.chain.filter(c=>c.hop<=hopIdx&&c._y>0);
    ctx.strokeStyle='rgba(184,145,47,0.7)';ctx.lineWidth=1.4;
    ctx.beginPath();
    chn.forEach((c,i)=>{if(i===0)ctx.moveTo(c._x,c._y);else ctx.lineTo(c._x,c._y);});
    ctx.stroke();
    chn.forEach((c,i)=>{
      ctx.fillStyle='#B8912F';ctx.beginPath();ctx.arc(c._x,c._y,4.2,0,7);ctx.fill();
      if(c.hop===hopIdx&&phase>0.5){
        const pu=0.5+0.5*Math.sin(phase*22);
        ctx.strokeStyle='#B8912F';ctx.lineWidth=1.5;
        ctx.beginPath();ctx.arc(c._x,c._y,7.4+pu*1.6,0,7);ctx.stroke();
      }
    });
      if(p.f.status==='pruned'){
        const lastH=p.hops[p.hops.length-1];
        stamp(g.cx,p.rows[lastH].y+34,'剪');
      }
    nodes+=p.f.nodes.length;gods+=p.f.n_god_total;deepMax=Math.max(deepMax,chn.length?p.f.hops.filter(h=>h.n_neighbors!==undefined).length:0);
  });
  const rq=RUN.deep.meta.requests;
  document.getElementById('hud').innerHTML=
    '<b>层</b> '+(hopIdx+1)+'/'+maxHops+' · <b>节点</b> '+nodes+' · <b>神作</b> '+gods+' · <b>请求</b> '+rq.related+
    ' · 横轴 = 发布年月（各流链跨度归一）';
  return maxHops;
}
// ---------- E 臂：回溯定向（DOM 交互视图） ----------
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function fmtW(v){return v>=10000?(v/10000).toFixed(1)+'万':String(v);}
function med(a){const b=[...a].sort((x,y)=>x-y);return b[Math.floor(b.length/2)];}
let retroSel=0;
function retroHops(f){return f.hops.filter(h=>h.n_neighbors!==undefined);}
function retroSpan(f){
  const ch=retroHops(f).flatMap(h=>h.selected||[]).filter(s=>s.pubdate).map(s=>s.pubdate);
  if(ch.length<2)return {span:'—',drift:'—',dcls:''};
  const span=fmtYM(Math.min(...ch))+' ~ '+fmtYM(Math.max(...ch));
  let drift='—',dcls='';
  if(ch.length>=4){
    const dm=Math.round((med(ch.slice(-3))-med(ch.slice(0,3)))/2592000);
    if(dm<=-2){drift='回溯 ↘ 约'+(-dm)+' 个月';dcls='ku2';}
    else if(dm>=2){drift='向新 ↗ +'+dm+' 个月';dcls='';}
    else{drift='走平 →';dcls='';}
  }
  return {span,drift,dcls};
}
function renderRetro(){
  if(!RUN.retro)return;
  const F=RUN.retro.flows;
  let side='';
  F.forEach((f,i)=>{
    const hops=retroHops(f);
    side+='<button class="flowBtn'+(i===retroSel?' on':'')+'" onclick="RETRO.show('+i+')">'
      +esc((f.seed.bucket||'')+' · '+(f.seed.title||'').slice(0,15))
      +'<span class="st">'+hops.length+'层 · 神'+f.n_god_total+' · '+(f.status==='pruned'?'剪@L'+f.prune.hop:(f.status==='censored_depth'?'到顶':'…'))+'</span></button>';
  });
  document.getElementById('retroSide').innerHTML=side;
  showRetroFlow();
}
function showRetroFlow(){
  if(!RUN.retro)return;
  const f=RUN.retro.flows[retroSel];
  const hops=retroHops(f);
  const sp=retroSpan(f);
  let main='<div class="rmeta"><b>种子</b> <a href="https://www.bilibili.com/video/'+f.seed.bvid+'" target="_blank" rel="noopener">'+esc(f.seed.title||'')+'</a>（'+esc(f.seed.bucket||'')+'） · <b>状态</b> '
    +(f.status==='pruned'?'<span class="ku2">剪 · '+esc(f.prune.reason)+'</span>':f.status)
    +' · <b>深度</b> '+hops.length+' · <b>神作</b> '+f.n_god_total+' · <b>链跨度</b> '+sp.span+' · <b>漂移</b> <span class="'+sp.dcls+'">'+sp.drift+'</span>'
    +'<br>规则：每层从神作候选里选<b>发布最早</b>的 2 个。金色 = 被选中的回溯节点；点「候选」展开当层完整选择现场——看它放弃了谁、选了谁。</div>';
  hops.forEach(h=>{
    const sels=h.selected||[];
    const d0=sels.length&&sels[0].pubdate?fmtYM(sels[0].pubdate):'—';
    main+='<div class="layer"><div class="lt"><span class="lnum">L'+h.hop+'</span><span class="ldate">'+d0+'</span>';
    if(h.pruned){main+='<span class="ku2">剪 · '+esc(h.pruned)+'</span>';}
    sels.forEach(s=>{
      main+='<span class="ltitle"><a href="https://www.bilibili.com/video/'+s.bvid+'" target="_blank" rel="noopener">'+esc(s.title)+'</a></span>'
        +'<span class="lpct">pct '+(s.coin_pct*100).toFixed(1)+'% · '+fmtW(s.view)+'</span>';
    });
    if(!h.pruned&&h.n_gods>sels.length){
      main+='<button class="cbtn" onclick="RETRO.tg('+retroSel+','+h.hop+')">候选 '+h.n_gods+' ▸</button>';
    }else if(!h.pruned){
      main+='<span class="lpct">候选 '+h.n_gods+'</span>';
    }
    main+='</div><div class="cands" id="cands_'+retroSel+'_'+h.hop+'">';
    (h.candidates||[]).forEach((c,i)=>{
      const picked=sels.some(s=>s.bvid===c.bvid);
      main+='<div class="cand"><span class="cd">'+(c.pubdate?fmtYM(c.pubdate):'—')+'</span>'
        +'<a href="https://www.bilibili.com/video/'+c.bvid+'" target="_blank" rel="noopener" class="'+(picked?'picked':'')+'">'+(picked?'★ ':'')+esc(c.title)+'</a>'
        +' · pct '+(c.coin_pct*100).toFixed(1)+'% · '+fmtW(c.view)+'</div>';
    });
    main+='</div></div>';
  });
  document.getElementById('retroMain').innerHTML=main;
}
const RETRO={show(i){retroSel=i;renderRetro();},tg(fi,h){const el=document.getElementById('cands_'+fi+'_'+h);if(el)el.classList.toggle('open');}};
function draw(){
  if(arm==='retro'){requestAnimationFrame(draw);return;}
  const now=performance.now();
  if(playing)clock+=(now-last)*speed;
  last=now;
  ctx.clearRect(0,0,LW,LH);
  if(arm==='deep'){drawD(PREP.deep);}
  else{drawB(PREP[arm]);}
  requestAnimationFrame(draw);
}
// ---------- 表格 ----------
function renderTables(){
  const fa=document.getElementById('fates');
  if(arm==='retro'&&RUN.retro){
    let html='<table><tr><th>种子（门类）</th><th>深度</th><th>神作</th><th>链跨度</th><th>漂移</th><th>剪因</th></tr>';
    RUN.retro.flows.forEach((f,i)=>{
      const hops=retroHops(f);
      const sp=retroSpan(f);
      html+='<tr onclick="RETRO.show('+i+')" style="cursor:pointer"><td>'+esc((f.seed.bucket||'')+' · '+(f.seed.title||'').slice(0,14))+'</td><td class=num>'+hops.length+'</td><td class=num>'+f.n_god_total+'</td><td class=num>'+sp.span+'</td><td class="'+sp.dcls+'">'+sp.drift+'</td><td>'+(f.prune?esc(f.prune.reason):'—')+'</td></tr>';
    });
    const rq=RUN.retro.meta.requests;
    const nd=RUN.retro.flows.reduce((s,f)=>s+f.nodes.length,0);
    const ng=RUN.retro.flows.reduce((s,f)=>s+f.n_god_total,0);
    fa.innerHTML=html+'</table>';
    document.getElementById('yieldp').innerHTML='<div class="note">E 臂：前沿 2、神=0 剪、神冗余时选<b>发布最早</b>的神作——把「选中即回溯」做成机制。点左表任意一行跳转到对应流的交互时间线。</div>';
    document.getElementById('cmp').innerHTML='<div class="note"><b>回溯总账</b> —— 10 流 · 节点 <b>'+nd+'</b> · 神作 <b>'+ng+'</b> · 请求 '+rq.related+' · 点各流时间线里的「候选」可展开当层完整选择现场，视频标题可点击直达。</div>';
    return;
  }
  if(arm==='bnopad'&&RUN.bnopad){
    let html='<table><tr><th>种子（门类）</th><th>状态</th><th>深度</th><th>神作</th><th>剪因</th></tr>';
    PREP.bnopad.forEach(p=>{
      const f=p.f, hops=f.hops.filter(h=>h.n_neighbors!==undefined);
      const st=f.status==='pruned'?'<span class="ku">剪</span>':(f.status==='censored_depth'?'到底(8层)':f.status==='censored_budget'?'预算截断':f.status);
      html+='<tr><td>'+(f.seed.bucket||'')+' · '+(f.seed.title||'').slice(0,13)+'</td><td>'+st+'</td><td class=num>'+hops.length+'</td><td class=num>'+f.n_god_total+'</td><td>'+(f.dry?f.dry.reason:'—')+'</td></tr>';
    });
    fa.innerHTML=html+'</table>';
    function ph(a){const m={};const src=a==='bnopad'?RUN.bnopad:RUN.breadth.arms[a];
      (src||{flows:[]}).flows.forEach(f=>f.hops.forEach(h=>{if(h.n_neighbors!==undefined)m[h.hop]=(m[h.hop]||0)+h.n_gods;}));return m;}
    const gt=ph('target'),gd=ph('bnopad');
    const hops=[...new Set([...Object.keys(gt),...Object.keys(gd)])].map(Number).sort((a,b)=>a-b);
    const mx=Math.max(1,...hops.map(h=>Math.max(gt[h]||0,gd[h]||0)));
    let bars='<table><tr><th>hop</th><th>A神</th><th>D神</th><th>产量对照</th></tr>';
    hops.forEach(h=>{
      const wA=Math.round(110*(gt[h]||0)/mx),wD=Math.round(110*(gd[h]||0)/mx);
      bars+='<tr><td class=num>'+h+'</td><td class=num>'+(gt[h]||0)+'</td><td class=num>'+(gd[h]||0)+'</td><td><span style="display:inline-block;height:9px;width:'+wA+'px;background:#B8912F"></span><span style="display:inline-block;height:9px;width:'+wD+'px;background:#D0E3FF;margin-left:3px"></span></td></tr>';
    });
    document.getElementById('yieldp').innerHTML=bars+'</table><div class="note">金条 = A 定向（带补位） · 浅蓝 = D 无补位 · A 与 D 唯一差异 = 优秀补位</div>';
    function tot(src,k){return (src||{flows:[]}).flows.reduce((s,f)=>s+(f.nodes?f.nodes.filter(n=>n.tier===k).length:0),0);}
    function stN(src,st){return (src||{flows:[]}).flows.filter(f=>f.status===st).length;}
    document.getElementById('cmp').innerHTML='<div class="note"><b>四臂总账</b> —— A 神 <b>'+tot(RUN.breadth.arms.target,'神作候选')+'</b> / B 神 '+tot(RUN.breadth.arms.random,'神作候选')+' / C 神 '+(RUN.deep?RUN.deep.flows.reduce((s,f)=>s+f.n_god_total,0):0)+' / D 神 <b>'+tot(RUN.bnopad,'神作候选')+'</b> ｜ D 剪流 '+stN(RUN.bnopad,'pruned')+' / 到底 '+stN(RUN.bnopad,'censored_depth')+'<br><b>补位价值</b> = A − D：同种子同神作优先，唯一差异是优秀补位——差异量即补位引入的探索量</div>';
    return;
  }
  if(arm==='deep'&&RUN.deep){
    let html='<table><tr><th>种子（门类）</th><th>状态</th><th>深度</th><th>神作</th><th>链时间跨度</th><th>剪因</th></tr>';
    PREP.deep.forEach(p=>{
      const f=p.f, hops=f.hops.filter(h=>h.n_neighbors!==undefined);
      const ch=f.chain.filter(c=>c.pubdate);
      const span=ch.length?(ch.length>1?fmtYM(Math.min(...ch.map(c=>c.pubdate)))+' ~ '+fmtYM(Math.max(...ch.map(c=>c.pubdate))):fmtYM(ch[0].pubdate)):'—';
      html+='<tr><td>'+(f.seed.bucket||'')+' · '+(f.seed.title||'').slice(0,13)+'</td><td>'+(f.status==='pruned'?'<span class="ku">剪</span>':f.status==='censored_depth'?'到底(15层)':f.status)+'</td><td class=num>'+hops.length+'</td><td class=num>'+f.n_god_total+'</td><td class=num>'+span+'</td><td>'+(f.prune?f.prune.reason:'—')+'</td></tr>';
    });
    fa.innerHTML=html+'</table>';
    document.getElementById('yieldp').innerHTML='<div class="note">纵深臂只走神作：链 = 金色折线，横轴 = 发布年月。链向右漂 = 算法把老神作链向新神作；向左 = 向经典回溯；摊平 = 跨年代通吃。</div>';
    const alive=PREP.deep.filter(p=>p.f.status==='censored_depth').length;
    document.getElementById('cmp').innerHTML='<div class="note"><b>纵深总账</b> —— 到底(15层) <b>'+alive+'</b>/5 条 · 剪 '+PREP.deep.filter(p=>p.f.status==='pruned').length+' 条 · 各流最深链见左表</div>';
    return;
  }
  const P=PREP[arm];
  let html='<table><tr><th>种子（门类）</th><th>状态</th><th>神作</th><th>优秀</th><th>枯因</th></tr>';
  P.forEach(p=>{
    const f=p.f;
    html+='<tr><td>'+(f.seed.bucket||'')+' · '+(f.seed.title||'').slice(0,13)+'</td><td>'+(f.status==='dry'?'<span class="ku">枯</span>':f.status==='censored_depth'?'深度截断':f.status)+'</td><td class=num>'+f.n_god_total+'</td><td class=num>'+(f.n_good_total||0)+'</td><td>'+(f.dry?f.dry.reason:'—')+'</td></tr>';
  });
  fa.innerHTML=html+'</table>';
  function perHop(a,key){const m={};(RUN.breadth.arms[a]||{flows:[]}).flows.forEach(f=>f.hops.forEach(h=>{if(h.n_neighbors!==undefined)m[h.hop]=(m[h.hop]||0)+h[key];}));return m;}
  const gt=perHop('target','n_gods'),gr=perHop('random','n_gods');
  const hops=[...new Set([...Object.keys(gt),...Object.keys(gr)])].map(Number).sort((a,b)=>a-b);
  const mx=Math.max(1,...hops.map(h=>Math.max(gt[h]||0,gr[h]||0)));
  let bars='<table><tr><th>hop</th><th>A神</th><th>B神</th><th>产量对照</th></tr>';
  hops.forEach(h=>{
    const wA=Math.round(110*(gt[h]||0)/mx),wB=Math.round(110*(gr[h]||0)/mx);
    bars+='<tr><td class=num>'+h+'</td><td class=num>'+(gt[h]||0)+'</td><td class=num>'+(gr[h]||0)+'</td><td><span style="display:inline-block;height:9px;width:'+wA+'px;background:#B8912F"></span><span style="display:inline-block;height:9px;width:'+wB+'px;background:#D0E3FF;margin-left:3px"></span></td></tr>';
  });
  document.getElementById('yieldp').innerHTML=bars+'</table><div class="note">金条 = A 定向 · 浅蓝 = B 随机 · 数值 = 该 hop 邻居中判神作数（合计）</div>';
  function tot(a,k){return (RUN.breadth.arms[a]||{flows:[]}).flows.reduce((s,f)=>s+(f.nodes?f.nodes.filter(n=>n.tier===k).length:0),0);}
  function dryN(a){return (RUN.breadth.arms[a]||{flows:[]}).flows.filter(f=>f.status==='dry').length;}
  document.getElementById('cmp').innerHTML='<div class="note"><b>总账</b> —— A 臂：神作 <b>'+tot('target','神作候选')+'</b> / 优秀 '+tot('target','优秀候选')+' / 枯流 '+dryN('target')+' ｜ B 臂：神作 <b>'+tot('random','神作候选')+'</b> / 优秀 '+tot('random','优秀候选')+' / 枯流 '+dryN('random')+' ｜ C 纵深：神作链见「C · 纵深流」页</div>';
}
fitCanvas();
draw();renderTables();
</script></body></html>
"""

data = {"breadth": breadth, "deep": deep, "bnopad": bnopad, "retro": retro}
html = (TPL.replace("__DATA__", json.dumps(data, ensure_ascii=False))
           .replace("__BFILE__", os.path.basename(b_path))
           .replace("__DFILE__", os.path.basename(d_path) if d_path else "（未接入）")
           .replace("__BNFILE__", os.path.basename(bn_path) if bn_path else "（未接入）")
           .replace("__RTFILE__", os.path.basename(rt_path) if rt_path else "（未接入）"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"[done] -> {OUT} ({os.path.getsize(OUT) // 1024} KB)")
