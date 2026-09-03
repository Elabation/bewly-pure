# -*- coding: utf-8 -*-
"""个人兴趣子报告 · CBI 擦边/颜值区扫描（2026-09-03，Elabation 私人委托）

问题：美女/舞蹈/擦边类视频能不能「骗过」CBI？
方法：分区名 + 标题关键词双通道检出候选 → 神作率/行为构成 vs 全库对照 → CBI 降序名录供人审。
纪律：纯本地、零请求、只统计视频不统计人（无 from_user 字段输出）、文件仅存本地不入仓不上传。
输出：docs/personal/cbi-edge-review.html
"""
import html
import json
import os
import re
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
OUTDIR = os.path.join(ROOT, "docs", "personal")
OUT = os.path.join(OUTDIR, "cbi-edge-review.html")

ZONE_KW = ["舞蹈", "宅舞", "时尚", "美妆", "颜值"]
TITLE_KW = ["美女", "小姐姐", "小姐姐", "擦边", "颜值", "热舞", "宅舞", "跳舞", "黑丝",
            "JK", "jk", "制服", "性感", "变装", "女团", "cos", "Cos", "COS", "纯欲",
            "身材", "御姐", "妹子", "舞蹈", "舞翻", "卡点舞"]

TPL = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>个人子报告 · CBI 擦边/颜值区扫描</title>
<style>
  :root{--paper:#f7f5f0;--ink:#1c2430;--blue:#35507a;--gold:#b8912f;--silver:#5b7ba0;
        --faint:#8b94a3;--line:#d8d3c8;--warn:#a04b2f}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--paper);color:var(--ink);
       font-family:'Lanxi-叮叮','Source Han Serif SC','Noto Serif SC',serif;
       line-height:1.85;padding:44px 20px;max-width:1160px;margin:0 auto}
  h1{font-size:27px;letter-spacing:5px;text-align:center}
  .subtitle{text-align:center;color:var(--faint);letter-spacing:2px;font-size:13px;margin:6px 0 4px}
  .banner{background:#f0e4d8;border:1px solid #d8b89a;border-radius:8px;padding:10px 18px;
          font-size:13px;color:var(--warn);text-align:center;margin:14px 0 26px;letter-spacing:1px}
  h2{font-size:19px;letter-spacing:3px;color:var(--blue);border-left:4px solid var(--gold);
     padding-left:12px;margin:44px 0 14px}
  p{font-size:14.5px;margin:10px 0}
  table{width:100%;border-collapse:collapse;margin:12px 0;font-size:13.5px;background:#fdfcf9}
  th{background:var(--ink);color:var(--paper);padding:7px 9px;text-align:left;font-weight:normal;letter-spacing:1px}
  td{padding:6px 9px;border-bottom:1px solid var(--line)}
  tr:hover td{background:#f4f1e8}
  .gold{color:var(--gold);font-weight:bold}
  .sil{color:var(--silver)}
  .note{color:var(--faint);font-size:13px}
  .kpi{display:flex;gap:14px;flex-wrap:wrap;margin:16px 0}
  .kpi div{flex:1;min-width:150px;background:#fdfcf9;border:1px solid var(--line);border-radius:8px;
           padding:12px;text-align:center}
  .kpi b{display:block;font-size:24px;color:var(--gold)}
  .kpi span{font-size:12px;color:var(--faint)}
  a{color:var(--blue);text-decoration:none}
  a:hover{text-decoration:underline}
  footer{margin-top:50px;text-align:center;color:var(--faint);font-size:12px;letter-spacing:2px}
</style>
</head>
<body>
<h1>CBI 会「被骗」吗 —— 擦边/颜值区扫描</h1>
<div class="subtitle">个人兴趣子报告 · 与主报告《看过，却不给》第二季无隶属关系</div>
<div class="banner">仅本地存档 · 不上传 GitHub · 不入主报告 · 只统计视频不统计人（无任何用户字段）</div>

<h2>〇 · 问题与方法</h2>
<p><b>问题</b>：收藏夹里的美女/舞蹈/擦边类视频，能否借「收藏=想再看」的行为逃过 CBI 的三档判定、
甚至混入神作名录？——这本质是在问 CBI 的价值观边界：它度量的是<b>感谢行为浓度</b>，不是抽象的
「内容质量」。如果颜值内容真被大量收藏（想再看），CBI 会如实反映这种行为——「骗过」与否，
取决于我们认为算法该度量什么。本报告只呈现行为数据，判定权在人。</p>
<p><b>检出</b>（双通道，任一命中即入候选）：① 分区名含 舞蹈/宅舞/时尚/美妆/颜值；
② 标题含 {TITLEKW}。全部候选按 CBI 降序排名供人工审核。</p>
<p class="note"><b>覆盖度坦白</b>：通道①结构性失效——view API 的 tname 字段当前返回空串（09-02 旧库
亦全为「?」，即整条收藏管线从未有过分区数据，主报告 S4/S6 分区节空白同源）。故候选全部来自标题
关键词通道：标题无舞蹈/美女字样的同类视频会漏检。下一轮挖矿可加 tags API 请求补齐分区（+1 请求/视频，已登记）。</p>

<h2>一 · 检出规模</h2>
__KPI__

<h2>二 · 神作率与行为构成对照（候选组 vs 全库）</h2>
__COMPARE__

<h2>三 · 分区神作率排行（全库背景，n≥40 的分区）</h2>
__ZONES__

<h2>四 · 名录 · 按 CBI 降序（共 __NROWS__ 条候选）</h2>
<p class="note">列：CBI | 档 | 播放 | 分区 | 每播放行为（币/藏/赞）| 形态判读（fav主导=想再看档案型，
coin主导=投币表态型）| 标题与链接。人审建议：先看 gold（CBI≥3）的行——它们若入主报告神作名录，
就是「擦边混入」的直接证据。</p>
__TABLE__

<footer>个人子报告 · 本地存档 · 洁净B站 · 只统计视频，不统计人</footer>
</body>
</html>
"""


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
    print(f"[edge] 全库合格视频 {len(vids)}")

    def zone_hit(v):
        t = v.get("tname") or ""
        return any(k in t for k in ZONE_KW)

    def title_hit(v):
        t = v.get("title") or ""
        return any(k in t for k in TITLE_KW)

    def is_cand(v):
        return zone_hit(v) or title_hit(v)

    cands = [v for v in vids if is_cand(v)]
    for v in cands:
        v["tier"] = tier_of(v.get("cbi", 0), v.get("view") or 0)
    print(f"[edge] 候选 {len(cands)}（分区命中 {sum(1 for v in cands if zone_hit(v))}，"
          f"标题命中 {sum(1 for v in cands if title_hit(v))}）")

    def stats(vs):
        n = len(vs)
        gods = sum(1 for v in vs if v["tier"] == "high")
        goods = sum(1 for v in vs if v["tier"] in ("high", "good"))
        med = lambda k: sorted(vs, key=lambda v: (v.get("stat") or {}).get(k, 0) / max(1, v.get("view") or 1))[n // 2] if n else {}
        mv = med("view")
        return {"n": n, "gods": gods, "god_rate": gods / max(1, n),
                "good_rate": goods / max(1, n),
                "coin": (mv.get("coin", 0) / max(1, mv.get("view", 1))),
                "fav": (mv.get("favorite", 0) / max(1, mv.get("view", 1))),
                "like": (mv.get("like", 0) / max(1, mv.get("view", 1)))}

    s_c, s_all = stats(cands), stats(vids)
    # 形态判读：候选神作的 fav/coin 主导比
    cg = [v for v in cands if v["tier"] == "high"]
    fav_dom = sum(1 for v in cg if (v.get("stat") or {}).get("favorite", 0) > (v.get("stat") or {}).get("coin", 0))
    allg = [v for v in vids if v["tier"] == "high"]
    allg_fav_dom = sum(1 for v in allg if (v.get("stat") or {}).get("favorite", 0) > (v.get("stat") or {}).get("coin", 0))

    # 分区排行（n≥40）
    zones = defaultdict(lambda: [0, 0])
    for v in vids:
        z = v.get("tname") or "?"
        zones[z][0] += 1
        zones[z][1] += v["tier"] == "high"
    zrows = sorted(((z, n, g, g / n) for z, (n, g) in zones.items() if n >= 40),
                   key=lambda r: -r[3])

    cands.sort(key=lambda v: -(v.get("cbi") or 0))
    rows = []
    for i, v in enumerate(cands, 1):
        st = v.get("stat") or {}
        view = max(1, v.get("view") or 1)
        fav_d = st.get("favorite", 0) > st.get("coin", 0)
        shape = "fav档案型" if fav_d else "coin表态型"
        cls = "gold" if v["tier"] == "high" else ("sil" if v["tier"] == "good" else "")
        rows.append(
            f"<tr><td>{i}</td><td class='{cls}'><b>{round(v.get('cbi', 0), 2)}</b></td>"
            f"<td>{v['tier']}</td><td>{v.get('view', 0):,}</td>"
            f"<td>{html.escape(v.get('tname') or '?')}</td>"
            f"<td>{st.get('coin', 0)/view:.3%} / {st.get('favorite', 0)/view:.3%} / {st.get('like', 0)/view:.3%}</td>"
            f"<td>{shape}</td>"
            f"<td><a href='https://www.bilibili.com/video/{v['bvid']}' target='_blank'>"
            f"{html.escape((v.get('title') or '?')[:46])}</a></td></tr>")
    show = rows[:250]
    more = f"<p class='note'>仅展示前 250 条（共 {len(rows)} 条）。</p>" if len(rows) > 250 else ""

    kpi = f"""
    <div class="kpi">
      <div><b>{len(vids):,}</b><span>全库合格视频</span></div>
      <div><b>{len(cands)}</b><span>候选（舞蹈/颜值/擦边）</span></div>
      <div><b>{s_c['gods']}</b><span>候选中的「神作」（CBI≥3）</span></div>
      <div><b>{s_c['god_rate']:.1%}</b><span>候选神作率（全库 {s_all['god_rate']:.1%}）</span></div>
    </div>"""

    cmp_rows = f"""
    <table>
      <tr><th></th><th>候选组</th><th>全库</th></tr>
      <tr><td>神作率（CBI≥3）</td><td class="gold"><b>{s_c['god_rate']:.1%}</b></td><td>{s_all['god_rate']:.1%}</td></tr>
      <tr><td>优秀率（CBI≥2）</td><td>{s_c['good_rate']:.1%}</td><td>{s_all['good_rate']:.1%}</td></tr>
      <tr><td>每播放投币（中位）</td><td>{s_c['coin']:.3%}</td><td>{s_all['coin']:.3%}</td></tr>
      <tr><td>每播放收藏（中位）</td><td><b>{s_c['fav']:.2%}</b></td><td>{s_all['fav']:.2%}</td></tr>
      <tr><td>每播放点赞（中位）</td><td>{s_c['like']:.1%}</td><td>{s_all['like']:.1%}</td></tr>
      <tr><td>神作中 fav&gt;coin 占比</td><td>{fav_dom}/{s_c['gods']} = {fav_dom/max(1,s_c['gods']):.0%}</td>
          <td>{allg_fav_dom}/{len(allg)} = {allg_fav_dom/max(1,len(allg)):.0%}</td></tr>
    </table>
    <p class="note">读法：若候选组神作率≈全库且行为构成无异常 → CBI 没有被「颜值效应」特殊优待或歧视；
    若 fav 主导占比显著更高 → 「收藏=想再看」确实在为颜值内容开绿灯，这是价值观层待你裁定的部分。</p>"""

    ztable = ("<table><tr><th>分区</th><th>样本</th><th>神作</th><th>神作率</th></tr>"
              + "".join(f"<tr><td>{html.escape(z)}</td><td>{n}</td><td>{g}</td>"
                        f"<td class='{'gold' if r >= 0.3 else ''}'>{r:.1%}</td></tr>" for z, n, g, r in zrows)
              + "</table>")

    doc = (TPL.replace("__TITLEKW__", "／".join(TITLE_KW[:12]) + " 等")
              .replace("__KPI__", kpi)
              .replace("__COMPARE__", cmp_rows)
              .replace("__ZONES__", ztable)
              .replace("__NROWS__", str(len(rows)))
              .replace("__TABLE__", "".join(show) + more))
    os.makedirs(OUTDIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"[edge] 候选 {len(cands)} | 神作 {s_c['gods']}（{s_c['god_rate']:.1%} vs 全库 {s_all['god_rate']:.1%}）"
          f" | 神作中fav主导 {fav_dom}/{s_c['gods']} -> {OUT}")


from cbi_scale import tier_of  # noqa: E402

if __name__ == "__main__":
    main()
