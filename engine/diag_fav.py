# -*- coding: utf-8 -*-
"""收藏夹接口诊断（2026-09-03 晨）：臂②四连熔断后，判定「IP 软封锁 vs 接口变更」。

全匿名 ~7 请求：2×fetch_view 解析真实 mid + 2×list-all 原始报文 + 1×collected/list + 1×匿名 reply。
不碰账号、不写库、不重试。打印原始 JSON 报文供人眼判读。
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
from collect_stats import BiliClient, UA  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDIR = os.path.join(ROOT, "data", "samples")


def raw_get(url, params, cookies):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + "?" + qs, headers={
        "User-Agent": UA, "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
        "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", "replace")


def main():
    cli = BiliClient(interval=1.0)
    try:
        req = urllib.request.Request("https://www.bilibili.com/", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            for sc in (resp.headers.get_all("Set-Cookie") or []):
                m = re.match(r"([^=]+)=([^;]*)", sc)
                if m:
                    cli.cookies[m.group(1)] = m.group(2)
        print(f"[diag] warmup OK: {', '.join(cli.cookies.keys()) or 'none'}")
    except Exception as e:
        print(f"[diag] warmup failed: {e}")

    # 取 4 个高播放样本 bvid → fetch_view 解析 mid + aid
    bvids = []
    for fn in sorted(os.listdir(SDIR)):
        if fn.startswith("sample_") and fn.endswith(".json"):
            try:
                for v in json.load(open(os.path.join(SDIR, fn), encoding="utf-8")).get("videos") or []:
                    if v.get("bvid") and (v.get("stat") or {}).get("view", 0) > 100000:
                        bvids.append(v["bvid"])
            except Exception:
                continue
        if len(bvids) >= 4:
            break
    mids, aid = [], None
    for bv in bvids:
        try:
            v = cli.fetch_view(bv)
            aid = aid or v.get("aid")
            mid = v.get("owner_mid")
            if mid:
                mids.append((bv, mid))
                print(f"[diag] fetch_view OK: {bv} → mid={mid}")
        except Exception as e:
            print(f"[diag] fetch_view {bv} failed: {e}")
        if len(mids) >= 2:
            break

    # list-all 原始报文（核心判据）
    for bv, mid in mids:
        try:
            body = raw_get("https://api.bilibili.com/x/v3/fav/folder/created/list-all",
                           {"up_mid": mid, "type": 2, "rid": 0}, cli.cookies)
            print(f"--- list-all mid={mid} ({bv}) raw {len(body)}B ---")
            print(body[:700])
        except Exception as e:
            print(f"[diag] list-all {mid} failed: {e}")

    # collected 变体
    if mids:
        try:
            body = raw_get("https://api.bilibili.com/x/v3/fav/folder/collected/list",
                           {"up_mid": mids[0][1], "ps": 20, "pn": 1, "platform": "web"}, cli.cookies)
            print(f"--- collected/list mid={mids[0][1]} raw {len(body)}B ---")
            print(body[:400])
        except Exception as e:
            print(f"[diag] collected failed: {e}")

    # 匿名评论区可行性（臂①③ 种子线）
    if aid:
        try:
            d = cli.get_json("https://api.bilibili.com/x/v2/reply",
                             {"type": 1, "oid": aid, "ps": 20, "pn": 1, "sort": 1}, tries=1)
            n = len((d or {}).get("replies") or [])
            print(f"[diag] 匿名 reply OK：{n} 条评论（aid={aid}）")
        except Exception as e:
            print(f"[diag] 匿名 reply BLOCKED：{e}")


if __name__ == "__main__":
    main()
