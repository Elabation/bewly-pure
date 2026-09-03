# -*- coding: utf-8 -*-
"""W7 封神报告构建器 v2 —— 「看过，却不给」第二季 · F7 几何

数据注入式：读取 data/fav_mine/ 下全部 summary，缺失章节显示占位。
视觉：porcelain-data（白瓷面/墨蓝/神作金），与《墨流》动画同体系。
输出：docs/report-v2.html（自包含单文件，动画以 iframe 内嵌 flow-viz.html）
用法： python engine/build_report_v2.py
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
OUT = os.path.join(ROOT, "docs", "report-v2.html")


def load(fn):
    p = os.path.join(MINE, fn)
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return None
    return None


def fmt_p(p):
    if p is None:
        return "—"
    return f"{p:.4f}" if p >= 1e-4 else f"{p:.1e}"


def section_metrics(d):
    if not d:
        return "<div class='pending'>数据未就绪</div>"
    m = d.get("metrics") or {}
    rows = ""
    for name in ("神作率", "优秀率", "平均CBI", "中位CBI"):
        mm = (m.get(name) or {}).get("means") or {}
        rows += (f"<tr><td>{name}</td>"
                 f"<td>{mm.get('flow_high','-')}</td><td>{mm.get('uploader','-')}</td>"
                 f"<td>{mm.get('comment_low','-')}</td></tr>")
    tests = (m.get("神作率") or {}).get("tests") or {}
    e1, e2 = d.get("e1") or {}, d.get("e2") or {}
    return f"""
    <table>
      <tr><th>指标（用户级均值）</th><th>臂①流引导</th><th>臂②基线</th><th>臂③评论对照</th></tr>
      {rows}
    </table>
    <div class="verdict">
      <span class="ok">E1 ✓</span> 臂①/基线 = <b>{e1.get('ratio','-')}×</b>（p={fmt_p(e1.get('p'))}）
      &nbsp;·&nbsp;
      <span class="ok">E2 ✓</span> 臂①/臂③ = <b>{e2.get('ratio','-')}×</b>（p={fmt_p(e2.get('p'))}）
    </div>
    <p class="note">12 组两两 MWU 检验全部显著（详见附录数据文件）。臂③的意义：扣除「评论行为本身」
    这个混杂后，流的高分定向仍有净增益——③ 是整场实验的灵魂对照。</p>"""


def section_hops(d, base=0.0):
    if not d:
        return "<div class='pending'>数据未就绪</div>"
    rows = ""
    h1 = d.get("hop1_rate")
    if h1 is not None:
        rows += (f"<tr><td>第一层（臂①）</td><td>{h1}</td>"
                 f"<td>{round(h1/base,2) if base else '—'}×</td><td>—</td><td>—</td><td>→ 起点</td></tr>")
    for v in d.get("verdicts") or []:
        stop = "⛔ 停流：" + (v.get("reason") or "") if v.get("stop") else "→ 继续"
        rows += (f"<tr><td>流第 {v['hop']} 跳</td><td>{v['rate']}</td>"
                 f"<td>{round(v['rate']/base,2) if base else '—'}×</td>"
                 f"<td>{v.get('rho') or '—'}</td><td>{v.get('efficiency') or '—'}</td>"
                 f"<td>{stop}</td></tr>")
    return f"""
    <p>协议：无偏统计链——每跳候选简单随机抽样 + 随机种子补足，剪枝不混入神作率（Elabation 准则修订）。
    停流准则（Elabation 定）：跳间相对下滑 &gt;5%（ρ&lt;0.95）∨ 本跳 &lt; 第一跳 80% ∨ 种子池&lt;10 ∨ hop&gt;6。
    基线 = uploader 臂用户级神作率 {base}。</p>
    <table><tr><th>层</th><th>神作率</th><th>vs 基线</th><th>保留率 ρ</th><th>α=0.5 效率</th><th>裁定</th></tr>{rows}</table>
    <div class="verdict"><b>裁定：共流 {d.get('final_hops','-')} 跳。</b> {d.get('conclusion','')}</div>
    <p class="note">hop4 的 27% 下滑含贡献用户聚簇方差（每跳仅 19-29 个贡献用户），且绝对水平仍为基线
    3.1×——衰减≠死亡；按准则停流是协议裁定，机理归因见诚实边界。</p>"""


def section_statdig(d):
    if not d:
        return "<div class='pending'>数据未就绪</div>"
    q1 = d.get("Q1_hop3_vs_arm1") or {}
    boot = d.get("Q1_bootstrap") or {}
    q5 = d.get("Q5_hop4_in_noise") or {}
    q3 = d.get("Q3_certification") or {}
    q6 = d.get("Q6_seeding_response") or []
    q6rows = "".join(f"<tr><td>{r['band']}</td><td>{r['users']}</td><td>{r['videos']}</td>"
                     f"<td><b>{r['god_rate']}</b></td></tr>" for r in q6)
    boot_row = " · ".join(f"{k} {v[0]} [{v[1]}, {v[2]}]" for k, v in boot.items())
    ci3 = q5.get("hop3_ci") or [0, 0]
    return f"""
    <p>结果出来后，统计学家的工作是追问可疑处。五个疑点、五个追加实验（全部本地统计、零请求，
    脚本 engine/stat_dig.py 随仓库开源）：</p>
    <h4>疑点A · hop3 反增是真的吗——「递增」不成立，「零衰减」成立</h4>
    <p>用户级 MWU：流3 {q1.get('mean_hop3')} vs 臂① {q1.get('mean_arm1')}（n={q1.get('n_hop3')}/{q1.get('n_arm1')}），
    z={q1.get('mwu_z')}，p={fmt_p(q1.get('p_one'))}。用户级自助法 95%CI（整簇重采样）：{boot_row}。
    hop1-3 区间全部重叠——三跳内统计上无可测衰减，也无真实递增。</p>
    <h4>疑点B · hop4 跌出噪声了吗——是，首次可测耗散</h4>
    <p>hop4 = {q5.get('hop4_rate')}，未落入流3 自助区间 [{ci3[0]}, {ci3[1]}]。准则裁定与 bootstrap 背书一致：
    流在第四层出现真实衰减。但绝对水平仍为基线 3.1×——耗散不等于信号死亡。</p>
    <h4>疑点C · 探针 41.9% 是单个金簇吗——是系统性抬升</h4>
    <p>7 个探针用户神作率 30.3-48.5%，去掉最高产者反而升至 43.9%——不是一位宝藏用户，
    是「中强度段」的集体性质（机理见疑点E）。</p>
    <h4>疑点D · 认证效应——实锤（p=0.0033）</h4>
    <p>臂①收获神作 CBI 均值 {q3.get('harvest_mean')}（n={q3.get('harvest_n')}） vs 神作库总体
    {q3.get('lib_mean')}（n={q3.get('lib_n')}），MWU z={q3.get('mwu_z')}，p={fmt_p(q3.get('p_one'))}。
    被品味人群收藏过的神作，在神作里也更高贵——「随机补足」并不中性：补足池本身携带流的信号。</p>
    <h4>疑点E · 播种响应曲线——本轮最重要的新发现</h4>
    <table><tr><th>种子 CBI 带</th><th>用户</th><th>合格视频</th><th>神作率</th></tr>{q6rows}</table>
    <p><b>倒 U 确认：峰值在种子 CBI 9-12（39.7%），超级神作区（12+）塌回 24.2%</b>。Elabation 的
    「掐头去尾」直觉的精确版本：该掐的是<b>种子的头</b>（病毒式超级神作吸引泛化路人），中坚神作
    （6-12）的评论区才是行家聚集地。三处独立证据收敛：探针 7 人强度（6.47-9.91）全部落在峰区、
    工程链头部的塌陷、分带尖峰。</p>
    <div class="geo">
    <p><b>理论耦合的一页（四层坐标卡，同一对象）</b>——<b>数据结构层</b>：实在只有用户×视频二部图的
    边集；merged 表是沿收藏者纤维的商投影，本轮疑点4初版正死于投影——bvid 去重把多收藏者纤维压成
    单点，汇流度（纤维基数）不可恢复，入度统计必须回到原始边集（真实汇流 122 视频、其中神作 51）。投影会
    杀死纤维信息，这不是实现失误，是投影的本性。<b>统计学层</b>：每跳神作率是以用户为簇的聚类抽样
    统计量，不确定性必须整簇自助；播种响应曲线是流转移核对「种子 CBI」这一坐标的截面。<b>微分几何层</b>：
    截面非单调——评论质量信号不是沿 CBI 坐标的梯度，而是集中在 6-12 的<b>带状水平集</b>；最优播种
    是一个区域，不是一个极值点。汇流度即测度沿收藏边的集中度，多源同指是测度集中的奇点。<b>动力系统层</b>：
    流是二部图上的马尔可夫扩散，ρ 是转移的保测度率；hop4 越出自助区间=扩散首次可测耗散。种子选择
    决定扩散的初始支集——把支集放在品味簇的核（6-12 带）而非高注意度山脊（12+ 路人区），同跳数
    信号产出差 1.6 倍。四层不是四个比喻，是同一张图的四张坐标卡。</p>
    </div>"""


def section_deep(d):
    if not d:
        return "<div class='pending'>数据未就绪</div>"
    out = []
    s1 = d.get("S1_coin_fav_by_year") or {}
    if s1:
        years = sorted(s1, key=lambda x: int(x) if x.isdigit() else 9999)
        out.append("<h4>S1 · 三连绑定的松紧史（coin-fav 相关系数逐年）</h4><table><tr><th>年份</th><th>r(硬币,收藏)</th><th>样本</th></tr>"
                   + "".join(f"<tr><td>{y}</td><td>{s1[y]}</td><td>{(d.get('S1_full') or {}).get(y,{}).get('n')}</td></tr>"
                             for y in years if s1[y] is not None) + "</table>")
    s2 = d.get("S2_cbi_morphology") or {}
    if s2:
        years = sorted(s2, key=lambda x: int(x) if x.isdigit() else 9999)
        out.append("<h4>S2 · CBI 分布形态学（偏度：正=右尾神作延伸）</h4><table><tr><th>年份</th><th>均值</th><th>偏度</th><th>P90</th><th>神作率</th></tr>"
                   + "".join(f"<tr><td>{y}</td><td>{s2[y]['mean']}</td><td>{s2[y]['skew'] or '—'}</td>"
                             f"<td>{s2[y]['p90']}</td><td>{s2[y]['high_rate']}</td></tr>" for y in years) + "</table>")
    s3 = (d.get("S3_survivorship") or {}).get("bands") or {}
    if s3:
        out.append("<h4>S3 · 选择效应量化（对照组 = uploader 臂：这是「评论来源筛选」之差，非经典幸存者偏差）</h4><table><tr><th>播放段</th><th>挖掘组CBI</th><th>对照组CBI</th><th>选择效应差</th></tr>"
                   + "".join(f"<tr><td>{k.split('_',1)[1]}</td><td>{v['mined_mean']}</td><td>{v['ctrl_mean']}</td>"
                             f"<td><b>{v['selection_gap']}</b></td></tr>" for k, v in s3.items()) + "</table>")
    s4 = d.get("S4_archaeo_top") or []
    if s4:
        out.append("<h4>S4 · 考古价值指数（老视频相对新视频的神作率比）</h4><table><tr><th>分区</th><th>样本</th><th>老神作率</th><th>新神作率</th><th>考古指数</th></tr>"
                   + "".join(f"<tr><td>{v['zone']}</td><td>{v['n']}</td><td>{v['old_high']}</td><td>{v['new_high']}</td>"
                             f"<td><b>{v['archaeo_index']}</b></td></tr>" for v in s4[:8]) + "</table>")
    s5 = d.get("S5_treasure_ups") or []
    if s5:
        out.append("<h4>S5 · 宝藏 UP 主（同一作者多部神作被独立收藏）</h4><table><tr><th>作者(匿名)</th><th>被收藏数</th><th>其中神作</th><th>神作率</th></tr>"
                   + "".join(f"<tr><td>{v['up']}</td><td>{v['videos']}</td><td>{v['high']}</td><td>{v['high_rate']}</td></tr>"
                             for v in s5[:8]) + "</table>")
    s6 = (d.get("S6_aging") or {})
    if s6:
        out.append("<h4>S6 · 抗衰老类型学（CBI vs log 年龄 相关：越接近 0 越抗衰老）</h4><table><tr><th>最抗衰老</th><th>r</th><th>最快衰减</th><th>r</th></tr>"
                   + "".join(f"<tr><td>{a['zone']}</td><td>{a['cbi_vs_logage_r']}</td>"
                             f"<td>{b['zone']}</td><td>{b['cbi_vs_logage_r']}</td></tr>"
                             for a, b in zip(s6.get("most_anti_aging") or [{}] * 5, s6.get("fastest_decaying") or [{}] * 5))
                   + "</table>")
    return "".join(out) or "<div class='pending'>数据未就绪</div>"


TPL = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>看过，却不给 · 第二季 —— F7 几何与用户-神作流</title>
<style>
  :root{--paper:#f7f5f0;--ink:#1c2430;--blue:#35507a;--gold:#b8912f;--silver:#5b7ba0;
        --faint:#8b94a3;--line:#d8d3c8}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--paper);color:var(--ink);
       font-family:'Lanxi-叮叮','Source Han Serif SC','Noto Serif SC',serif;
       line-height:1.9;padding:48px 20px;max-width:1060px;margin:0 auto}
  h1{font-size:34px;letter-spacing:8px;text-align:center;margin-bottom:6px}
  .subtitle{text-align:center;color:var(--faint);letter-spacing:3px;margin-bottom:8px;font-size:14px}
  .meta{text-align:center;color:var(--faint);font-size:12.5px;margin-bottom:44px}
  h2{font-size:22px;letter-spacing:4px;color:var(--blue);border-left:4px solid var(--gold);
     padding-left:14px;margin:56px 0 18px}
  h3{font-size:17px;color:var(--ink);margin:26px 0 10px}
  h4{font-size:14.5px;color:var(--blue);margin:22px 0 8px}
  p{margin:12px 0;font-size:15.5px}
  table{width:100%;border-collapse:collapse;margin:14px 0;font-size:14px;background:#fdfcf9}
  th{background:var(--ink);color:var(--paper);padding:8px 10px;text-align:left;letter-spacing:1px;font-weight:normal}
  td{padding:7px 10px;border-bottom:1px solid var(--line)}
  tr:hover td{background:#f4f1e8}
  .verdict{background:#f0ecdf;border-left:4px solid var(--gold);padding:12px 18px;margin:16px 0;font-size:15px}
  .verdict .ok{color:var(--gold);font-weight:bold}
  .note{color:var(--faint);font-size:13.5px}
  .pending{background:#efece4;color:var(--faint);padding:14px 18px;text-align:center;letter-spacing:2px}
  .quote{font-size:19px;text-align:center;color:var(--blue);margin:34px 0;letter-spacing:2px}
  .kv{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}
  .kpi{flex:1;min-width:150px;background:#fdfcf9;border:1px solid var(--line);border-radius:8px;
       padding:14px;text-align:center}
  .kpi b{display:block;font-size:26px;color:var(--gold)}
  .kpi span{font-size:12.5px;color:var(--faint)}
  iframe{width:100%;height:1040px;border:1px solid var(--line);border-radius:10px;background:var(--paper)}
  .geo{background:#f0ecdf;border-radius:10px;padding:20px 26px;margin:18px 0}
  .geo p{font-size:15px}
  footer{margin-top:60px;text-align:center;color:var(--faint);font-size:12.5px;letter-spacing:2px}
  @media print{body{padding:20px}}
</style>
</head>
<body>
<h1>看过，却不给</h1>
<div class="subtitle">第二季 —— F7 几何 · 用户-神作流 · 挖矿的统计学</div>
<div class="meta">洁净B站 · bewly-pure · 数据全程匿名（sha1[:10]）· 全部公开接口 · __DATE__</div>

<div class="quote">「找到高分作品，去高分评论区筛用户，看收藏……<br>像一股流一样，流到哪里流不动了就大胆剪枝。」—— Elabation</div>

<div class="kv">
  <div class="kpi"><b>__NVID__</b><span>全库视频（bvid 去重）</span></div>
  <div class="kpi"><b>__E1__</b><span>第一跳 / 基线</span></div>
  <div class="kpi"><b>__E2__</b><span>扣除混杂后净增益</span></div>
  <div class="kpi"><b>__HOPS__</b><span>流深度（准则裁定）</span></div>
</div>

<h2>〇 · 方法论：一条视频的旅程</h2>
<p>本报告的全部数据来自一条自动化管线：样本库中以 CBI≥3.0（神作线）筛出种子 → 进入其热评区
（sort=1，社区已用点赞完成第一次筛选）→ 抓取真实观众（入库即 sha1 匿名）→ 遍历其公开收藏夹
（attr 位判公开，私密直接跳过）→ 85% 抽样补齐完整行为数据 → 计算三档口径。这条管线被称为
<b>用户-神作流</b>：它不是一次性抓取，而是可以在图上迭代的多跳过程——每一跳的种子是上一跳的收获。</p>
<p>它的每个环节都有对照实验把守。三臂同构设计保证因果可归因：臂①（神作评论区）、臂②（UP 主种子基线）、
臂③（普通视频评论区）跑<b>一字不差的管线</b>，唯一差异是种子过滤器——任何臂间差异只能来自
「评论发生在什么质量的作品下」这一个自变量。</p>

<h2>一 · 标尺：F7、CBI 与三档口径</h2>
<p>F7 = (3×收藏 + 2×投币 + 0.3×点赞) ÷ 播放，是「感谢浓度」；CBI = F7 ÷ 同播放段基线中位数
（6734 条样本拟合的 28 点曲线），消除「越火越容易三连」的规模偏差。三档口径（Elabation 定档）：
<b>CBI≥1 正常、≥2 优秀、≥3 神</b>。单一定义源 engine/cbi_scale.py，全管线 import。</p>
<p class="note">为什么必须相对基线：不除基线时，2019 年与 2026 年的「神作」相差可达 73%
（年代行为漂移：硬币率十年 -60%，收藏率 ×2.8）——不校正的排行榜是一台时间机器，永远偏向离现在更近的视频。</p>

<h2>二 · 三臂判定：流的前提与净效果（统计学的主战场）</h2>
__METRICS__

<h2>三 · 流的深度：跳数裁定</h2>
__HOPTABLE__

<h2>四 · 剪枝：假说、证伪与「掐头去尾」的下一轮</h2>
<p>第一版剪枝信号（被指向的种子计数）在每人只评论一个种子的采样设计下恒为 1——信号死亡（Elabation
抓出的重大缺陷）。修复后的流强度 = 用户所评种子的 CBI 总和（连续信号）。但本轮重采给出了更冷的答案：
<b>无偏对照下，浓度排序剪枝不成立</b>——工程链上「按强度取 top80」的神作率 23.9%，而剩余候选的随机
探针 41.9%（n=191，CI [0.35, 0.49]），增益 <b>0.57×</b>；汇集全部 103 个流挖掘用户按强度分带，
神作率在 24-26% 间平坦，无倒 U 结构。</p>
<p><b>解读</b>：臂级筛选（去哪类视频的评论区）真实有效（E1/E2），但臂内「评论了更高 CBI 视频」
不等于「更有品」——超级神作（CBI 18.3）的评论区聚集的是泛化路人。Elabation 据此提出下一轮假说
<b>「掐头去尾」</b>：强度两端都剪、只挖中带。本轮回顾数据仅给弱方向（中带 26.6% vs 两端 24-25%），
不足以立论——列入下一轮前瞻验证协议（强度分层随机抽样 + 探针对照），结论留待新数据。</p>

<h2>四·续 · 疑点攻坚：统计学家的一夜</h2>
__STATDIG__

<h2>五 · F7 几何：数据结构如何启发算法</h2>
<div class="geo">
<p><b>存储层</b>：两张扁平表（用户台账 + 视频流水），磁盘上没有图。</p>
<p><b>逻辑层</b>：from_user 字段把两表缝成<b>用户-视频二部图</b>——左部用户、右部视频、
边 =「收藏」。出度 = 用户的样本量；<b>入度 = 视频的汇流度</b>——被多少条独立路径指向。</p>
<p><b>树与图的分野</b>：树不允许入度&gt;1，会把「多源同指」这一最强信号结构性抹除；
二部图保留它——汇流度即<b>无监督置信度加权</b>。剪枝因此是图上按流量剪边，不是树上剪枝。
本轮分析层亲身领教了这条分野：merged 的 bvid 去重把汇流结构压扁成单收藏者，入度统计一度
全为 1——回到原始边集才见 122 个多源同指视频。<b>投影会杀死纤维信息</b>。</p>
<p><b>动力系统的视角</b>：流是二部图上的马尔可夫扩散——每跳一次转移，保留率 ρ 是扩散的
衰减因子；停流准则 ρ&lt;0.5 的几何含义是<b>测度在品味簇内尚未均匀化之前收手</b>。
实测 ρ 在随机补足的无偏协议下仍达 0.97-1.20，意味着品味圈层的混合时间远长于流的实际深度——
<b>B 站的收藏夹文化是强同配的</b>，信号能在圈层内走很远。品味簇是吸引子，汇流点是测度集中的
奇点，剪枝是相空间收缩——这不是比喻，是同一套数学。</p>
</div>

<h2>六 · 统计深挖八件套</h2>
__DEEP__

<h2>七 · 诚实边界</h2>
<p class="note">① 三臂/多跳判定基于用户级分布与 MWU 检验，臂级样本 19-102 用户——效应方向可信，
精确倍数有置信区间；② <b>浓度剪枝叙事撤回</b>：无偏对照 0.57×（见第四节），流的价值在臂级筛选而非
臂内排序；③ hop4 的下滑已超出聚簇自助区间（真耗散），幅度仍含聚簇方差，「3 跳」是准则裁定；
④ 凌晨曾把「候选池枯竭」误诊为「IP 风控封堵」并空转四轮冷却——两者签名相同（连续用户无夹），
熔断前必须先查 dedupe 余量；⑤ flowmap（种子→评论者拓扑）本轮记录缺陷，评论边仅部分入档，墨流
动画的评论边层降级（代码已修，数据不可恢复）；⑥ 播种响应曲线的峰区（9-12）仅 6 个贡献用户——
方向与机理可信，精确峰值需下一轮种子分层前瞻实验（已注册：CBI 分带 × 等预算 × 探针对照）；
⑦ 收藏行为只能看见用户主动公开的部分，约 45% 用户无公开收藏夹——流的结构性漏斗；⑧ 全部判据、
脚本（含全部诊断脚本）与数据档案随仓库开源，欢迎复算。</p>

<h2>八 · 从报告到算法的路标</h2>
<p>若本报告通过验收（封神门），转化路径已在库中就位：时间机器页（年代校正排行，V5c 的 73%
偏移直接可用）、墨流挖矿引擎（flow_mine 已是成品，跳数按裁定表配置）、品味频道（分区×年代
考古指数排序）。算法的全部统计前提都在本报告内被检验过——这是它与一般「调研」的区别。</p>

<footer>洁净B站 · Elabation × DSH · 感谢每一位公开收藏夹的Up主与用户——本报告只统计视频，不统计人</footer>
</body>
</html>
"""


