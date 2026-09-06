# -*- coding: utf-8 -*-
"""view/related 通道探针（search 412 风控后的备用路径验证）。"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient

cli = BiliClient(interval=0.5)
try:
    v = cli.fetch_view("BV1GJ411x7h7")
    print("fetch_view OK:", (v.get("title") or "")[:30], "| view:", (v.get("stat") or {}).get("view"))
except Exception as e:
    print("fetch_view FAIL:", str(e)[:150])
try:
    d = cli.get_json("https://api.bilibili.com/x/web-interface/archive/related", {"aid": 390729720}, tries=1)
    items = d if isinstance(d, list) else []
    print("related OK:", len(items), "items")
except Exception as e:
    print("related FAIL:", str(e)[:150])
