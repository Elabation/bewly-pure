# -*- coding: utf-8 -*-
"""神作用户流 · 神作端名录——流筛出的全部神作（CBI≥3），按 CBI 降序，供 Elabation 人审"""
import html
import json
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
OUT = os.path.join(ROOT, "docs", "personal", "flow-god-review.html")
sys.path.insert(0, os.path.join(ROOT, "engine"))
from cbi_scale import tier_of  # noqa: E402

FILES = [("臂①", "favmine_20260903_102226.json"),
         ("流2", "favmine_flowH2_20260903_113231.json"),
         ("流3", "favmine_flowH3_20260903_114437.json"),
         ("流4", "favmine_flowH4_20260903_115415.json"),
         ("中带", "favmine_flowH2_20260903_135254.json"),
         ("工程", "favmine_flowH2_20260903_120735.json"),
         ("臂②", "favmine_20260903_020202.json"),
         ("臂③", "favmine_20260903_105503.json")]

prov = defaultdict(set)
rec = {}
inflow = defaultdict(set)
for tag, fn in FILES:
    p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
    for v in (p.get("videos") or []):
        if (v.get("view") or 0) >= 3000 and v.get("bvid"):
            prov[v["bvid"]].add(tag)
            rec[v["bvid"]] = v
            if v.get("from_user"):
                inflow[v["bvid"]].add(v["from_user"])

# Elabation 已判（擦边子报告的判定交叉引用）
elab = {}
vp = os.path.join(MINE, "elabation_verdicts.json")
if os.path.exists(vp):
    ej = json.load(open(vp, encoding="utf-8"))
    elab.update(ej.get("rows") or {})
    elab.update(ej.get("cards") or {})

gods = []
for b, v in rec.items():
    view = v.get("view") or 0
    t = tier_of(v.get("cbi", 0), view)
    if t == "high":
        st = v.get("stat") or {}
        view_ = max(1, view)
        gods.append({"bvid": b, "cbi": round(v.get("cbi", 0), 2), "view": view,
                     "coin": st.get("coin", 0) / view_, "fav": st.get("favorite", 0) / view_,
                     "like": st.get("like", 0) / view_, "inflow": len(inflow.get(b, set())),
                     "prov": "、".join(sorted(prov[b])), "title": v.get("title") or "?", "tier": t})
gods.sort(key=lambda g: -g["cbi"])

rows = []
for i, g in enumerate(gods, 1):
    shape = "档案型" if g["fav"] > g["coin"] else "表态型"
    ev = elab.get(g["bvid"], "")
    ev_show = (ev[:28] + "…") if len(ev) > 28 else ev
    rows.append(
        f'<tr><td class="num">{i}</td><td class="num"><b>{g["cbi"]:.2f}</b></td>'
        f'<td class="num">{g["inflow"]}</td><td>{g["prov"]}</td>'
        f'<td class="num">{g["view"]:,}</td>'
        f'<td>{g["coin"]:.2%} / {g["fav"]:.2%} / {g["like"]:.2%}</td><td>{shape}</td>'
        f'<td><a href="https://www.bilibili.com/video/{g["bvid"]}" target="_blank">'
        f'{html.escape(g["title"][:46])}</a></td>'
        f'<td class="num">{html.escape(ev_show) if ev_show else "—"}</td>'
        f'<td class="blank">＿＿＿</td></tr>')

