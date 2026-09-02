# -*- coding: utf-8 -*-
"""账号存活检查（独立脚本，路径自解析——避开中文路径过命令行的编码坑）。"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
from collect_stats import BiliClient  # noqa: E402

sess_path = os.path.join(ROOT, "data", "fav_mine", ".sessdata")
cli = BiliClient(interval=0.5)
if os.path.exists(sess_path):
    cli.cookies["SESSDATA"] = open(sess_path, encoding="utf-8").read().strip()
d = cli.get_json("https://api.bilibili.com/x/web-interface/nav", {}, sign_wbi=True)
data = d.get("data") or {}
alive = bool(d.get("isLogin") or data.get("isLogin"))
print("ALIVE" if alive else "DEAD")
sys.exit(0 if alive else 2)
