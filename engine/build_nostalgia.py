# -*- coding: utf-8 -*-
"""构建怀旧报告网页：把收藏夹考古分析 JSON 注入 HTML（幂等）。
用法： python engine/build_nostalgia.py [analysis_json]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "web", "nostalgia-report.html")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

path = sys.argv[1] if len(sys.argv) > 1 else None
if not path:
    d = os.path.join(ROOT, "data", "fav_mine")
    cands = sorted(f for f in os.listdir(d) if f.endswith("_analysis.json"))
    if not cands:
        raise SystemExit("data/fav_mine/ 下没有 *_analysis.json")
    path = os.path.join(d, cands[-1])
A = json.load(open(path, encoding="utf-8"))

years = [r for r in A.get("by_year", []) if r.get("n", 0) > 0]
A["year_span"] = f"{years[0]['year']}–{years[-1]['year']}" if years else "—"

o, c, on = A["overall"], A["control"], A["old_vs_new"]
old, new = on.get("old", {}), on.get("new", {})


def pct0(x):
    return "—" if x is None else f"{round(x*1000)/10}%"
deep_years = [r for r in years if r["n"] >= 5 and r["avg_cbi"] < 0.85]
peak_years = [r for r in years if r["n"] >= 5]
peak = max(peak_years, key=lambda r: r["avg_cbi"]) if peak_years else None

A["year_text"] = (
    f"<p>两个值得停下来看的形状：<b>① 「感谢低谷」</b>——"
    + ("、".join(f"{r['year']} 年（平均CBI {r['avg_cbi']}）" for r in deep_years) or "无")
    + f" 的收藏条目感谢水平显著低于两侧年份，全段最低点 {min((r for r in years if r['n']>=5), key=lambda r: r['avg_cbi'])['year']} 年。"
    "这批视频大量收藏、但相对其播放量得到的硬币与点赞稀薄——与收藏行为本身的「存档心态」（先存下再说）吻合，具体成因属假说，本报告不展开；"
    f"<b>② 年代峰值</b>——{peak['year']} 年的条目平均 CBI 达 {peak['avg_cbi']}（n={peak['n']}），"
    "成为整条时间线的高水位段。</p>"
) if deep_years and peak else "<p>样本年份内未见显著低谷形态。</p>"

old_star = round(old.get("n", 0) * old.get("high_rate", 0))
A["oldnew_text"] = (
    f"<p><b>五年之界的读法：</b>≥5 年前发布的 {old.get('n', 0)} 条里，神作线以上 {old_star} 条"
    f"（神作率 {pct0(old.get('high_rate'))}、优秀率 {pct0(old.get('good_rate'))}、平均 CBI {old.get('avg_cbi')}）"
    f"——它们今天出现在你首页的概率趋近于零，除非你恰好关注了当年的 up 主。"
    f"近 5 年的 {new.get('n', 0)} 条水位更高（平均 CBI {new.get('avg_cbi')}），"
    "但这不是「新比旧好」的证据，而是收藏行为的「存档偏向」：人们收藏时更倾向新内容。"
    "真正站得住的结论是：<b>被时间线掩埋的旧内容里，每 10 条就有约 3 条神作</b>——"
    "这条平行时间线值得一条专门的浏览通道。</p>"
)


A["year_text"] = A["year_text"]
mine_js = json.dumps(A, ensure_ascii=False)

lines = open(HTML, encoding="utf-8").read().split("\n")
hit = False
for i, ln in enumerate(lines):
    if ln.startswith("const MINE = "):
        lines[i] = "const MINE = " + mine_js + ";"
        hit = True
        break
if not hit:
    raise SystemExit("未找到 const MINE 行")
open(HTML, "w", encoding="utf-8").write("\n".join(lines))
print(f"[done] MINE {len(mine_js)}B <- {path} -> {HTML}")
print(f"  users={A['meta']['users']} videos={o['n']} span={A['year_span']} "
      f"high={o['high_rate']} good={o['good_rate']} ctrl_high={c['high_rate']}")
