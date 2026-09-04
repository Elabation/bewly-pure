# -*- coding: utf-8 -*-
"""v3 第二轮筛查名录生成器——主动学习采样：边界带/规则冲突/域样本/对照/锚定

流程：参照库(7,481收藏域+170首页域) → 特征计算(带内投币百分位/币藏赞率/时长/藏币比)
→ v0 草案规则判档 → 分层抽样(边界带+冲突+域+对照+锚定) → docs/personal/v3-screen-catalog.html
纪律：仅本地、不上传；已判 95 条不入新样本（另出 5 条锚定）。
"""
import html
import json
import math
import os
import random
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
random.seed(9527)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
OUT = os.path.join(ROOT, "docs", "personal", "v3-screen-catalog.html")
BAND = 0.2

# v0 草案阈值（待第二轮校准）
T_GOD, T_GOOD = 0.93, 0.85          # 投币百分位：神作候选/优秀候选线
T_NORMAL = 0.72                      # 一般/垃圾线
DUR_EXEC, DUR_CAP = 90, 30           # 时长斩杀线(秒) / 封顶一般线
R_FAVCOIN, R_FAVRATE = 8.0, 0.15     # 吃灰罚：藏/币比 与 收藏率
R_EDGE_LIKE, R_EDGE_COIN, R_EDGE_FAV = 0.20, 0.02, 0.10  # 擦边三连


def load_all():
    pop = {}
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                if (v.get("view") or 0) >= 3000 and v.get("bvid"):
                    st = v.get("stat") or {}
                    view = max(1, v.get("view") or 1)
                    pop[v["bvid"]] = {"bvid": v["bvid"], "title": v.get("title") or "?",
                                      "view": view, "dur": v.get("duration") or 0,
                                      "coin": st.get("coin", 0) / view,
                                      "fav": st.get("favorite", 0) / view,
                                      "like": st.get("like", 0) / view,
                                      "cbi": v.get("cbi", 0)}
    hs = json.load(open(os.path.join(SDIR, "sample_20260903_185231.json"), encoding="utf-8"))
    n_home = 0
    for v in (hs.get("videos") or []):
        st = v.get("stat") or {}
        view = st.get("view") or 0  # collect_stats 样本：view 在 stat 里层
        if view >= 3000 and v.get("bvid"):
            b = v["bvid"]
            if b not in pop:
                n_home += 1
            pop[b] = {"bvid": b, "title": v.get("title") or "?", "view": view,
                      "dur": v.get("duration") or 0,
                      "coin": st.get("coin", 0) / max(1, view),
                      "fav": st.get("favorite", 0) / max(1, view),
                      "like": st.get("like", 0) / max(1, view),
                      "cbi": None}
    print(f"[v3] 首页域新增 {n_home} 条")
    return pop


