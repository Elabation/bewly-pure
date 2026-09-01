# -*- coding: utf-8 -*-
"""下载 mstation bundle 并 grep feed 接口路径"""
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
base = "https://s1.hdslb.com/bfs/static/jinkela/mstation-h5-new/"
files = ["mstation.60188cd1fcf202eb70f6abf67f4b7fee2b8d51bc.js",
         "0.mstation.60188cd1fcf202eb70f6abf67f4b7fee2b8d51bc.js",
         "2.mstation.60188cd1fcf202eb70f6abf67f4b7fee2b8d51bc.js",
         "6.mstation.60188cd1fcf202eb70f6abf67f4b7fee2b8d51bc.js",
         "14.mstation.60188cd1fcf202eb70f6abf67f4b7fee2b8d51bc.js"]
pats = re.compile(r"/x/(web-interface|v2|ppe)/[A-Za-z0-9/_-]+")
hits = {}
for fn in files:
    try:
        req = urllib.request.Request(base + fn, headers={"User-Agent": UA})
        js = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
        found = set(pats.findall(js.replace("\\/", "/")))
        for a, b in found:
            key = f"/x/{a}/{b}"
            hits[key] = hits.get(key, 0) + 1
        print(f"{fn[:24]}... len={len(js)//1024}KB apis={len(found)}")
    except Exception as e:
        print(f"{fn[:24]}... FAIL {e}")
feed_like = sorted(k for k in hits if re.search(r"feed|rcmd|index|recommend", k, re.I))
print("\n== feed-like APIs ==")
for k in feed_like:
    print("  ", k)
