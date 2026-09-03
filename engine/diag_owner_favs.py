# -*- coding: utf-8 -*-
"""主页收藏夹全景——匿名通道：folder list-all + 每夹首页样本 + 特例热评补枪(ps=20)。

输出：文件夹清单 / 每夹抽样统计 / 与 mine_owner_113 快照交叉 / 特例热评指纹。
"""
import json
import os
import statistics
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
OWNER_MID = "3494381103352463"
TARGET = "BV1cBtc65EQc"
MAX_FOLDERS = 30


def main():
    cli = BiliClient(interval=0.8)
    out = {"mid": OWNER_MID, "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S")}

    # ---- 特例热评补枪（ps=20 上限）----
    aid = None
    try:
        v = cli.fetch_view(TARGET)
        aid = v.get("aid") or (v.get("stat") or {}).get("aid") or v.get("id")
    except Exception:
        pass
    if aid:
        try:
            d = cli.get_json("https://api.bilibili.com/x/v2/reply",
                             {"type": 1, "oid": aid, "ps": 20, "sort": 1}, tries=1)
            reps = ((d or {}).get("replies") or [])
            msgs = [(r.get("content") or {}).get("message") or "" for r in reps]
            out["case_comments"] = msgs
            print(f"[case] 特例热评 {len(msgs)} 条：")
            for m in msgs[:8]:
                print("   ·", (m[:60] + "…") if len(m) > 60 else m)
        except Exception as e:
            print(f"[case] 热评仍失败: {e}")

    # ---- 收藏夹清单 ----
    d = cli.get_json("https://api.bilibili.com/x/v3/fav/folder/created/list-all",
                     {"up_mid": OWNER_MID, "type": 2, "rid": 0}, tries=1)
    folders = (d or {}).get("list") or []
    print(f"\n[folders] 共 {len(folders)} 个收藏夹")
    for f in folders:
        print(f"   · [{f.get('id')}] {f.get('title')}（{f.get('media_count')} 条）")

    # ---- 旧快照交叉 ----
    old = {}
    try:
        mo = json.load(open(os.path.join(MINE, f"mine_owner_{OWNER_MID}.json"), encoding="utf-8"))
        old = {x["bvid"]: x for x in (mo.get("videos") or [])}
        print(f"[cross] 旧快照 113 条：档位分布 "
              f"{ {t: sum(1 for x in old.values() if x.get('tier') == t) for t in ('high', 'good', 'normal', 'low', 'junk', 'unproven')} }")
    except Exception as e:
        print(f"[cross] 旧快照读取失败: {e}")

    # ---- 每夹首页抽样 ----
    folders_out = []
    for f in folders[:MAX_FOLDERS]:
        mid_id, title, cnt = f.get("id"), f.get("title"), f.get("media_count") or 0
        try:
            d = cli.get_json("https://api.bilibili.com/x/v3/fav/resource/list",
                             {"media_id": mid_id, "pn": 1, "ps": 20, "order": "mtime", "platform": "web"},
                             tries=1)
        except Exception as e:
            print(f"   [skip] {title}: {e}")
            continue
        items = (d or {}).get("medias") or []
        rows = []
        for it in items:
            ci = it.get("cnt_info") or {}
            play = ci.get("play") or 0
            collect = ci.get("collect") or 0
            thumb = ci.get("thumb") or 0
            rows.append({
                "bvid": it.get("bvid"), "title": (it.get("title") or "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
                "play": play, "fav": collect, "like": thumb, "dur": it.get("duration") or 0,
                "fav_time": it.get("fav_time") or 0,
                "fav_rate": collect / max(1, play), "like_rate": thumb / max(1, play),
            })
        views = [r["play"] for r in rows if r["play"]]
        frs = [r["fav_rate"] for r in rows]
        in_old = sum(1 for r in rows if r["bvid"] in old)
        star = sorted(rows, key=lambda r: -r["fav_rate"])[:3]
        folders_out.append({"id": mid_id, "title": title, "media_count": cnt,
                            "sampled": len(rows), "in_old_snapshot": in_old,
                            "median_view": statistics.median(views) if views else 0,
                            "median_fav_rate": statistics.median(frs) if frs else 0,
                            "star_items": star, "items": rows})
        print(f"   [{mid_id}] {title}: 总 {cnt} ｜ 抽 {len(rows)}（旧快照命中 {in_old}）｜ 抽样播放中位 {folders_out[-1]['median_view']:,.0f} ｜ 藏率中位 {folders_out[-1]['median_fav_rate']:.1%}")
        for s in star:
            print(f"        ★ 藏率 {s['fav_rate']:.1%} · {s['play']:,}播放 · {(s['title'] or '')[:36]}")

    out["folders"] = folders_out
    out["n_folders"] = len(folders)
    out["total_media"] = sum(f.get("media_count") or 0 for f in folders)
    fn = os.path.join(MINE, f"fav_owner_snapshot_{time.strftime('%Y%m%d_%H%M%S')}.json")
    json.dump(out, open(fn, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n[done] 总收藏 {out['total_media']} 条 / {len(folders)} 夹 -> {fn}")


if __name__ == "__main__":
    main()