def main():
    pop = load_all()
    print(f"[v3] 参照库 {len(pop)}")

    # 带内百分位
    bands = defaultdict(lambda: defaultdict(list))
    for r in pop.values():
        k = round(math.log10(r["view"]) / BAND)
        bands[k]["coin"].append((r["coin"], r["bvid"]))
    coin_pct = {}
    for k, d in bands.items():
        d["coin"].sort()
        n = len(d["coin"])
        for i, (_, b) in enumerate(d["coin"]):
            coin_pct[b] = i / max(1, n - 1)

    # v0 草案规则判档
    labeled_bv = set()
    lp = os.path.join(MINE, "elabation_flow_labels.json")
    if os.path.exists(lp):
        labeled_bv = {j["bvid"] for j in json.load(open(lp, encoding="utf-8"))["labels"]}

    for r in pop.values():
        r["coin_pct"] = coin_pct.get(r["bvid"])
        r["favcoin"] = (r["fav"] / r["coin"]) if r["coin"] > 1e-6 else float("inf")
        firings = []
        tier = "一般候选"
        if r["coin_pct"] is not None:
            if r["coin_pct"] >= T_GOD:
                tier = "神作候选"
            elif r["coin_pct"] >= T_GOOD:
                tier = "优秀候选"
            elif r["coin_pct"] < T_NORMAL:
                tier = "垃圾候选"
        if r["dur"] and r["dur"] < DUR_CAP:
            tier = "一般候选" if tier in ("神作候选", "优秀候选") else tier
            firings.append(f"R2a 时长<{DUR_CAP}s 封顶一般")
        elif r["dur"] and r["dur"] < DUR_EXEC:
            if tier == "神作候选":
                tier = "优秀候选"
                firings.append(f"R2b 时长<{DUR_EXEC}s 斩杀神作线→封顶优秀")
        if r["favcoin"] > R_FAVCOIN and r["fav"] > R_FAVRATE:
            if tier == "神作候选":
                tier = "优秀候选"
            firings.append(f"R3 吃灰嫌疑(藏/币={r['favcoin']:.0f}, 藏={r['fav']:.1%}) 封顶优秀")
        if r["like"] > R_EDGE_LIKE and r["coin"] < R_EDGE_COIN and r["fav"] > R_EDGE_FAV:
            if tier == "神作候选":
                tier = "优秀候选"
            firings.append("R4 擦边三连(赞高币低藏高) 降档")
        r["v3"] = tier
        r["firings"] = firings

    pool = [r for r in pop.values() if r["coin_pct"] is not None]
    fresh = [r for r in pool if r["bvid"] not in labeled_bv]
    old = {r["bvid"]: r for r in pool if r["bvid"] in labeled_bv}
    print(f"[v3] 可判 {len(pool)} | 未审 {len(fresh)} | 已审锚定 {len(old)}")

    # ── 分层抽样 ──
    def pick(pred, n, exclude=()):
        c = [r for r in fresh if pred(r) and r["bvid"] not in exclude]
        random.shuffle(c)
        return c[:n]

    sample = []
    # 1 锚定样例（已判 5 条，每个人判档位各取 1 条）
    lab = json.load(open(os.path.join(MINE, "elabation_flow_labels.json"), encoding="utf-8"))["labels"]
    lab_group = {j["bvid"]: j.get("group", "") for j in lab}
    anchors = []
    for want_tier in ("神作", "优秀", "实用吃灰类", "垃圾/低创/擦边", "不典型/存疑"):
        c = [r for r in old.values() if lab_group.get(r["bvid"]) == want_tier]
        random.shuffle(c)
        if c:
            anchors.append(c[0])
        else:  # 该档无已判样本时从旧池随机补
            c2 = [r for r in old.values() if r["bvid"] not in {a["bvid"] for a in anchors}]
            random.shuffle(c2)
            if c2:
                anchors.append(c2[0])
    # 2 神作候选 top（确认锚）
    sample += sorted([r for r in fresh if r["v3"] == "神作候选" and r["coin_pct"] >= T_GOD],
                     key=lambda r: -r["coin_pct"])[:10]
    # 3 神作/优秀边界
    sample += pick(lambda r: T_GOOD <= r["coin_pct"] < T_GOD, 12)
    # 4 优秀/一般边界
    sample += pick(lambda r: T_NORMAL <= r["coin_pct"] < T_GOOD, 10)
    # 5 一般/垃圾边界
    sample += pick(lambda r: r["coin_pct"] < T_NORMAL, 8)
    # 6 规则冲突：高投币 × 短时长
    sample += pick(lambda r: r["coin_pct"] >= T_GOD and r["dur"] and r["dur"] < DUR_EXEC, 5)
    # 7 规则冲突：高投币 × 吃灰嫌疑
    sample += pick(lambda r: r["coin_pct"] >= T_GOD and r["favcoin"] > R_FAVCOIN and r["fav"] > R_FAVRATE, 5)
    # 8 擦边三连结构
    sample += pick(lambda r: r["like"] > R_EDGE_LIKE and r["coin"] < R_EDGE_COIN and r["fav"] > R_EDGE_FAV, 5)
    # 9 首页域样本
    home = set()
    hs = json.load(open(os.path.join(SDIR, "sample_20260903_185231.json"), encoding="utf-8"))
    for v in (hs.get("videos") or []):
        home.add(v.get("bvid"))
    sample += pick(lambda r: r["bvid"] in home, 8)
    # 10 随机对照
    sample += pick(lambda r: True, 7)

    # 去重
    seen, final = set(), []
    for r in sample + anchors:
        if r["bvid"] not in seen:
            seen.add(r["bvid"])
            final.append(r)
    print(f"[v3] 第二轮筛查样本 {len(final)} 条（含锚定 {len(anchors)}）")

    # ── HTML ──
    def row_html(i, r, anchor=None):
        fir = "；".join(r["firings"]) if r["firings"] else "—"
        anch = f'<div class="m" style="color:{AMB}">Elabation 前判：{anchor}</div>' if anchor else ""
        return (f'<tr><td class="num">{i}</td><td class="num"><b>{r["coin_pct"]:.2f}</b></td>'
                f'<td><span class="tag">{r["v3"].replace("候选","")}</span></td>'
                f'<td class="num">{r["cbi"] if r["cbi"] is not None else "—"}</td>'
                f'<td class="num">{r["view"]:,}</td><td class="num">{r["dur"] or "—"}s</td>'
                f'<td>{r["coin"]:.2%} / {r["fav"]:.2%} / {r["like"]:.2%}</td>'
                f'<td class="num">{r["favcoin"]:.0f}</td>'
                f'<td class="num">{fir}</td>'
                f'<td><a href="https://www.bilibili.com/video/{r["bvid"]}" target="_blank">'
                f'{html.escape(r["title"][:42])}</a></td>'
                f'<td class="blank">＿＿＿</td></tr>{anch}')

    AMB = "#C2803A"
    # 简化：锚定的前判直接查 labels
    lab = json.load(open(os.path.join(MINE, "elabation_flow_labels.json"), encoding="utf-8"))["labels"]
    labmap = {j["bvid"]: j["verdict"][:40] for j in lab}
    anchor_rows = "".join(row_html(i, r, labmap.get(r["bvid"], "已判")) for i, r in enumerate(anchors, 1))
    body_rows = "".join(row_html(i, r) for i, r in enumerate(final, len(anchors) + 1))

    doc = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>v3 第二轮筛查名录</title>
