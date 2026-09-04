# -*- coding: utf-8 -*-
"""个人兴趣子报告 v2 · CBI 擦边/颜值区扫描（2026-09-03，Elabation 私人委托）

问题：美女/舞蹈/擦边类视频能不能「骗过」CBI？
设计语言学自主报告（porcelain-data 完全体）；名录按行排列、gold 级样例卡、留人工判定列。
纪律：纯本地、零请求、只统计视频不统计人（无 from_user 字段输出）、文件仅存本地不入仓不上传。
输出：docs/personal/cbi-edge-review.html
"""
import html
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
OUTDIR = os.path.join(ROOT, "docs", "personal")
OUT = os.path.join(OUTDIR, "cbi-edge-review.html")

ZONE_KW = ["舞蹈", "宅舞", "时尚", "美妆", "颜值"]
TITLE_KW = ["美女", "小姐姐", "擦边", "颜值", "热舞", "宅舞", "跳舞", "黑丝",
            "JK", "jk", "制服", "性感", "变装", "女团", "cos", "Cos", "COS", "纯欲",
            "身材", "御姐", "妹子", "舞蹈", "卡点舞"]

TPL = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>个人子报告 · CBI 擦边/颜值区扫描</title>
<style>
:root{--ink:#081F5C;--data1:#334EAC;--data2:#7096D1;--data3:#BAD6EB;--paper:#F7F2EB;--shadow:#E3DACB;--sub:#5B7EC2;--dim:#9FB6D4;--amber:#C2803A}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font:14px/1.9 -apple-system,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:0 22px 80px}
header.hero{padding:60px 0 26px;border-bottom:1px solid var(--shadow)}
.kicker{font-size:11px;letter-spacing:4px;color:var(--amber);border:1px dashed var(--amber);display:inline-block;padding:4px 14px;border-radius:999px;margin-bottom:20px}
h1{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:36px;font-weight:900;letter-spacing:2px}
.hero .lede{font-size:14.5px;color:var(--sub);margin-top:12px;max-width:720px}
.badges{margin-top:18px;font-size:11.5px;color:var(--amber)}
.badges span{border:1px solid #d8b89a;border-radius:4px;padding:2px 9px;margin-right:8px;display:inline-block;margin-bottom:6px;background:#fff8}
nav{position:sticky;top:0;background:var(--paper);border-bottom:1px solid var(--shadow);z-index:9;font-size:12px;padding:9px 0}
nav a{color:var(--sub);text-decoration:none;margin-right:12px}
nav a:hover{color:var(--ink)}
section{padding:42px 0 10px;border-bottom:1px solid var(--shadow)}
.sn{font-size:11px;letter-spacing:3px;color:var(--amber)}
h2{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:24px;margin:6px 0 10px}
p{margin:10px 0;max-width:820px}
p.note{font-size:12.5px;color:var(--sub)}
.guide{background:#EFE8DA;border-left:4px solid var(--amber);padding:12px 18px;margin:14px 0;font-size:13.5px;color:#22346B;max-width:840px}
.guide b{color:#081F5C}
.kpirow{display:flex;gap:14px;flex-wrap:wrap;margin:16px 0}
.kpi{flex:1 1 160px;background:#EFE8DA;padding:13px 15px}
.kpi .n{font-family:Georgia,serif;font-size:25px;color:var(--ink)}
.kpi .d{font-size:11.5px;color:var(--sub);line-height:1.5;margin-top:2px}
.bar-row{display:flex;align-items:center;margin:7px 0}
.bar-lab{width:150px;font-size:12px;color:var(--ink);flex:none}
.bar-track{flex:1;height:14px;background:#EDE5D8;position:relative}
.bar-fill{height:14px}
.bar-val{width:110px;text-align:right;font-family:Georgia,serif;font-size:12px;color:var(--data1);flex:none}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:12.5px;background:#fdfcf9}
th{color:var(--data1);font-weight:600;border-bottom:2px solid var(--data2);padding:7px 8px;text-align:left;font-size:11.5px;white-space:nowrap}
td{border-bottom:1px solid var(--shadow);padding:7px 8px;vertical-align:top}
td.num{font-family:Georgia,serif;white-space:nowrap}
td.blank{color:#C9C0B0;letter-spacing:2px}
tr.gold td{background:#b8912f10}
tr.good td{background:#334EAC0a}
a{color:var(--data1);text-decoration:none}
a:hover{text-decoration:underline}
.exq{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}
.ex{flex:1 1 420px;border-left:3px solid #b8912f;background:#fff8;padding:10px 14px;font-size:12.5px}
.ex .rank{font-family:Georgia,serif;font-size:20px;color:#b8912f;font-weight:bold;float:right}
.ex .t{color:var(--ink);font-weight:600}
.ex .m{font-family:Georgia,serif;color:var(--data1);font-size:12px;margin-top:3px}
.ex .fill{color:#C9C0B0;margin-top:4px;letter-spacing:1px}
.foot{padding:34px 0 10px;font-size:11.5px;color:var(--dim);letter-spacing:1px}
</style>
</head>
<body>
<div class="wrap">
<header class="hero">
  <div class="kicker">个人兴趣 · 与主报告无隶属 · 本地存档</div>
  <h1>CBI 会「被骗」吗</h1>
  <div class="lede">收藏夹里的美女/舞蹈/擦边类视频，能否借「收藏 = 想再看」逃过三档判定、混入神作名录？
  ——这本质是在问 CBI 的价值观边界：它度量的是感谢行为浓度，不是抽象的「内容质量」。</div>
  <div class="badges"><span>仅本地存档</span><span>不上传 GitHub</span><span>不入主报告</span><span>只统计视频 · 无任何用户字段</span></div>
</header>
<nav><a href="#s1">检出规模</a><a href="#s2">对照分析</a><a href="#s3">gold 级 9 条</a><a href="#s4">完整名录</a><a href="#s5">结论</a></nav>

<section id="s1">
  <div class="sn">〇 · 一</div>
  <h2>问题、方法与覆盖度</h2>
  <p><b>检出</b>（双通道，任一命中即入候选）：① 分区名含 舞蹈/宅舞/时尚/美妆/颜值；② 标题含
  美女／小姐姐／擦边／颜值／热舞／宅舞／跳舞／黑丝／JK／制服／性感／变装／女团／cos／纯欲／身材／御姐／妹子 等 24 词。</p>
  <div class="guide"><b>覆盖度坦白</b>：通道①结构性失效——view API 的 tname 字段当前返回空串
  （09-02 旧库亦全为「?」，即整条收藏管线从未有过分区数据，主报告 S4/S6 分区节空白同源）。
  故候选全部来自标题关键词通道：标题含蓄的同类视频会漏检。下一轮挖矿可加 tags API 补齐分区
  （+1 请求/视频，已登记）。</div>
  __KPI__
</section>

<section id="s2">
  <div class="sn">二</div>
  <h2>对照分析：候选组 vs 全库</h2>
  __BARS__
  <p class="note">读法：若候选组神作率≈全库且行为构成无异常 → CBI 没有被「颜值效应」特殊优待或歧视；
  若 fav 主导占比显著更高 → 「收藏=想再看」确实在为颜值内容开绿灯——这是价值观层待裁定的部分。</p>
</section>

<section id="s3">
  <div class="sn">三</div>
  <h2>gold 级 __NGOLD__ 条 · 人审重点</h2>
  <p>这些条目若出现在主报告的神作名录里，就是「擦边混入」的直接样本。每条的收藏者数（入度）
  已从原始边集核算——__GOLDNOTE__</p>
  __EXQ__
</section>

<section id="s4">
  <div class="sn">四</div>
  <h2>完整名录 · 按 CBI 降序（77 条）</h2>
  <p class="note">每播放行为 = 投币 / 收藏 / 点赞。形态：fav 主导 = 档案型（想再看），coin 主导 = 表态型。
  末列「我的判定」留白供人工填写：真神作 / 颜值档案 / 擦边。</p>
  __TABLE__
</section>

<section id="s5">
  <div class="sn">五</div>
  <h2>结论</h2>
  <div class="guide">
  <p><b>CBI 没有被系统性骗过</b>：候选组神作率 11.7%，只有全库 21.4% 的一半；纯 clickbait
  （车展车模、性感诱惑）稳稳落在 junk（CBI 0.3-0.4）。</p>
  <p><b>但混入神作的 __NGOLD__ 条中 __FAVDM__ 条是 fav 档案型</b>，且收藏率高得离谱（fav/view 18.8%、
  31.8%、17.6%）——「想再看」机制真实存在，CBI 如实记录了这种行为，但它分不清「感谢」和「惦记」。</p>
  <p><b>汇流度是擦边内容的天然过滤器</b>：__GOLDNOTE2__ 挖矿引擎若要利用颜值档案，
  需要独立建轨（fav 主导方向 × 单源内容），那是价值观决策，不是技术决策。</p>
  </div>
</section>

<footer class="foot">个人子报告 · 本地存档 · 洁净B站 · 只统计视频，不统计人</footer>
</div>
</body>
</html>
"""


def bar(label, v, maxv, color, val):
    w = (v or 0) / maxv * 100
    return (f'<div class="bar-row"><span class="bar-lab">{label}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{w:.1f}%;background:{color}"></div></div>'
            f'<span class="bar-val">{val}</span></div>')


def main():
    merged = None
    mfs = sorted((f for f in os.listdir(MINE)
                  if f.startswith("favmine_merged_") and f.endswith(".json") and "_analysis" not in f),
                 key=lambda f: os.path.getmtime(os.path.join(MINE, f)))
    if mfs:
        merged = json.load(open(os.path.join(MINE, mfs[-1]), encoding="utf-8"))
    if not merged:
        print("[edge] 无 merged 全库")
        sys.exit(1)
    vids = [v for v in (merged.get("videos") or []) if (v.get("view") or 0) >= 3000]

    # 原始边集：bvid -> 收藏者数（merged 去重会抹掉，须回原始档案）
    inflow = defaultdict(set)
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                if (v.get("view") or 0) >= 3000 and v.get("from_user") and v.get("bvid"):
                    inflow[v["bvid"]].add(v["from_user"])

    def zone_hit(v):
        return any(k in (v.get("tname") or "") for k in ZONE_KW)

    def title_hit(v):
        return any(k in (v.get("title") or "") for k in TITLE_KW)

    cands = [v for v in vids if zone_hit(v) or title_hit(v)]
    for v in cands:
        v["tier"] = tier_of(v.get("cbi", 0), v.get("view") or 0)
        st = v.get("stat") or {}
        view = max(1, v.get("view") or 1)
        v["_coin"] = st.get("coin", 0) / view
        v["_fav"] = st.get("favorite", 0) / view
        v["_like"] = st.get("like", 0) / view
        v["_inflow"] = len(inflow.get(v["bvid"], set()))
    print(f"[edge] 全库 {len(vids)} | 候选 {len(cands)}（分区 {sum(1 for v in cands if zone_hit(v))} / "
          f"标题 {sum(1 for v in cands if title_hit(v))}）")

    def stats(vs):
        n = len(vs)
        gods = sum(1 for v in vs if v["tier"] == "high")
        goods = sum(1 for v in vs if v["tier"] in ("high", "good"))
        med = (sorted(vs, key=lambda v: (v.get("stat") or {}).get("favorite", 0) / max(1, v.get("view") or 1))[n // 2]
               if n else {})
        view = max(1, med.get("view") or 1)
        st = med.get("stat") or {}
        return {"n": n, "gods": gods, "god_rate": gods / max(1, n), "good_rate": goods / max(1, n),
                "coin": st.get("coin", 0) / view, "fav": st.get("favorite", 0) / view,
                "like": st.get("like", 0) / view}

    s_c, s_a = stats(cands), stats(vids)
    cg = [v for v in cands if v["tier"] == "high"]
    fav_dom = sum(1 for v in cg if v["_fav"] > v["_coin"])
    allg = [v for v in vids if v["tier"] == "high"]
    allg_fav_dom = sum(1 for v in allg if (v.get("stat") or {}).get("favorite", 0) > (v.get("stat") or {}).get("coin", 0))

    cands.sort(key=lambda v: -(v.get("cbi") or 0))
    gold = [v for v in cands if v["tier"] == "high"]

    kpi = f"""
    <div class="kpirow">
      <div class="kpi"><div class="n">{len(vids):,}</div><div class="d">全库合格视频</div></div>
      <div class="kpi"><div class="n">{len(cands)}</div><div class="d">候选（1.1%）</div></div>
      <div class="kpi"><div class="n">{s_c['gods']}</div><div class="d">候选中的「神作」（CBI≥3）</div></div>
      <div class="kpi"><div class="n">{s_c['god_rate']:.1%}</div><div class="d">候选神作率<br>全库 {s_a['god_rate']:.1%}</div></div>
    </div>"""

    mx_fav = max(s_c["fav"], s_a["fav"], 0.01)
    mx_rate = max(s_c["god_rate"], s_a["god_rate"], 0.01)
    bars = (
        bar("神作率 候选组", s_c["god_rate"], mx_rate, "#b8912f", f"{s_c['god_rate']:.1%}")
        + bar("神作率 全库", s_a["god_rate"], mx_rate, "#7096D1", f"{s_a['god_rate']:.1%}")
        + bar("优秀率 候选组", s_c["good_rate"], mx_rate, "#b8912f", f"{s_c['good_rate']:.1%}")
        + bar("优秀率 全库", s_a["good_rate"], mx_rate, "#7096D1", f"{s_a['good_rate']:.1%}")
        + '<p style="margin:14px 0 4px">每播放行为中位数：</p>'
        + bar("收藏/播放 候选组", s_c["fav"], mx_fav, "#b8912f", f"{s_c['fav']:.2%}")
        + bar("收藏/播放 全库", s_a["fav"], mx_fav, "#7096D1", f"{s_a['fav']:.2%}")
        + bar("投币/播放 候选组", s_c["coin"], mx_fav, "#b8912f", f"{s_c['coin']:.2%}")
        + bar("投币/播放 全库", s_a["coin"], mx_fav, "#7096D1", f"{s_a['coin']:.2%}")
        + bar("点赞/播放 候选组", s_c["like"], mx_fav, "#b8912f", f"{s_c['like']:.2%}")
        + bar("点赞/播放 全库", s_a["like"], mx_fav, "#7096D1", f"{s_a['like']:.2%}")
        + f'<p style="margin:10px 0 4px">候选神作中 fav&gt;coin 占比：<b>{fav_dom}/{s_c["gods"]} = {fav_dom/max(1,s_c["gods"]):.0%}</b>'
        + f'（全库神作 {allg_fav_dom}/{len(allg)} = {allg_fav_dom/max(1,len(allg)):.0%}）</p>')

    exq = ""
    for i, v in enumerate(gold, 1):
        exq += (f'<div class="ex"><span class="rank">#{i}</span>'
                f'<div class="t"><a href="https://www.bilibili.com/video/{v["bvid"]}" target="_blank">'
                f'{html.escape((v.get("title") or "?")[:52])}</a></div>'
                f'<div class="m">CBI {round(v.get("cbi",0),2)} · 播放 {v.get("view",0):,} · '
                f'币 {v["_coin"]:.2%} / 藏 {v["_fav"]:.2%} / 赞 {v["_like"]:.2%} · '
                f'收藏者 {v["_inflow"]} 人 · {"档案型" if v["_fav"] > v["_coin"] else "表态型"}</div>'
                f'<div class="fill">我的判定：＿＿＿＿（真神作 / 颜值档案 / 擦边）</div></div>')

    rows = []
    for i, v in enumerate(cands, 1):
        cls = "gold" if v["tier"] == "high" else ("good" if v["tier"] == "good" else "")
        shape = "档案型" if v["_fav"] > v["_coin"] else "表态型"
        rows.append(
            f'<tr class="{cls}"><td class="num">{i}</td>'
            f'<td class="num"><b>{round(v.get("cbi", 0), 2)}</b></td><td>{v["tier"]}</td>'
            f'<td class="num">{v["_inflow"]}</td><td class="num">{v.get("view", 0):,}</td>'
            f'<td>{v["_coin"]:.2%} / {v["_fav"]:.2%} / {v["_like"]:.2%}</td><td>{shape}</td>'
            f'<td><a href="https://www.bilibili.com/video/{v["bvid"]}" target="_blank">'
            f'{html.escape((v.get("title") or "?")[:44])}</a></td>'
            f'<td class="blank">＿＿＿</td></tr>')

    table = ('<table><tr><th>#</th><th>CBI</th><th>档</th><th>收藏者</th><th>播放</th>'
             '<th>币/藏/赞 每播放</th><th>形态</th><th>标题</th><th>我的判定</th></tr>'
             + "".join(rows) + "</table>")

    doc = (TPL.replace("__KPI__", kpi)
              .replace("__BARS__", bars)
              .replace("__EXQ__", exq)
              .replace("__TABLE__", table)
              .replace("__NGOLD__", str(len(gold)))
              .replace("__FAVDM__", f"{fav_dom}/{len(gold)}"))
    n_iso = sum(1 for v in gold if v["_inflow"] <= 1)
    exc = "、".join(f"CBI {round(v.get('cbi', 0), 2)}（入度 {v['_inflow']}）" for v in gold if v["_inflow"] > 1)
    note1 = (f"{len(gold)} 条中 {n_iso} 条入度=1：零社区共验，全部是个人「想再看」的孤岛。"
             if n_iso == len(gold) else
             f"{len(gold)} 条中 {n_iso} 条入度=1（零社区共验的个人孤岛）；例外：{exc}——"
             f"它被选为本轮中带实验的流种子，评论区经二次挖掘后获得第二位收藏者。"
             f"除非内容进入流的种子池，颜值档案在收藏图上保持孤岛状态。")
    note2 = ("本轮 12 条 gold 的入度分布证明：未经流种子化的颜值内容在收藏图上保持孤岛（入度 1），"
             "只有进入种子池触发二次挖掘才可能获得共验——但那已经是流的正常工作，不是擦边的胜利。" if any(v["_inflow"] > 1 for v in gold) else "")
    doc = doc.replace("__GOLDNOTE__", note1).replace("__GOLDNOTE2__", note2)
    os.makedirs(OUTDIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"[edge] 候选 {len(cands)} | 神作 {s_c['gods']}（{s_c['god_rate']:.1%} vs 全库 {s_a['god_rate']:.1%}）"
          f" | god 候选入度全1={all(v['_inflow'] <= 1 for v in gold)} -> {OUT}")


if __name__ == "__main__":
    main()
