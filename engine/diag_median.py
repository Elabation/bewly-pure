# -*- coding: utf-8 -*-
"""中位数伪影验证 + 独立真中位数——单一视频法 vs 逐指标独立中位"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fav_mine")

mfs = sorted((f for f in os.listdir(MINE)
              if f.startswith("favmine_merged_") and f.endswith(".json") and "_analysis" not in f),
             key=lambda f: os.path.getmtime(os.path.join(MINE, f)))
m = json.load(open(os.path.join(MINE, mfs[-1]), encoding="utf-8"))
vids = [v for v in (m.get("videos") or []) if (v.get("view") or 0) >= 3000]


def med_rate(key):
    vals = sorted(((v.get("stat") or {}).get(key, 0) / max(1, v.get("view") or 1)) for v in vids)
    return vals[len(vals) // 2]


print(f"n={len(vids)}（最新 merged: {mfs[-1]}）")
print(f"投币/播放 独立中位: {med_rate('coin'):.3%}")
print(f"收藏/播放 独立中位: {med_rate('favorite'):.3%}")
print(f"点赞/播放 独立中位: {med_rate('like'):.3%}")
favmed = sorted(vids, key=lambda v: (v.get("stat") or {}).get("favorite", 0) / max(1, v.get("view") or 1))[len(vids) // 2]
print(f"旧法（按收藏排序取单视频）该视频的币/赞: "
      f"{(favmed.get('stat') or {}).get('coin', 0) / max(1, favmed.get('view') or 1):.3%} / "
      f"{(favmed.get('stat') or {}).get('like', 0) / max(1, favmed.get('view') or 1):.3%}")
