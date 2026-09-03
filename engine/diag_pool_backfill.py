# -*- coding: utf-8 -*-
"""全池 view 回填——封面 pic + pubdate + UP 名 + 最新计数，一枪全齐（匿名通道）。

目标：公共池全部条目（约 4.9K）。间隔 0.6s ≈ 50 分钟。
落盘 data/flow_graph/pool_view_backfill.json {bvid: {pic,pubdate,owner,dur,stat{view,coin,fav,like}}}
每 100 条 checkpoint；已有有效条目跳过（可断点续跑）。
"""
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402
from god_pool import build_pool, FG  # noqa: E402

OUT = os.path.join(FG, "pool_view_backfill.json")
INTERVAL = 0.6
sys.stdout.reconfigure(line_buffering=True)


def main():
    pool, _ = build_pool()
    bf = {}
    if os.path.exists(OUT):
        try:
            bf = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            bf = {}
    targets = sorted((r["bvid"] for b, r in pool.items() if b not in bf or not (bf[b] or {}).get("pic")),
                     key=lambda b: (0 if pool[b]["tier"] == "神作候选" else 1, -(pool[b].get("pct") or 0)))
    print(f"[pool-view] 待回填 {len(targets)}（已有 {len(bf)}）", flush=True)
    cli = BiliClient(interval=INTERVAL)
    done, fails = 0, 0
    t0 = time.time()
    for b in targets:
        try:
            v = cli.fetch_view(b)
            st = v.get("stat") or {}
            pic = v.get("pic") or ""
            if pic.startswith("http://"):
                pic = "https://" + pic[7:]
            bf[b] = {"pic": pic, "pubdate": v.get("pubdate"), "owner": v.get("owner") or "",
                     "dur": v.get("duration") or 0, "tname": v.get("tname") or "",
                     "stat": {"view": st.get("view") or 0, "coin": st.get("coin") or 0,
                              "fav": st.get("favorite") or 0, "like": st.get("like") or 0,
                              "share": st.get("share") or 0, "reply": st.get("reply") or 0}}
        except Exception as e:
            bf[b] = {"error": str(e)[:80]}
            fails += 1
        done += 1
        if done % 100 == 0:
            try:
                json.dump(bf, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
            except Exception as e:
                print(f"[ckpt-warn] {e}")
            el = time.time() - t0
            print(f"[ckpt] {done}/{len(targets)} fail={fails} 用时 {el:.0f}s 剩余约 {el/done*(len(targets)-done):.0f}s", flush=True)
    json.dump(bf, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[done] {len(bf)} 条 fail={fails} -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
