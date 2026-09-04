# -*- coding: utf-8 -*-
"""一次性风控探针（2026-09-03 交接版）：匿名通道 2 请求，判当前出口 IP 是否仍被封。

只读、不重试（tries=1）、不循环、不写库；打印 B 站真实返回码。
用法： python engine/probe_once.py
退出码： 0=通道畅通  3=通道仍被封  2=无法探测（样本库缺 owner_mid）
"""
import glob
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient, UA  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDIR = os.path.join(ROOT, "data", "samples")


def pick_bvid():
    """从既有样本库取一个真实 bvid（本地数据，零编造）。"""
    for pat in ("sample_*.json", "ecosystem_*.json"):
        for fn in sorted(glob.glob(os.path.join(SDIR, pat)), reverse=True):
            try:
                for v in json.load(open(fn, encoding="utf-8")).get("videos") or []:
                    if v.get("bvid") and (v.get("stat") or {}).get("view", 0) > 10000:
                        return v["bvid"]
            except Exception:
                continue
    return None


def main():
    bv = pick_bvid()
    if not bv:
        print("[probe] 样本库无 bvid，无法探测")
        sys.exit(2)
    cli = BiliClient(interval=0.8)
    # 请求1：主页 warmup 拿 buvid3（与挖掘器同款前置）
    try:
        import re
        import urllib.request
        req = urllib.request.Request("https://www.bilibili.com/", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            for sc in (resp.headers.get_all("Set-Cookie") or []):
                m = re.match(r"([^=]+)=([^;]*)", sc)
                if m:
                    cli.cookies[m.group(1)] = m.group(2)
        print(f"[probe] warmup OK, cookies: {', '.join(cli.cookies.keys()) or 'none'}")
    except Exception as e:
        print(f"[probe] warmup failed: {e}")
    # 请求2：view 详情解析真实 uploader mid（旧样本无 owner_mid 字段）
    try:
        v = cli.fetch_view(bv)
        mid = v.get("owner_mid")  # fetch_view 契约：owner=名字字符串，owner_mid=数字 mid
        if not mid:
            print(f"[probe] fetch_view 未返回 owner_mid（bvid={bv}）")
            sys.exit(2)
        print(f"[probe] fetch_view OK：bvid={bv} → mid={mid}（code 0，匿名详情通道畅通）")
    except Exception as e:
        print(f"[probe] fetch_view BLOCKED：{e} → 通道仍被封")
        sys.exit(3)
    # 请求3：收藏夹接口（今晚被封堵的正是这一类）
    try:
        d = cli.get_json("https://api.bilibili.com/x/v3/fav/folder/created/list-all",
                         {"up_mid": mid, "type": 2, "rid": 0}, tries=1)
        n = len((d or {}).get("list") or [])
        print(f"[probe] 匿名收藏夹接口 OK：mid={mid} 返回 {n} 个夹 → 通道畅通，可发车")
    except Exception as e:
        print(f"[probe] 匿名收藏夹接口 BLOCKED：{e} → 通道仍被封")
        sys.exit(3)


if __name__ == "__main__":
    main()
