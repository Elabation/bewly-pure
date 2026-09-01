# -*- coding: utf-8 -*-
"""探测 m.bilibili.com 移动版首页：feed 接口 + 页面结构线索"""
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
HDR = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}


def fetch(url, hdr=None):
    req = urllib.request.Request(url, headers=hdr or HDR)
    return urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")


html = fetch("https://m.bilibili.com/")
print("HTML len:", len(html))
print("title:", re.search(r"<title>(.*?)</title>", html, re.S).group(1) if re.search(r"<title>(.*?)</title>", html, re.S) else "?")
# 接口线索
for pat in (r"/x/web-interface/[a-z/]+", r"/x/v2/[a-z/]+", r"feed[/a-z]*rcmd", r"pugv?[a-z/]*feed"):
    hits = sorted(set(re.findall(pat, html)))
    if hits:
        print("API hits:", hits[:15])
# JS bundle
js = sorted(set(re.findall(r'https://[^"\']+\.js', html)))
print("JS bundles:", len(js))
for u in js[:12]:
    print("  ", u)
with open("m_index.html", "w", encoding="utf-8") as f:
    f.write(html)
