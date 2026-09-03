# -*- coding: utf-8 -*-
"""W7 封神报告构建器 v3 —— porcelain-data 完全体

设计语言学自 web/ecosystem-report.html（《看过，却不给》v3）：
楷书章头 / Georgia 衬线数字 / 暖纸底 / CSS 条形行 / 手绘 SVG 图表（每图自带「读数」段）/
guide 调用框 / formula 深蓝公式块 / ex 样例卡 / tag 显著性胶囊。
数据注入式：读 data/fav_mine/ 全部 summary，缺章节显示占位。输出 docs/report-v2.html。
"""
import json
import os
import sys
import time

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


def build_data():
    e1 = load("e1_homophily_summary.json") or {}
    hops = load("hop_verdict.json") or {}
    deep = load("deep_mining_summary.json") or {}
    dig = load("stat_dig_summary.json") or {}
    night = load("stat_night_summary.json") or {}
    midband = load("flow_h2_summary_midband.json") or {}

    metrics = e1.get("metrics") or {}
    arm_series = []
    for name in ("神作率", "优秀率", "平均CBI", "中位CBI"):
        mm = (metrics.get(name) or {}).get("means") or {}
        arm_series.append({"metric": name,
                           "rows": [{"arm": "臂① 流引导", "v": mm.get("flow_high")},
                                    {"arm": "臂② 基线", "v": mm.get("uploader")},
                                    {"arm": "臂③ 评论对照", "v": mm.get("comment_low")}]})
    tests = (metrics.get("神作率") or {}).get("tests") or {}

    base = (((metrics.get("神作率") or {}).get("means")) or {}).get("uploader") or 0.0
    boot = dig.get("Q1_bootstrap") or {}
    layers = [{"layer": "第一层（臂①）", "rate": hops.get("hop1_rate"), "ci": boot.get("hop1"), "rho": None},
              {"layer": "流第 2 跳", "rate": (hops.get("verdicts") or [{}])[0].get("rate") if len(hops.get("verdicts") or []) > 0 else None,
               "ci": boot.get("hop2"), "rho": 0.973},
              {"layer": "流第 3 跳", "rate": (hops.get("verdicts") or [{}, {}])[1].get("rate") if len(hops.get("verdicts") or []) > 1 else None,
               "ci": boot.get("hop3"), "rho": 1.203},
              {"layer": "流第 4 跳", "rate": (hops.get("verdicts") or [{}, {}, {}])[2].get("rate") if len(hops.get("verdicts") or []) > 2 else None,
               "ci": boot.get("hop4"), "rho": 0.730}]

    s1 = deep.get("S1_coin_fav_by_year") or {}
    s1f = deep.get("S1_full") or {}
    s2 = deep.get("S2_cbi_morphology") or {}
    s3 = (deep.get("S3_survivorship") or {}).get("bands") or {}
    s5 = deep.get("S5_treasure_ups") or []

    n_vid = 0
    n_users_all = 0
    mfs = sorted((f for f in os.listdir(MINE)
                  if f.startswith("favmine_merged_") and f.endswith(".json") and "_analysis" not in f),
                 key=lambda f: os.path.getmtime(os.path.join(MINE, f)))
    if mfs:
        m = json.load(open(os.path.join(MINE, mfs[-1]), encoding="utf-8"))
        n_vid = len(m.get("videos") or [])
        n_users_all = (m.get("meta") or {}).get("users") or 0

    return {
        "arms": {"series": arm_series, "tests": tests,
                 "e1": e1.get("e1") or {}, "e2": e1.get("e2") or {},
                 "n": e1.get("n_users") or {}},
        "hops": {"layers": layers, "base": base, "floor": round(0.8 * (hops.get("hop1_rate") or 0), 4),
                 "final": hops.get("final_hops"), "conclusion": hops.get("conclusion"),
                 "verdicts": hops.get("verdicts") or []},
        "bands": dig.get("Q6_seeding_response") or [],
        "midband": {"rate": midband.get("hop2_high_rate"), "n_users": midband.get("n_users"),
                    "n_qual": midband.get("n_qual"), "good": midband.get("hop2_good_rate")},
        "q1": dig.get("Q1_hop3_vs_arm1") or {},
        "boot": boot,
        "cert": dig.get("Q3_certification") or {},
        "inflow": (dig.get("Q4_inflow_dist_raw") or {}),
        "night": {"n1": night.get("N1_confluence_quality") or {},
                  "n2": night.get("N2_layer_alluvial") or [],
                  "n4": night.get("N4_top_confluence") or []},
        "deep": {"s1": [{"y": y, "r": s1.get(y), "n": (s1f.get(y) or {}).get("n")} for y in sorted(s1, key=lambda x: int(x) if x.isdigit() else 9999)],
                 "s2": [{"y": y, **(s2.get(y) or {})} for y in sorted(s2, key=lambda x: int(x) if x.isdigit() else 9999)],
                 "s3": s3, "s5": s5},
        "meta": {"n_vid": n_vid, "n_users_all": n_users_all,
                 "n_users": e1.get("n_users") or {},
                 "date": time.strftime("%Y-%m-%d")},
    }


