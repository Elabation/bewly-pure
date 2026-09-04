# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\work_space\b站插件项目\bilibili-clean\engine")
from collect_stats import BiliClient  # noqa: E402

cli = BiliClient(interval=0.5)
for wbi in (False, True):
    for pn in (1, 2):
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/popular",
                             {"ps": 20, "pn": pn}, sign_wbi=wbi, tries=1)
            data = d.get("data") or {}
            lst = data.get("list") or []
            sample = lst[0].get("title", "")[:24] if lst else ""
            print(f"wbi={wbi} pn={pn}: code={d.get('code')} n={len(lst)} 样题={sample}")
        except Exception as e:
            print(f"wbi={wbi} pn={pn}: FAIL {str(e)[:80]}")