<style>
:root{{--ink:#081F5C;--data1:#334EAC;--data2:#7096D1;--data3:#BAD6EB;--paper:#F7F2EB;--shadow:#E3DACB;--sub:#5B7EC2;--dim:#9FB6D4;--amber:#C2803A}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--paper);color:var(--ink);font:14px/1.9 -apple-system,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif}}
.wrap{{max-width:1240px;margin:0 auto;padding:0 22px 80px}}
header.hero{{padding:50px 0 22px;border-bottom:1px solid var(--shadow)}}
.kicker{{font-size:11px;letter-spacing:4px;color:var(--data1);border:1px dashed var(--data2);display:inline-block;padding:4px 14px;border-radius:999px;margin-bottom:18px}}
h1{{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:32px;font-weight:900;letter-spacing:2px}}
.hero .lede{{font-size:14px;color:var(--sub);margin-top:10px}}
.kpirow{{display:flex;gap:14px;flex-wrap:wrap;margin:16px 0}}
.kpi{{flex:1 1 150px;background:#EFE8DA;padding:12px 15px}}
.kpi .n{{font-family:Georgia,serif;font-size:23px;color:var(--ink)}}
.kpi .d{{font-size:11.5px;color:var(--sub);line-height:1.5;margin-top:2px}}
nav{{position:sticky;top:0;background:var(--paper);border-bottom:1px solid var(--shadow);z-index:9;font-size:12px;padding:9px 0}}
nav a{{color:var(--sub);text-decoration:none;margin-right:12px}}
section{{padding:38px 0 10px;border-bottom:1px solid var(--shadow)}}
.sn{{font-size:11px;letter-spacing:3px;color:var(--data2)}}
h2{{font-family:'Kaiti SC','STKaiti','KaiTi',serif;font-size:23px;margin:6px 0 10px}}
p{{margin:10px 0}}
p.note{{font-size:12.5px;color:var(--sub)}}
table{{border-collapse:collapse;width:100%;margin:14px 0;font-size:12px;background:#fdfcf9}}
th{{color:var(--data1);font-weight:600;border-bottom:2px solid var(--data2);padding:6px 7px;text-align:left;font-size:11px;white-space:nowrap}}
td{{border-bottom:1px solid var(--shadow);padding:6px 7px;vertical-align:top}}
td.num{{font-family:Georgia,serif;white-space:nowrap}}
td.blank{{color:#C9C0B0;letter-spacing:2px}}
.tag{{font-size:10.5px;border:1px solid var(--data2);color:var(--data1);border-radius:3px;padding:1px 6px;white-space:nowrap}}
a{{color:var(--data1);text-decoration:none}}
a:hover{{text-decoration:underline}}
.m{{font-family:Georgia,serif;font-size:11.5px;color:var(--data1);margin-top:2px}}
.foot{{padding:30px 0 10px;font-size:11.5px;color:var(--dim);letter-spacing:1px}}
</style></head><body><div class="wrap">
<header class="hero">
  <div class="kicker">v3 第二轮筛查 · 主动学习采样 · 仅本地</div>
  <h1>v3 评分筛查名录</h1>
  <div class="lede">草案规则 v0 对参照库全量判档后，按信息量分层抽样：档位边界带 / 规则冲突 /
  擦边三连 / 首页域 / 随机对照 / 已判锚定。你的一轮判定同时完成：阈值校准、规则验证、新标签入账。</div>
</header>
<nav><a href="#s1">锚定</a><a href="#s2">边界与冲突</a><a href="#s3">完整特征表</a><a href="cbi-edge-review.html">擦边子报告</a><a href="flow-god-review.html">神作端名录</a></nav>
<div class="kpirow">
  <div class="kpi"><div class="n">{len(final)}</div><div class="d">本轮待审（不含锚定）</div></div>
  <div class="kpi"><div class="n">{len(anchors)}</div><div class="d">锚定样例（你已判）</div></div>
  <div class="kpi"><div class="n">{len(pop)}</div><div class="d">参照库总量</div></div>
  <div class="kpi"><div class="n">v0</div><div class="d">规则版本（阈值待你校准）</div></div>
</div>

<section id="s1">
  <div class="sn">一</div>
  <h2>锚定样例 · v3 预测 vs 你的前判</h2>
  <p class="note">这 5 条你已经判过。对照 v3 草案的预测档与你的判定——分歧处就是阈值要校准的地方。</p>
  <table><tr><th>#</th><th>带内投币百分位</th><th>v3 预测</th><th>旧CBI</th><th>播放</th><th>时长</th><th>币/藏/赞</th><th>藏币比</th><th>触发规则</th><th>标题</th><th>我的判定</th></tr>
  {anchor_rows}</table>
</section>

<section id="s2">
  <div class="sn">二</div>
  <h2>筛查样本</h2>
  <p class="note">列说明：带内投币百分位 = 同播放带内的投币率排名（0-1，v3 主锚）；v3 预测 = 草案规则判档
  （含 R2 时长罚 / R3 吃灰罚 / R4 擦边三连罚的触发记录）；分歧最大、触发规则最多的行信息量最高。
  请独立判定后再看 v3 预测列。</p>
  <table><tr><th>#</th><th>带内投币百分位</th><th>v3 预测</th><th>旧CBI</th><th>播放</th><th>时长</th><th>币/藏/赞</th><th>藏币比</th><th>触发规则</th><th>标题</th><th>我的判定</th></tr>
  {body_rows}</table>
</section>

<footer class="foot">v3 第二轮筛查名录 · 本地存档 · 不上传 · 阈值校准数据回填 elabation_flow_labels.json 同构格式</footer>
</div></body></html>"""

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"[v3] 名录 -> {OUT}（样本 {len(final)} + 锚定 {len(anchors)}）")


if __name__ == "__main__":
    main()
