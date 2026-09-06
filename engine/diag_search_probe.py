# -*- coding: utf-8 -*-
"""搜索通道探针：打印原始响应定位失败原因。"""
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
    d = cli.get_json("https://api.bilibili.com/x/web-interface/search/type",
                     {"search_type": "video", "keyword": "Neuro-sama", "page": 1}, sign_wbi=True, tries=1)
    s = str(d)
    print("code:", (d or {}).get("code"), "| message:", (d or {}).get("message"))
    print("raw[:300]:", s[:300])
except Exception as e:
    print("EXC:", str(e)[:300])