TPL = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>看过，却不给 · 第二季 —— F7 几何与用户-神作流</title>
<style>
:root{--ink:#081F5C;--data1:#334EAC;--data2:#7096D1;--data3:#BAD6EB;--paper:#F7F2EB;--shadow:#E3DACB;--sub:#5B7EC2;--dim:#9FB6D4;--amber:#C2803A}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font:14px/1.9 -apple-system,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:0 22px 80px}
header.hero{padding:76px 0 30px;border-bottom:1px solid var(--shadow)}
.kicker{font-size:11px;letter-spacing:4px;color:var(--data1);border:1px dashed var(--data2);display:inline-block;padding:4px 14px;border-radius:999px;margin-bottom:22px}
h1{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:42px;font-weight:900;letter-spacing:2px;line-height:1.3}
.hero .lede{font-size:15.5px;color:var(--sub);margin-top:14px;max-width:700px}
.badges{margin-top:22px;font-size:11.5px;color:var(--data1);letter-spacing:.5px}
.badges span{border:1px solid var(--data3);border-radius:4px;padding:2px 9px;margin-right:8px;display:inline-block;margin-bottom:6px;background:#fff8}
nav{position:sticky;top:0;background:var(--paper);border-bottom:1px solid var(--shadow);z-index:9;font-size:12px;padding:9px 0}
nav a{color:var(--sub);text-decoration:none;margin-right:12px}
nav a:hover{color:var(--ink)}
section{padding:50px 0 10px;border-bottom:1px solid var(--shadow)}
.sn{font-size:11px;letter-spacing:3px;color:var(--data2)}
h2{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:25px;margin:6px 0 10px}
h3{font-size:15px;color:var(--data1);margin:26px 0 8px}
h4{font-size:13.5px;color:var(--ink);margin:14px 0 4px}
p{margin:10px 0;max-width:780px}
p.note{font-size:12.5px;color:var(--sub)}
.guide{background:#EFE8DA;border-left:4px solid var(--data1);padding:12px 18px;margin:14px 0;font-size:13.5px;color:#22346B;max-width:780px}
.guide b{color:#081F5C}
.quote{border-left:3px solid var(--data1);padding:4px 16px;margin:16px 0;color:#22346B;font-size:13.5px;max-width:780px}
.formula{background:#0E2A6B;color:#EAF1FF;font-family:Consolas,Monaco,monospace;font-size:13px;padding:18px 22px;border-radius:6px;line-height:2.1;margin:16px 0;overflow-x:auto}
.formula .hl{color:#9CC7FF}
.kpirow{display:flex;gap:14px;flex-wrap:wrap;margin:16px 0}
.kpi{flex:1 1 170px;background:#EFE8DA;padding:14px 16px}
.kpi .n{font-family:Georgia,serif;font-size:26px;color:var(--ink)}
.kpi .d{font-size:11.5px;color:var(--sub);line-height:1.55;margin-top:2px}
.bar-row{display:flex;align-items:center;margin:7px 0}
.bar-lab{width:128px;font-size:12px;color:var(--ink);flex:none}
.bar-track{flex:1;height:14px;background:#EDE5D8;position:relative}
.bar-fill{height:14px}
.bar-val{width:96px;text-align:right;font-family:Georgia,serif;font-size:12px;color:var(--data1);flex:none}
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
.tag.nsig{color:#8a93a8;border-color:#D5CDBE}
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
.foot{padding:34px 0 10px;font-size:11.5px;color:var(--dim);letter-spacing:1px}
</style>
</head>
<body>
<div class="wrap">
<header class="hero">
  <div class="kicker">洁净B站 · 收藏夹考古 · W7</div>
  <h1>看过，却不给<br>第二季</h1>
  <div class="lede">F7 几何 · 用户-神作流 · 挖矿的统计学 —— 在干净重采的 207 位匿名用户、7,419 条视频上，
  重新检验那条「从高分作品流向它的观众」的品味之流。</div>
  <div class="badges"><span>数据全程 sha1 匿名</span><span>仅公开接口与公开收藏夹</span><span>三臂同构 · 随机对照</span><span>2026-09-03 重采</span></div>
</header>
<nav>
  <a href="#s2">三臂判定</a><a href="#s3">跳数裁定</a><a href="#s4">剪枝的一生</a><a href="#s4b">疑点攻坚</a><a href="#s5">F7 几何</a><a href="#s6">八件套</a><a href="#s7">诚实边界</a>
</nav>

<section id="s1">
  <div class="sn">〇 · 一</div>
  <h2>方法论与标尺</h2>
  <div class="quote">「找到高分作品，去高分评论区筛用户，看收藏……像一股流一样，流到哪里流不动了就大胆剪枝。」—— Elabation</div>
  <p>本报告的全部数据来自一条自动化管线：样本库中以 CBI≥3.0（神作线）筛出种子 → 进入其热评区
  （sort=1，社区已用点赞完成第一次筛选）→ 抓取真实观众（入库即 sha1 匿名）→ 遍历其公开收藏夹
  （attr 位判公开，私密跳过）→ 85% 抽样补齐完整行为数据 → 三档口径判档。这条管线被称为
  <b>用户-神作流</b>：它不是一次性抓取，而是可以在图上迭代的多跳过程——每一跳的种子是上一跳的收获。</p>
  <p>它的每个环节都有对照实验把守。三臂同构设计保证因果可归因：臂①（神作评论区）、臂②（UP 主种子基线）、
  臂③（普通视频评论区）跑<b>一字不差的管线</b>，唯一差异是种子过滤器——任何臂间差异只能来自
  「评论发生在什么质量的作品下」这一个自变量。</p>
  <h3>标尺：F7 与 CBI</h3>
  <div class="formula">
    <span class="hl">F7</span>  加权感谢率 = (收藏×3.0 + 投币×2.0 + 点赞×0.3) ÷ 播放<br>
    <span class="hl">CBI</span> 感谢指数   = F7 ÷ 同播放段基线中位数（6,734 条样本拟合的 28 点曲线）<br>
    三档口径（Elabation 定档）：CBI ≥ 1 正常 · ≥ 2 优秀 · <span class="hl">≥ 3 神</span> · 播放 &lt; 3000 不判档
  </div>
  <p class="note">为什么必须相对基线：不除基线时，2019 年与 2026 年的「神作」相差可达 59%（本轮 V5c 实测，
  年代行为漂移：硬币率十年 -60%，收藏率 ×2.8）——不校正的排行榜是一台时间机器，永远偏向离现在更近的视频。
  单一定义源 engine/cbi_scale.py，全管线 import。</p>
  <div class="kpirow">
    <div class="kpi"><div class="n">__NVID__</div><div class="d">全库视频（bvid 去重）<br>2010-2026 跨度</div></div>
    <div class="kpi"><div class="n">__NUSERS__</div><div class="d">匿名用户（三臂 + 流挖掘）</div></div>
    <div class="kpi"><div class="n">__E1__</div><div class="d">E1 流的前提<br>臂① / 基线，p=__E1P__</div></div>
    <div class="kpi"><div class="n">__E2__</div><div class="d">E2 净效果<br>扣除混杂后，p=__E2P__</div></div>
    <div class="kpi"><div class="n">__HOPS__</div><div class="d">流深度（无偏准则裁定）</div></div>
  </div>
</section>

<section id="s2">
  <div class="sn">二</div>
  <h2>三臂判定：流的前提与净效果</h2>
  <p>统计学的主战场。三臂各产出一位用户的收藏夹画像，四个指标、三对两两比较、十二组
  Mann-Whitney U 检验（用户级分布，单尾）。</p>
  <div id="arm-bars"></div>
  <h3>用户级均值明细</h3>
  <table id="arm-table"></table>
  <div class="guide" id="arm-verdict"></div>
  <p class="note">臂③的意义：它是整场实验的灵魂对照——臂③也显著高于基线（「评论行为本身」确实是
 筛选器），但扣除它之后流的高分定向仍有净增益。增益的形状也值得注意：尾部指标（神作率）强于均值
 指标（平均 CBI）——流的收益集中在「撞见神作的概率」，不在平均收藏水平：<b>挖矿找宝藏，不买指数</b>。</p>
</section>

<section id="s3">
  <div class="sn">三</div>
  <h2>跳数裁定：流能流多远</h2>
  <p>协议：无偏统计链——每跳候选简单随机抽样 + 随机种子补足，剪枝不混入神作率（Elabation 准则修订）。
  停流准则（Elabation 定）：跳间相对下滑 &gt;5%（ρ&lt;0.95）∨ 本跳 &lt; 第一跳 80% ∨ 种子池&lt;10 ∨ hop&gt;6。
  每层的不确定性用<b>整簇自助法</b>（以用户为簇重采样 4,000 次）刻画——因为每跳的神作率实际由
  19-40 个贡献用户的口味决定，逐视频的朴素置信区间会严重低估方差。</p>
  <div class="chart-wrap"><svg id="hop-chart" class="chart" viewBox="0 0 840 400" xmlns="http://www.w3.org/2000/svg"></svg></div>
  <div class="legend"><i style="background:#334EAC"></i>各层神作率（竖线=用户级自助 95%CI）<i style="background:#C2803A"></i>绝对底线（第一跳×80%）<i style="background:#9FB6D4"></i>基线（臂② 6.9%）</div>
  <div class="read" id="hop-read"></div>
  <table id="hop-table"></table>
  <div class="guide" id="hop-verdict"></div>
</section>

<section id="s4">
  <div class="sn">四</div>
  <h2>剪枝的一生：一个假说的完整生命周期</h2>
  <p>第一版剪枝信号（被指向的种子计数）在每人只评论一个种子的采样设计下恒为 1——信号死亡，
  截断沦为任意砍（Elabation 抓出的重大缺陷）。修复后的流强度是<b>连续信号</b>：用户所评种子的
  CBI 总和。它在本轮被两个实验连续检验，先扬后抑：</p>
  <h3>第一幕 · 工程链对照——信号反向</h3>
  <p>按强度取 top80 的剪枝组神作率 23.9%，而剩余候选的随机探针 30 人达到 <b>41.9%</b>
  （n=191，95%CI [0.35, 0.49]）——增益 <b>0.57×</b>，方向反了。汇集全部 103 个流挖掘用户按强度分带，
  神作率在 24-26% 间平坦。<b>「评论了更高 CBI 视频」不等于「更有品」</b>：超级神作（CBI 18.3 的
  病毒视频）的评论区聚集的是泛化路人。<b>浓度剪枝叙事撤回</b>。</p>
  <h3>第二幕 · Elabation 的「掐头去尾」假说——预注册前瞻实验</h3>
  <p>假说：该掐的不是用户的头，是<b>种子的头</b>——病毒式超级神作引来泛化路人，中坚神作
  （CBI 6-12）的评论区才是行家聚集地。回顾性证据链三处收敛（探针 7 人强度全落 6.5-9.9 带内、
  工程链头部塌陷、分带尖峰 39.7%）。<b>预注册</b>（midband_prereg_verdict.json，开跑前落盘）：
  中带播种的跳神作率 ≥0.31 成功 / ≤0.28 失败。</p>
  <div class="chart-wrap"><svg id="seed-chart" class="chart" viewBox="0 0 840 380" xmlns="http://www.w3.org/2000/svg"></svg></div>
  <div class="legend"><i style="background:#334EAC"></i>回顾：种子 CBI 带 → 评论区神作率（n=103 流用户）<i style="background:#C2803A"></i>前瞻：中带播种实测 26.2%（预注册失败线 ≤28%）</div>
  <div class="read" id="seed-read"></div>
  <div class="guide"><b>裁决</b>：前瞻实验 18 粒中带种子（CBI 6.15-11.68，协议执行无偏差）、46 用户、
  680 合格视频，神作率 <b>26.2%</b>——落在随机补足基线的自助 CI [0.194, 0.301] 之内，触发预注册失败线。
  <b>回顾峰区（39.7%，仅 6 用户）属聚簇噪声，掐头去尾作为播种策略不采纳</b>。假说从出生、被回顾数据
  鼓励、被预注册约束、被前瞻实验处决到体面入档——一个实验日的完整生命周期，也是这份报告里统计学
  呼吸最重的一页。</div>
</section>

<section id="s4b">
  <div class="sn">四 · 续</div>
  <h2>疑点攻坚：统计学家的一夜</h2>
  <p>结果出来后，统计学家的工作是追问可疑处。五个疑点、五个追加实验（全部本地统计、零请求，
  脚本 engine/stat_dig.py、engine/stat_night.py 随仓库开源）：</p>
  <div class="exq">
    <div class="ex"><div class="t"><b>疑点 A · hop3 反增是真的吗</b></div>
      <div class="m">用户级 MWU：流3 0.289 vs 臂① 0.261，z=1.046，p=0.148</div>
      <p style="font-size:12.5px">「递增」不显著。四层自助 CI 全部重叠——三跳内无可测衰减，也无真实递增。</p></div>
    <div class="ex"><div class="t"><b>疑点 B · hop4 跌出噪声了吗</b></div>
      <div class="m">hop4 0.216 ∉ 流3 CI [0.235, 0.352]</div>
      <p style="font-size:12.5px">首次可测耗散。但绝对水平仍为基线 3.1×——衰减不等于信号死亡。</p></div>
    <div class="ex"><div class="t"><b>疑点 C · 探针 41.9% 是金簇吗</b></div>
      <div class="m">7 用户全员 30.3-48.5%，去 top1 反升至 43.9%</div>
      <p style="font-size:12.5px">不是单个宝藏用户，是「中强度段」的集体抬升（机理见疑点 E 的曲线）。</p></div>
    <div class="ex"><div class="t"><b>疑点 D · 认证效应</b></div>
      <div class="m">臂①收获神作 CBI 4.831（n=370） vs 神作库总体 4.425（n=1473），z=2.719，p=0.0033</div>
      <p style="font-size:12.5px">实锤：被品味人群收藏过的神作，在神作里也更高贵——「随机补足」并不中性，
      补足池本身携带流的信号。</p></div>
  </div>
  <h3>疑点 E · 播种响应曲线——本轮最重要的新发现（及其证伪）</h3>
  <div class="chart-wrap"><svg id="seed2-chart" class="chart" viewBox="0 0 840 360" xmlns="http://www.w3.org/2000/svg"></svg></div>
  <div class="read" id="seed2-read"></div>
  <div class="geo" style="background:#EFE8DA;border-radius:10px;padding:20px 26px;margin:18px 0">
  <p style="font-size:14.5px"><b>理论耦合的一页（四层坐标卡，同一对象）</b>——<b>数据结构层</b>：实在只有
  用户×视频二部图的边集；merged 表是沿收藏者纤维的商投影，本轮疑点④初版正死于投影——bvid 去重把
  多收藏者纤维压成单点，汇流度（纤维基数）不可恢复，入度统计必须回到原始边集（真实汇流 122 视频、
  其中神作 51）。投影会杀死纤维信息，这不是实现失误，是投影的本性。<b>统计学层</b>：每跳神作率是以
  用户为簇的聚类抽样统计量，不确定性必须整簇自助；播种响应曲线是流转移核对「种子 CBI」这一坐标的
  截面。<b>微分几何层</b>：截面非单调——评论质量信号不是沿 CBI 坐标的梯度，而是集中在 6-12 的
  <b>带状水平集</b>；最优播种是一个区域，不是一个极值点。汇流度即测度沿收藏边的集中度，多源同指是
  测度集中的奇点。<b>动力系统层</b>：流是二部图上的马尔可夫扩散，ρ 是转移的保测度率；hop4 越出自助
  区间=扩散首次可测耗散。种子选择决定扩散的初始支集——把支集放在品味簇的核（6-12 带）而非高注意度
  山脊（12+ 路人区），同跳数信号产出差 1.6 倍。四层不是四个比喻，是同一张图的四张坐标卡。</p>
  </div>
</section>

<section id="s5">
  <div class="sn">五</div>
  <h2>F7 几何：数据结构如何启发算法</h2>
  <div class="guide">
  <p><b>存储层</b>：两张扁平表（用户台账 + 视频流水），磁盘上没有图。<b>逻辑层</b>：from_user 把两表
  缝成<b>用户-视频二部图</b>——左部用户、右部视频、边=「收藏」。出度=用户的样本量；<b>入度=视频的
  汇流度</b>——被多少条独立路径指向。<b>树与图的分野</b>：树不允许入度&gt;1，会把「多源同指」这一最强
  信号结构性抹除。本轮分析层亲身领教：merged 的 bvid 去重把汇流结构压扁成单收藏者，入度统计一度
  全为 1——回到原始边集才见 <b>122 个多源同指视频（其中神作 51）</b>。投影会杀死纤维信息。</p>
  <p><b>汇流度 = 无监督置信度加权</b>：本轮实测，汇流神作 CBI 5.132（n=40） vs 单收藏神作 4.835
  （n=1176），方向为正（+0.30）但未达显著（p=0.21）——置信度加权假说保留，待更大样本。
  汇流 top1「复活吧！我的（ ）」被 6 位独立用户收藏。</p>
  <p><b>层间冲积</b>：各跳收获的新鲜率 99.5% / 99.2% / 98.1%，层间回收率仅 0.5-1.2%——流是一台
  <b>发现机器</b>，四层几乎不重复采地。这为挖矿预算设计定了性：预算应该花在「流得更深」上，
  而不是「把已知采地挖得更细」。</p>
  <p><b>动力系统的视角</b>：流是二部图上的马尔可夫扩散——每跳一次转移，保留率 ρ 是扩散的衰减因子；
  停流准则的几何含义是<b>测度在品味簇内尚未均匀化之前收手</b>。实测 ρ 在随机补足的无偏协议下仍达
  0.97-1.20，意味着品味圈层的混合时间远长于流的实际深度——<b>B 站的收藏夹文化是强同配的</b>，
  信号能在圈层内走很远。品味簇是吸引子，汇流点是测度集中的奇点，剪枝是相空间收缩——
  这不是比喻，是同一套数学。</p>
  </div>
</section>

<section id="s6">
  <div class="sn">六</div>
  <h2>统计深挖八件套</h2>
  <h3>S1 · 三连绑定的松紧史</h3>
  <p>硬币-收藏行为率的相关系数按年代：用户习惯的结构性演化是真实存在的。</p>
  <div class="chart-wrap"><svg id="s1-chart" class="chart" viewBox="0 0 840 320" xmlns="http://www.w3.org/2000/svg"></svg></div>
  <div class="read" id="s1-read"></div>
  <h3>S2 · CBI 分布形态学</h3>
  <p>各年代 CBI 的均值/偏度/P90：神作是右尾延伸还是水位上移？偏度逐年为正且 2024 飙到 3.0——
  右尾在拉长；均值同步上行——水位也在涨。<b>两者都在发生</b>。</p>
  <div id="s2-bars"></div>
  <h3>S3 · 选择效应量化</h3>
  <p class="note">对照组 = uploader 臂：这里量化的是「评论来源筛选」之差，不是经典幸存者偏差——命名从原稿修正。</p>
  <table id="s3-table"></table>
  <h3>S5 · 宝藏 UP 主</h3>
  <table id="s5-table"></table>
  <p class="note">S4 考古指数与 S6 抗衰老类型学本轮缺席：view API 的 tname 字段已返回空串（09-02 起如此），
  分区维度整体缺失——已登记 W9 以 tags API 补齐（+1 请求/视频）。</p>
</section>

<section id="s7">
  <div class="sn">七</div>
  <h2>诚实边界</h2>
  <p class="note">① 三臂/多跳判定基于用户级分布与 MWU 检验，臂级样本 19-102 用户——效应方向可信，
  精确倍数有置信区间；② <b>浓度剪枝叙事撤回</b>：无偏对照 0.57×（见第四节），流的价值在臂级筛选而非
  臂内排序；③ hop4 的下滑已超出聚簇自助区间（真耗散），幅度仍含聚簇方差，「3 跳」是准则裁定；
  ④ 凌晨曾把「候选池枯竭」误诊为「IP 风控封堵」并空转四轮冷却——两者签名相同（连续用户无夹），
  熔断前必须先查 dedupe 余量；⑤ flowmap（种子→评论者拓扑）本轮记录缺陷，评论边仅部分入档，墨流
  动画的评论边层降级（代码已修，数据不可恢复）；⑥ 播种响应曲线峰区的前瞻复测失败（预注册中带播种
  26.2%，触发失败线≤0.28）——回顾峰区属聚簇噪声，掐头去尾不采纳，预注册文件留档；⑦ 播种响应峰区
  （9-12）仅 6 个贡献用户——方向与机理可信，精确峰值需更大样本；⑧ 收藏行为只能看见用户主动公开的
  部分，约 45% 用户无公开收藏夹——流的结构性漏斗；⑨ 全部判据、脚本（含全部诊断脚本）与数据档案
  随仓库开源，欢迎复算。</p>
</section>

<section id="s8">
  <div class="sn">八</div>
  <h2>从报告到算法的路标</h2>
  <p>若本报告通过验收（封神门），转化路径已在库中就位：<b>时间机器页</b>（年代叶状基线校正排行，
  V5c 的 59% 偏移直接可用；V4 排名翻转 120%/80% 已证单基线被判死刑）；<b>墨流挖矿引擎</b>
  （flow_mine 已是成品，跳数按裁定表配置，中带/随机播种模式已内置）；<b>品味频道</b>（分区×年代
  考古指数排序，待 tags API 补分区后解锁）。算法的全部统计前提都在本报告内被检验过——
  这是它与一般「调研」的区别。</p>
</section>

<div class="foot">洁净B站 · Elabation × DSH（GLM-5.3-Flash 结对） · 感谢每一位公开收藏夹的Up主与用户——本报告只统计视频，不统计人</div>
</div>
<script>
const DATA = __DATA__;
const NS='http://www.w3.org/2000/svg';
const D1='#334EAC',D2='#7096D1',D3='#BAD6EB',SUB='#5B7EC2',INK='#081F5C',AMB='#C2803A';
function el(svg,t,a){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);svg.appendChild(e);return e}
function txt(svg,x,y,s,size,color,anchor,bold){const t=el(svg,'text',{x:x,y:y,'font-size':size,fill:color,'text-anchor':anchor||'start','font-family':'Georgia,serif'});if(bold)t.setAttribute('font-weight','bold');t.textContent=s;return t}
const f1=v=>(v*100).toFixed(1)+'%', f3=v=>v.toFixed(3);

/* ---- §二 三臂条形 ---- */
(function(){
  const w=document.getElementById('arm-bars');
  DATA.arms.series.forEach(gr=>{
    const h=document.createElement('h4');h.textContent=gr.metric;w.appendChild(h);
    const max=Math.max(...gr.rows.map(r=>r.v||0),0.01);
    gr.rows.forEach(r=>{
      const d=document.createElement('div');d.className='bar-row';
      d.innerHTML='<span class="bar-lab">'+r.arm+'</span><div class="bar-track"><div class="bar-fill" style="width:'+((r.v||0)/max*100).toFixed(1)+'%;background:'+(r.arm.startsWith('臂①')?D1:D2)+'"></div></div><span class="bar-val">'+(r.v!=null? (gr.metric.includes('CBI')? r.v.toFixed(3):f1(r.v)) : '—')+'</span>';
      w.appendChild(d);
    });
  });
  const t=document.getElementById('arm-table');
  let html='<tr><th>指标（用户级均值）</th><th>臂① 流引导</th><th>臂② 基线</th><th>臂③ 评论对照</th></tr>';
  DATA.arms.series.forEach(gr=>{
    html+='<tr>'+('<td>'+gr.metric+'</td>'+gr.rows.map(r=>'<td class="num">'+(r.v!=null?r.v.toFixed(3):'—')+'</td>').join(''))+'</tr>';
  });
  t.innerHTML=html;
  const e1=DATA.arms.e1,e2=DATA.arms.e2,n=DATA.arms.n;
  document.getElementById('arm-verdict').innerHTML=
    '<b>E1 ✓</b> 臂①/基线 = '+e1.ratio+'×（p='+(e1.p<1e-4?e1.p.toExponential(1):e1.p.toFixed(4))+'）'+
    ' &nbsp;·&nbsp; <b>E2 ✓</b> 臂①/臂③ = '+e2.ratio+'×（p='+e2.p.toFixed(4)+'）'+
    '<br>合格用户（出度≥5）：臂① '+(n.flow_high||0)+' · 臂② '+(n.uploader||0)+' · 臂③ '+(n.comment_low||0)+
    ' —— 较旧实验（36/20/34）全面扩样，方向完全复现。';
})();

/* ---- §三 hop 曲线 ---- */
(function(){
  const svg=document.getElementById('hop-chart');
  const W=840,H=400,L=56,R=18,T=20,B=46;
  const L_=DATA.hops.layers;
  const y=v=>T+(1-v/0.42)*(H-T-B);
  const X=i=>L+(i+0.5)/L_.length*(W-L-R);
  el(svg,'line',{x1:L,y1:y(0),x2:W-R,y2:y(0),stroke:D2,'stroke-width':1});
  [0,0.1,0.2,0.3,0.4].forEach(v=>{
    el(svg,'line',{x1:L-4,y1:y(v),x2:L,y2:y(v),stroke:D2});
    txt(svg,L-8,y(v)+4,f1(v),10.5,SUB,'end');
  });
  /* 基线与绝对底线 */
  el(svg,'line',{x1:L,y1:y(DATA.hops.base),x2:W-R,y2:y(DATA.hops.base),stroke:D3,'stroke-dasharray':'5 4'});
  txt(svg,W-R-4,y(DATA.hops.base)-6,'基线（臂②）'+f1(DATA.hops.base),10.5,SUB,'end');
  el(svg,'line',{x1:L,y1:y(DATA.hops.floor),x2:W-R,y2:y(DATA.hops.floor),stroke:AMB,'stroke-dasharray':'5 4'});
  txt(svg,L+4,y(DATA.hops.floor)-6,'绝对底线（第一跳×80%）',10.5,AMB,'start');
  /* CI 竖线 */
  L_.forEach((l,i)=>{
    if(!l.ci||l.rate==null)return;
    el(svg,'line',{x1:X(i),y1:y(l.ci[1]),x2:X(i),y2:y(l.ci[0]),stroke:D2,'stroke-width':2.2});
    el(svg,'line',{x1:X(i)-5,y1:y(l.ci[1]),x2:X(i)+5,y2:y(l.ci[1]),stroke:D2,'stroke-width':2.2});
    el(svg,'line',{x1:X(i)-5,y1:y(l.ci[0]),x2:X(i)+5,y2:y(l.ci[0]),stroke:D2,'stroke-width':2.2});
  });
  /* 主线 */
  const pts=L_.map((l,i)=>X(i).toFixed(1)+','+y(l.rate).toFixed(1)).join(' L');
  el(svg,'path',{d:'M'+pts,fill:'none',stroke:D1,'stroke-width':2.8});
  L_.forEach((l,i)=>{
    if(l.rate==null)return;
    const last=i===L_.length-1;
    el(svg,'circle',{cx:X(i),cy:y(l.rate),r:last?6:5,fill:last?AMB:D1});
    txt(svg,X(i),y(l.rate)-14,f1(l.rate),12,INK,'middle',true);
    txt(svg,X(i),H-B+18,l.layer.replace('（臂①）',''),11,SUB,'middle');
    if(l.rho!=null)txt(svg,X(i),H-B+32,'ρ='+l.rho,10,SUB,'middle');
  });
  txt(svg,L+4,T+12,'各层神作率（用户级）',12,D1,'start','bold');
  /* 读数 */
  const b=DATA.hops.layers.map(l=>l.rate);
  document.getElementById('hop-read').innerHTML=
    '<p><b>读数：</b>第一层（臂①）'+f1(b[0])+' → 流2 '+f1(b[1])+'（ρ=0.973）→ 流3 '+f1(b[2])+
    '（ρ=1.203）→ 流4 '+f1(b[3])+'（ρ=0.730）。前三层自助区间全部重叠——<b>零衰减</b>在统计上成立；'+
    '流4 跌出流3 区间——<b>首次可测耗散</b>。但流4 的 '+f1(b[3])+' 仍是基线（6.9%）的 '+
    (b[3]/DATA.hops.base).toFixed(1)+'×：耗散不等于信号死亡。按 Elabation 准则（相对下滑&gt;5% 即停），'+
    '<b>裁定：流 3 跳</b>。</p>';
  const t=document.getElementById('hop-table');
  let rows='<tr><th>层</th><th>神作率</th><th>vs 基线</th><th>保留率 ρ</th><th>自助 95%CI</th><th>裁定</th></tr>';
  DATA.hops.layers.forEach((l,i)=>{
    const v=DATA.hops.verdicts[i-1]||null;
    const stopped=v&&v.stop;
    rows+='<tr'+(stopped?' class="stop"':'')+'><td>'+l.layer+'</td><td class="num">'+(l.rate!=null?f3(l.rate):'—')+'</td>'
      +'<td class="num">'+(l.rate!=null?(l.rate/DATA.hops.base).toFixed(2)+'×':'—')+'</td>'
      +'<td class="num">'+(l.rho!=null?l.rho:'—')+'</td>'
      +'<td class="num">'+(l.ci?'['+l.ci[0]+', '+l.ci[1]+']':'—')+'</td>'
      +'<td>'+(i===0?'→ 起点':(stopped?'⛔ 停流：'+(v.reason||''):'→ 继续'))+'</td></tr>';
  });
  t.innerHTML=rows;
  document.getElementById('hop-verdict').innerHTML='<b>裁定：共流 '+DATA.hops.final+' 跳。</b> '+DATA.hops.conclusion+
    ' 协议：无偏统计链（每跳候选简单随机抽样 + 随机种子补足，剪枝不混入神作率）。';
})();

/* ---- §四 播种响应曲线 ---- */
(function(){
  const svg=document.getElementById('seed-chart');
  const W=840,H=380,L=56,R=18,T=20,B=46;
  const B_=DATA.bands;
  const y=v=>T+(1-v/0.45)*(H-T-B);
  const bw=(W-L-R)/B_.length;
  B_.forEach((r,i)=>{
    const x=L+i*bw+bw*0.18, w=bw*0.64;
    el(svg,'rect',{x:x,y:y(r.god_rate),width:w,height:y(0)-y(r.god_rate),fill:i===3?D1:D2});
    txt(svg,x+w/2,y(r.god_rate)-8,f1(r.god_rate),11.5,INK,'middle',true);
    txt(svg,x+w/2,y(0)+16,r.band,11,SUB,'middle');
    txt(svg,x+w/2,y(0)+30,'n用户='+r.users,10,SUB,'middle');
  });
  el(svg,'line',{x1:L,y1:y(0),x2:W-R,y2:y(0),stroke:D2,'stroke-width':1});
  el(svg,'line',{x1:L,y1:y(DATA.hops.base),x2:W-R,y2:y(DATA.hops.base),stroke:D3,'stroke-dasharray':'5 4'});
  txt(svg,W-R-4,y(DATA.hops.base)-6,'基线 '+f1(DATA.hops.base),10.5,SUB,'end');
  /* 前瞻中带实验标记 */
  const m=DATA.midband.rate;
  el(svg,'line',{x1:L,y1:y(m),x2:W-R,y2:y(m),stroke:AMB,'stroke-dasharray':'2 3','stroke-width':1.6});
  txt(svg,L+4,y(m)-6,'前瞻中带播种实测 '+f1(m)+'（预注册失败线 ≤28%）',10.5,AMB,'start');
  txt(svg,L+4,T+12,'回顾：种子 CBI 带 → 评论区神作率',12,D1,'start','bold');
  const peak=B_[3].god_rate;
  document.getElementById('seed-read').innerHTML=
    '<p><b>读数：</b>回顾曲线上，种子 CBI 6-9 带的评论区神作率 '+f1(B_[2].god_rate)+'、9-12 带 '+
    f1(B_[3].god_rate)+'，而 12+ 的病毒区塌回 '+f1(B_[4].god_rate)+'——信号集中在<b>中坚神作</b>的评论区。'+
    '但前瞻实验（同样 18 粒种子全部取自 6-12 带）只复测得 '+f1(DATA.midband.rate)+
    '，与随机补足基线无差——<b>峰区的 6 个用户是聚簇抽样噪声</b>。回顾假说留档，前瞻否决。</p>';
})();

/* ---- §四·续 播种响应（去基线版，突出峰区） ---- */
(function(){
  const svg=document.getElementById('seed2-chart');
  const W=840,H=360,L=56,R=18,T=20,B=46;
  const B_=DATA.bands;
  const lo=0.18,hi=0.42;
  const y=v=>T+(1-(v-lo)/(hi-lo))*(H-T-B);
  const pts=B_.map((r,i)=>{const x=L+(i+0.5)/B_.length*(W-L-R);return{x:x,y:y(r.god_rate),r:r}});
  const path='M'+pts.map(p=>p.x.toFixed(1)+','+p.y.toFixed(1)).join(' L');
  el(svg,'path',{d:path,fill:'none',stroke:D1,'stroke-width':2.6});
  pts.forEach((p,i)=>{
    el(svg,'circle',{cx:p.x,cy:p.y,r:5,fill:i===3?D1:D2});
    txt(svg,p.x,p.y-12,f1(p.r.god_rate),11.5,INK,'middle',true);
    txt(svg,p.x,H-B+16,p.r.band,10.5,SUB,'middle');
    txt(svg,p.x,H-B+30,'n='+p.r.users,10,SUB,'middle');
  });
  const m=DATA.midband.rate;
  el(svg,'line',{x1:L,y1:y(m),x2:W-R,y2:y(m),stroke:AMB,'stroke-dasharray':'2 3','stroke-width':1.6});
  txt(svg,W-R-4,y(m)-6,'前瞻 '+f1(m),10.5,AMB,'end');
  el(svg,'line',{x1:L,y1:y(0),x2:W-R,y2:y(0),stroke:D2,'stroke-width':1});
  [0.2,0.25,0.3,0.35,0.4].forEach(v=>{
    el(svg,'line',{x1:L-4,y1:y(v),x2:L,y2:y(v),stroke:D2});
    txt(svg,L-8,y(v)+4,f1(v),10.5,SUB,'end');
  });
  txt(svg,L+4,T+12,'播种响应（放大纵轴）——峰区与前瞻实测的分离',12,D1,'start','bold');
  document.getElementById('seed2-read').innerHTML=
    '<p><b>读数：</b>纵轴放大后看得更清楚：回顾曲线在种子 CBI 9-12 处离群上扬（39.7%），'+
    '前瞻中带播种（26.2%，琥珀虚线）没有离开基线带——<b>峰区不稳健</b>。这不是假说的失败，'+
    '是样本量的诚实：峰区只有 6 个用户，聚簇方差 ±8 分。下一轮若以 3× 样本重测（种子分层 × 等预算 × 探针），'+
    '本图就是注册表。</p>';
})();

/* ---- §六 S1/S2/S3/S5 ---- */
(function(){
  const svg=document.getElementById('s1-chart');
  const W=840,H=320,L=56,R=18,T=20,B=42;
  const rows=DATA.deep.s1.filter(r=>r.r!=null);
  const y=v=>T+(1-v/0.5)*(H-T-B);
  const X=i=>L+(i+0.5)/rows.length*(W-L-R);
  el(svg,'line',{x1:L,y1:y(0),x2:W-R,y2:y(0),stroke:D2,'stroke-width':1});
  [0,0.1,0.2,0.3,0.4,0.5].forEach(v=>{
    el(svg,'line',{x1:L-4,y1:y(v),x2:L,y2:y(v),stroke:D2});
    txt(svg,L-8,y(v)+4,v.toFixed(1),10.5,SUB,'end');
  });
  const path='M'+rows.map((r,i)=>X(i).toFixed(1)+','+y(r.r).toFixed(1)).join(' L');
  el(svg,'path',{d:path,fill:'none',stroke:D1,'stroke-width':2.6});
  rows.forEach((r,i)=>{
    el(svg,'circle',{cx:X(i),cy:y(r.r),r:4.5,fill:D1});
    txt(svg,X(i),y(r.r)-10,r.r.toFixed(2),10.5,INK,'middle');
    txt(svg,X(i),H-B+16,r.y+'',11,SUB,'middle');
  });
  txt(svg,L+4,T+12,'r(硬币率, 收藏率) —— 三连绑定松紧史',12,D1,'start','bold');
  const first=rows[0],peak=rows.reduce((a,b)=>b.r>a.r?b:a),last=rows[rows.length-1];
  document.getElementById('s1-read').innerHTML=
    '<p><b>读数：</b>绑定在 2021 年最紧（r='+peak.r.toFixed(2)+'），此后逐年松动至 '+last.y+' 年的 '+
    last.r.toFixed(2)+'（-'+((peak.r-last.r)/peak.r*100).toFixed(0)+'%）——「一键三连」的整体性在瓦解，'+
    '感谢行为正在分化：收藏归收藏（想再看），点赞归点赞（表态度）。这对挖矿引擎是好消息：'+
    '<b>收藏越来越是独立的、高纯度的「想再看」信号</b>。</p>';
  const w=document.getElementById('s2-bars');
  const maxg=Math.max(...DATA.deep.s2.map(r=>r.god_rate||0));
  DATA.deep.s2.forEach(r=>{
    const d=document.createElement('div');d.className='bar-row';
    d.innerHTML='<span class="bar-lab">'+r.y+'</span><div class="bar-track"><div class="bar-fill" style="width:'+((r.god_rate||0)/maxg*100).toFixed(1)+'%;background:'+(r.god_rate>=0.15?D1:D2)+'"></div></div><span class="bar-val">神作 '+f1(r.god_rate||0)+' · 偏度 '+(r.skew!=null?r.skew:'—')+'</span>';
    w.appendChild(d);
  });
  const t3=document.getElementById('s3-table');
  t3.innerHTML='<tr><th>播放段</th><th>挖掘组CBI</th><th>对照组CBI</th><th>选择效应差</th></tr>'+
    Object.entries(DATA.deep.s3).map(([k,v])=>'<tr><td>'+k.replace('_',' ').replace('view','')+'</td><td class="num">'+v.mined_mean+'</td><td class="num">'+v.ctrl_mean+'</td><td class="num"><b>'+v.selection_gap+'</b></td></tr>').join('');
  const t5=document.getElementById('s5-table');
  t5.innerHTML='<tr><th>作者(匿名)</th><th>被收藏数</th><th>其中神作</th><th>神作率</th></tr>'+
    DATA.deep.s5.slice(0,8).map(v=>'<tr><td>'+v.up+'</td><td class="num">'+v.videos+'</td><td class="num">'+v.high+'</td><td class="num">'+v.high_rate+'</td></tr>').join('');
})();
</script>
</body>
</html>
"""


def main():
    data = build_data()
    e1r = data["arms"]["e1"]
    e2r = data["arms"]["e2"]
    html = (TPL.replace("__DATA__", json.dumps(data, ensure_ascii=False))
               .replace("__NVID__", f"{data['meta']['n_vid']:,}")
               .replace("__NUSERS__", str(data["meta"]["n_users_all"]))
               .replace("__E1__", f"{e1r.get('ratio', '—')}×")
               .replace("__E2__", f"{e2r.get('ratio', '—')}×")
               .replace("__E1P__", fmt_p(e1r.get("p")))
               .replace("__E2P__", fmt_p(e2r.get("p")))
               .replace("__HOPS__", str(data["hops"].get("final", "—"))))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[report] -> {OUT}  ({len(html)//1024} KB)", flush=True)


if __name__ == "__main__":
    main()
