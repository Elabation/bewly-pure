# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\work_space\b站插件项目\bilibili-clean\engine")
from collect_stats import BiliClient  # noqa: E402

cli = BiliClient(interval=0.5)
for rid in (1, 3, 4, 36, 129, 217, 211, 119):
    try:
        d = cli.get_json("https://api.bilibili.com/x/web-interface/ranking/region", {"rid": rid, "day": 3}, tries=1)
        items = d.get("data") or []
        tn = items[0].get("tname", "") if items else ""
        sample = items[0]["title"][:20] if items else ""
        print(f"rid{rid}: n={len(items)} tname={tn!r} 样题={sample}")
    except Exception as e:
        print(f"rid{rid}: FAIL {str(e)[:60]}")
