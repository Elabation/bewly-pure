# -*- coding: utf-8 -*-
"""纵深链时间方向判定（零请求）。"""
import glob
import json
import statistics
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

p = sorted(glob.glob(r"D:\work_space\b站插件项目\bilibili-clean\data\flow_graph\godflowdeep_*.json"))[-1]
d = json.load(open(p, encoding="utf-8"))
for fl in d["flows"]:
    ch = [c for c in fl["chain"] if c.get("pubdate")]
    if len(ch) < 4:
        print(fl["seed"]["bucket"], "链太短（<4 节点）")
        continue
    head = [c["pubdate"] for c in ch[:3]]
    tail = [c["pubdate"] for c in ch[-3:]]
    hm = time.strftime("%Y-%m", time.localtime(statistics.median(head)))
    tm = time.strftime("%Y-%m", time.localtime(statistics.median(tail)))
    drift = "回溯(向老经典)" if statistics.median(tail) < statistics.median(head) else "向新"
    print(f"{fl['seed']['bucket']}: 链头中位 {hm} -> 链尾中位 {tm} | 漂移 = {drift} | 链长 {len(ch)}")