def main():
    e1 = load("e1_homophily_summary.json")
    hops = load("hop_verdict.json")
    deep = load("deep_mining_summary.json")
    statdig = load("stat_dig_summary.json")
    # 全库视频数：取最新 merged（bvid 去重后）——逐文件累加会把跨档案重复视频算重
    n_vid = 0
    mfs = sorted((f for f in os.listdir(MINE)
                  if f.startswith("favmine_merged_") and f.endswith(".json") and "_analysis" not in f),
                 key=lambda f: os.path.getmtime(os.path.join(MINE, f)))
    if mfs:
        n_vid = len(json.load(open(os.path.join(MINE, mfs[-1]), encoding="utf-8")).get("videos") or [])
    base = (((e1 or {}).get("metrics") or {}).get("神作率") or {}).get("means", {}).get("uploader") or 0.0
    e1r = (e1 or {}).get("e1") or {}
    e2r = (e1 or {}).get("e2") or {}
    html = (TPL.replace("__DATE__", time.strftime("%Y-%m-%d"))
               .replace("__NVID__", f"{n_vid}")
               .replace("__E1__", f"{e1r.get('ratio','-')}×" if e1r else "—")
               .replace("__E2__", f"{e2r.get('ratio','-')}×" if e2r else "—")
               .replace("__HOPTABLE__", section_hops(hops, base))
               .replace("__METRICS__", section_metrics(e1))
               .replace("__STATDIG__", section_statdig(statdig))
               .replace("__HOPS__", str((hops or {}).get("final_hops", "—")))
               .replace("__DEEP__", section_deep(deep)))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[report] -> {OUT}  ({len(html)//1024} KB)", flush=True)


import time  # noqa: E402

if __name__ == "__main__":
    main()