TPL = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>神作用户流 · 神作端名录</title>
<style>
:root{--ink:#081F5C;--data1:#334EAC;--data2:#7096D1;--data3:#BAD6EB;--paper:#F7F2EB;--shadow:#E3DACB;--sub:#5B7EC2;--dim:#9FB6D4}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font:14px/1.9 -apple-system,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 22px 80px}
header.hero{padding:50px 0 22px;border-bottom:1px solid var(--shadow)}
.kicker{font-size:11px;letter-spacing:4px;color:var(--data1);border:1px dashed var(--data2);display:inline-block;padding:4px 14px;border-radius:999px;margin-bottom:18px}
h1{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:34px;font-weight:900;letter-spacing:2px}
.hero .lede{font-size:14px;color:var(--sub);margin-top:10px}
.kpirow{display:flex;gap:14px;flex-wrap:wrap;margin:16px 0}
.kpi{flex:1 1 150px;background:#EFE8DA;padding:12px 15px}
.kpi .n{font-family:Georgia,serif;font-size:24px;color:var(--ink)}
.kpi .d{font-size:11.5px;color:var(--sub);line-height:1.5;margin-top:2px}
nav{position:sticky;top:0;background:var(--paper);border-bottom:1px solid var(--shadow);z-index:9;font-size:12px;padding:9px 0}
table{border-collapse:collapse;width:100%;margin:16px 0;font-size:12.5px;background:#fdfcf9}
th{color:var(--data1);font-weight:600;border-bottom:2px solid var(--data2);padding:7px 8px;text-align:left;font-size:11.5px;white-space:nowrap}
td{border-bottom:1px solid var(--shadow);padding:6px 8px;vertical-align:top}
td.num{font-family:Georgia,serif;white-space:nowrap}
td.blank{color:#C9C0B0;letter-spacing:2px}
tr td:first-child{color:var(--sub)}
p{margin:10px 0}
.note{color:var(--sub);font-size:12.5px}
.foot{padding:30px 0 10px;font-size:11.5px;color:var(--dim);letter-spacing:1px}
</style></head>
<body><div class="wrap">
<header class="hero">
  <div class="kicker">神作用户流 · 神作端 · 人审材料</div>
  <h1>神作端名录</h1>
  <div class="lede">流（臂① → 流2 → 流3 → 流4 → 中带实验）筛选出的全部神作（CBI≥3、播放≥3000），
  按 CBI 降序。来源列 = 该视频被哪些层收获。汇流列 = 独立收藏者数。已判列 = 你在擦边子报告里
  已给出的判定（有则回显）。末列留白。</div>
</header>
<nav><a href="cbi-edge-review.html">← 擦边子报告</a></nav>
<div class="kpirow">
  <div class="kpi"><div class="n">__NGOD__</div><div class="d">神作总数（CBI≥3）</div></div>
  <div class="kpi"><div class="n">__NMULTI__</div><div class="d">汇流神作（入度≥2）</div></div>
  <div class="kpi"><div class="n">__NCBI10__</div><div class="d">CBI≥10 的极端神作</div></div>
  <div class="kpi"><div class="n">__NJUDGED__</div><div class="d">你已判过（回显）</div></div>
</div>
<p class="note">人审动线：从 #1 往下看，重点盯<b>高 CBI 低汇流</b>的行（CBI 高但只有 1 个收藏者——
这种最可能是「单人口味虚高」）；汇流≥2 的行是被多个独立用户共同指向的，可信度天然更高。
「已判」列回显你在擦边子报告的判定，判过的不用重看。</p>
<table><tr><th>#</th><th>CBI</th><th>汇流</th><th>来源</th><th>播放</th><th>币/藏/赞 每播放</th><th>形态</th><th>标题</th><th>已判</th><th>我的判定</th></tr>
__ROWS__
</table>
<footer class="foot">神作端名录 · 本地存档 · 不上传 · 只统计视频不统计人</footer>
</div></body></html>
"""

doc = (TPL.replace("__NGOD__", str(len(gods)))
          .replace("__NMULTI__", str(sum(1 for g in gods if g["inflow"] >= 2)))
          .replace("__NCBI10__", str(sum(1 for g in gods if g["cbi"] >= 10)))
          .replace("__NJUDGED__", str(sum(1 for g in gods if elab.get(g["bvid"]))))
          .replace("__ROWS__", "".join(rows)))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(doc)
print(f"[god] 神作 {len(gods)} | 汇流≥2 {sum(1 for g in gods if g['inflow']>=2)} | "
      f"CBI≥10 {sum(1 for g in gods if g['cbi']>=10)} | 已判回显 {sum(1 for g in gods if elab.get(g['bvid']))} -> {OUT}")
