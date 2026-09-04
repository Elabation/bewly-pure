# -*- coding: utf-8 -*-
"""从 edgehunt2 JSON 捞人工审核名单（零请求）。"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
j = json.load(open(os.path.join(MINE, "r4_edgehunt2_20260905.json"), encoding="utf-8"))
scored = j["scored"]

print("== A组 真·擦边物种代表（搜索 top 播放，R4 全未触发）==")
for r in scored:
    if r["src"] == "search":
        print(f"  [{r['kw']}] {r['bvid']} 《{r['title'][:34]}》 播放{r['view']:,} 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%} 分区:{r['tname']}")

print("\n== B组 R4触发·疑似无辜（低带正常行为）==")
for b in ["BV1qh8z6JEuz", "BV1nWb96tE47", "BV1Qm421G7kh", "BV1uLth6rErU", "BV1RCxJevEHe"]:
    r = next((x for x in scored if x["bvid"] == b), None)
    if r:
        print(f"  {r['bvid']} 《{r['title'][:34]}》 播放{r['view']:,} 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%} 分区:{r['tname']} R4={r['r4']}")

print("\n== C组 R4触发·内容存疑（软擦边嫌疑，需人工裁决）==")
sus_kw = ["水手服", "小女友", "女友感", "cos", "cos]", "黑色？还是白色", "小爱", "姐姐", "萝莉", "女仆"]
seen = set()
n = 0
for r in sorted(scored, key=lambda x: -x["like_rate"]):
    if r["r4"] and r["bvid"] not in seen and any(k in r["title"] for k in sus_kw):
        seen.add(r["bvid"])
        n += 1
        print(f"  {r['bvid']} 《{r['title'][:38]}》 播放{r['view']:,} 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%} 分区:{r['tname']}")
        if n >= 12:
            break

print("\n== D组 边界样本（三条件都贴线但未触发）==")
for b in ["BV1wrcLzeEQw"]:
    r = next((x for x in scored if x["bvid"] == b), None)
    if r:
        print(f"  {r['bvid']} 《{r['title'][:34]}》 赞{r['like_rate']:.1%} 币{r['coin_rate']:.1%} 藏{r['fav_rate']:.1%} R4={r['r4']}")
