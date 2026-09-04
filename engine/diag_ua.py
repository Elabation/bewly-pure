# -*- coding: utf-8 -*-
"""UA 指纹对照实验（2026-09-03）：验证 fav_miner 预热裸 UA 是否导致收藏夹接口喂空数据。

三组同 mid 对照（全匿名 3 请求 + 1 次 warmup 复用）：
  A: 裸 UA "Mozilla/5.0" 签发 cookie → list-all
  B: 完整 Chrome UA 签发 cookie → list-all
  C: 无 cookie 直连 → list-all
目标 mid = 3546664153385147（诊断已证实有 3 个公开夹）。
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import UA  # noqa: E402

MID = 3546664153385147
URL = "https://api.bilibili.com/x/v3/fav/folder/created/list-all"


def warmup(ua):
    req = urllib.request.Request("https://www.bilibili.com/", headers={"User-Agent": ua})
    cookies = {}
    with urllib.request.urlopen(req, timeout=15) as resp:
        for sc in (resp.headers.get_all("Set-Cookie") or []):
            m = re.match(r"([^=]+)=([^;]*)", sc)
            if m:
                cookies[m.group(1)] = m.group(2)
    return cookies


def list_all(cookies):
    qs = urllib.parse.urlencode({"up_mid": MID, "type": 2, "rid": 0})
    req = urllib.request.Request(URL + "?" + qs, headers={
        "User-Agent": UA, "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
        "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", "replace")


def report(tag, cookies):
    body = list_all(cookies)
    try:
        j = json.loads(body)
        d = j.get("data")
        n = len((d or {}).get("list") or []) if isinstance(d, dict) else f"data={d!r}"
        print(f"[{tag}] code={j.get('code')} folders={n}")
    except Exception:
        print(f"[{tag}] raw: {body[:200]}")


def main():
    print(f"目标 mid={MID}（已知有 3 个公开夹）")
    a = warmup("Mozilla/5.0")
    print(f"[warmA] bare-UA cookies: {sorted(a.keys())}")
    report("A 裸UA-cookie", a)
    b = warmup(UA)
    print(f"[warmB] full-UA cookies: {sorted(b.keys())}")
    report("B 完整UA-cookie", b)
    report("C 无cookie", {})
    a2 = warmup("Mozilla/5.0")
    report("A2 裸UA-cookie 复测", a2)


if __name__ == "__main__":
    main()
