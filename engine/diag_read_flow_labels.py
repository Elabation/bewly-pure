# -*- coding: utf-8 -*-
"""提取 Elabation 95 条神作端判定 + 当场验证「投币判别」与罚项假说"""
import json
import os
import re
import statistics
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DESK = r"C:\Users\33768\Desktop\神作用户流 · 神作端名录.html"
MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fav_mine")

html = open(DESK, encoding="utf-8").read()
rows = re.findall(
    r'<tr><td class="num">(\d+)</td><td class="num"><b>([\d.]+)</b></td>'
    r'<td class="num">(\d+)</td><td>([^<]*)</td>'
    r'<td class="num">([\d,]+)</td>'
    r'<td>([\d.]+)% / ([\d.]+)% / ([\d.]+)%</td><td>(档案型|表态型)</td>'
    r'<td><a href="[^"]*?(BV1[A-Za-z0-9]+)"[^>]*>(.*?)</a></td>'
    r'<td class="num">(.*?)</td>'
    r'<td class="blank">(.*?)</td></tr>', html)

judged = []
for rank, cbi, inflow, prov, view, coin, fav, like, shape, bv, title, already, verdict in rows:
    v = verdict.strip()
    if not v or "＿＿＿" in v:
        continue
    judged.append({"rank": int(rank), "cbi": float(cbi), "inflow": int(inflow), "prov": prov.strip(),
                   "view": int(view.replace(",", "")), "coin": float(coin) / 100, "fav": float(fav) / 100,
                   "like": float(like) / 100, "shape": shape, "bvid": bv, "title": title,
                   "verdict": v})

print(f"已填判定 {len(judged)} / {len(rows)} 行")

# ── 分组（否定感知：「不可能神作/还有待考虑/够不到神作」先剥夺神作候选资格）──
NEG = ("不可能神作", "神作还有待考虑", "够不到神作", "神作还有待考虑，这种不典型", "门槛要更高", "不可能是神作", "很难神")

def group(v):
    if any(k in v for k in ("低创", "垃圾", "狗屎", "擦边", "恶心", "自慰", "引流")):
        return "垃圾/低创/擦边"
    negated = any(k in v for k in NEG)
    if ("神作" in v) and not negated:
        return "神作"
    if any(k in v for k in ("吃灰", "教学", "教程", "实用", "跟练")):
        return "实用吃灰类"
    if any(k in v for k in ("优秀", "值得", "高质", "精良")):
        return "优秀"
    return "不典型/存疑"

groups = defaultdict(list)
for j in judged:
    j["group"] = group(j["verdict"])
    groups[j["group"]].append(j)

print("\n=== 分组验证：投币判别假说（Elabation：「看投币可以秒」）===")
print(f"{'组':<14}{'n':>4}{'CBI中位':>9}{'投币中位':>9}{'收藏中位':>9}{'点赞中位':>9}{'时长中位':>9}")
summary = {}
for gname in ("神作", "优秀", "实用吃灰类", "垃圾/低创/擦边", "不典型/存疑"):
    gs = groups.get(gname) or []
    if not gs:
        continue
    med = lambda k: statistics.median([x[k] for x in gs])
    med_dur = statistics.median([x.get("dur", 0) for x in gs]) if gs and "dur" in gs[0] else 0
    summary[gname] = {"n": len(gs),
                      "cbi_med": round(med("cbi"), 2), "coin_med": round(med("coin"), 4),
                      "fav_med": round(med("fav"), 4), "like_med": round(med("like"), 4),
                      "members": [(x["rank"], x["cbi"], x["bvid"], x["verdict"][:30]) for x in gs]}
    print(f"{gname:<14}{len(gs):>4}{med('cbi'):>9.2f}{med('coin'):>9.2%}{med('fav'):>9.2%}{med('like'):>9.2%}")

json.dump({"n_judged": len(judged), "n_rows": len(rows), "summary": summary, "labels": judged},
          open(os.path.join(MINE, "elabation_flow_labels.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"\n[done] {len(judged)} 条标注（含分组） -> data/fav_mine/elabation_flow_labels.json")
