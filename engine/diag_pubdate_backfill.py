# -*- coding: utf-8 -*-
"""pubdate/UP 回填——为货架网站的年代编排补齐缺口（匿名通道）。

目标：池内缺 pubdate 的条目（当前 652）。fetch_view 每次顺带带回最新 stat 与 UP 名。
落盘：data/flow_graph/pubdate_backfill.json {bvid: {pubdate, owner, stat{...}, dur}}
每 50 条 checkpoint 一次，可断点续跑（已有条目跳过）。
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
from god_pool import build_pool, load_backfill, FG  # noqa: E402

CAP = 900


def main():
    pool, _ = build_pool()
    bf = load_backfill()
    targets = [r for b, r in pool.items()
               if b not in bf and not r.get("pubdate")]
    # 神作优先，再按 pct 降序
    targets.sort(key=lambda r: (0 if r["tier"] == "神作候选" else 1, -(r["pct"] or 0)))
    targets = targets[:CAP - 0]
    print(f"[backfill] 待回填 {len(targets)}（已有 {len(bf)}）")
    cli = BiliClient(interval=0.8)
    done = 0
    t0 = time.time()
    for i, r in enumerate(targets):
        b = r["bvid"]
        try:
            v = cli.fetch_view(b)
            st = v.get("stat") or {}
            bf[b] = {"pubdate": v.get("pubdate"), "owner": v.get("owner") or "",
                     "dur": v.get("duration") or 0,
                     "stat": {"view": st.get("view") or 0, "coin": st.get("coin") or 0,
                              "fav": st.get("favorite") or 0, "like": st.get("like") or 0}}
        except Exception as e:
            bf[b] = {"error": str(e)[:80]}
        done += 1
        if done % 50 == 0:
            try:
                json.dump(bf, open(os.path.join(FG, "pubdate_backfill.json"), "w", encoding="utf-8"), ensure_ascii=False)
            except Exception as e:
                print(f"[ckpt-warn] dump fail: {e}")
            el = time.time() - t0
            print(f"[ckpt] {done}/{len(targets)} 用时 {el:.0f}s（剩余约 {el/done*(len(targets)-done):.0f}s）")
    out = os.path.join(FG, "pubdate_backfill.json")
    json.dump(bf, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    ok = sum(1 for v in bf.values() if "pubdate" in v)
    print(f"[done] {ok} 条带 pubdate -> {out}")


if __name__ == "__main__":
    main()
