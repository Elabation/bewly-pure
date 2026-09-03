# -*- coding: utf-8 -*-
"""封面回填——player/pic 轻接口 × 全池（匿名通道）。

bvid → https://api.bilibili.com/x/player/pic → data.pic（CDN 封面地址）
落盘 data/flow_graph/cover_backfill.json {bvid: pic}
每 100 条 checkpoint，可断点续跑。间隔 0.5s，约 45 分钟。
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

COVER_FILE = os.path.join(FG, "cover_backfill.json")


def main():
    pool, _ = build_pool()
    covers = {}
    if os.path.exists(COVER_FILE):
        try:
            covers = json.load(open(COVER_FILE, encoding="utf-8"))
        except Exception:
            covers = {}
    targets = sorted((r["bvid"] for b, r in pool.items() if b not in covers),
                     key=lambda b: (0 if pool[b]["tier"] == "神作候选" else 1, -(pool[b].get("pct") or 0)))
    print(f"[cover] 待回填 {len(targets)}（已有 {len(covers)}）")
    cli = BiliClient(interval=0.5)
    done, fails = 0, 0
    t0 = time.time()
    for i, b in enumerate(targets):
        try:
            d = cli.get_json("https://api.bilibili.com/x/player/pic", {"bvid": b}, tries=1)
            pic = ((d or {}).get("data") or {}).get("pic") or ""
            if pic.startswith("http://"):
                pic = "https://" + pic[7:]
            covers[b] = pic
        except Exception:
            fails += 1
        done += 1
        if done % 100 == 0:
            try:
                json.dump(covers, open(COVER_FILE, "w", encoding="utf-8"), ensure_ascii=False)
            except Exception as e:
                print(f"[ckpt-warn] {e}")
            el = time.time() - t0
            print(f"[ckpt] {done}/{len(targets)} fail={fails} 用时 {el:.0f}s 剩余约 {el/done*(len(targets)-done):.0f}s")
    json.dump(covers, open(COVER_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[done] covers {len(covers)} fail={fails} -> {COVER_FILE}")


if __name__ == "__main__":
    main()
