# -*- coding: utf-8 -*-
"""洁净B站 · 数据采集脚本
从B站公开 API 采集一批视频的统计数据（播放/收藏/投币/点赞 + 时长/宽高比），
供评分权重与阈值校准使用。只走 API 元数据，不下载任何视频。

用法：
  python engine/collect_stats.py                    # 按 config/clean.config.json 的 collector 配置采集
  python engine/collect_stats.py --count 30         # 每来源最多30个
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# wbi 签名混淆表（来自 bilibili-API-collect）
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61,
    26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36,
    20, 34, 44, 52,
]


class BiliClient:
    """极简B站 API 客户端：urllib 实现，零第三方依赖，带节流/wbi签名/风控重试。"""

    def __init__(self, interval=0.4):
        self.interval = interval
        self.cookies = {}
        self.wbi_keys = None
        self._last_req = 0.0

    def _throttle(self):
        wait = self.interval - (time.time() - self._last_req)
        if wait > 0:
            time.sleep(wait + random.uniform(0, 0.1))
        self._last_req = time.time()

    def get_json(self, url, params=None, sign_wbi=False, tries=3, allow_codes=()):
        if params is None:
            params = {}
        if sign_wbi:
            if self.wbi_keys is None:
                self._load_wbi_keys()
            params = self._sign_wbi(params)
        qs = urllib.parse.urlencode(params)
        full = url + ("?" + qs if qs else "")
        last_err = None
        for i in range(tries):
            self._throttle()
            req = urllib.request.Request(full, headers={
                "User-Agent": UA,
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
                "Cookie": "; ".join(f"{k}={v}" for k, v in self.cookies.items()),
            })
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    for sc in (resp.headers.get_all("Set-Cookie") or []):
                        m = re.match(r"([^=]+)=([^;]*)", sc)
                        if m and m.group(1) not in self.cookies:
                            self.cookies[m.group(1)] = m.group(2)
                    payload = json.loads(resp.read().decode("utf-8", "replace"))
            except Exception as e:
                last_err = f"network: {e}"
                time.sleep(2 + i * 2)
                continue
            code = payload.get("code")
            if code == 0 or (allow_codes and code in allow_codes):
                return payload.get("data")
            last_err = f"code={code} msg={payload.get('message')}"
            if code in (-412, -352, -799):  # 风控，退避重试
                time.sleep(3 + i * 3)
                continue
            break
        raise RuntimeError(f"GET {url.split('?')[0]} failed: {last_err}")

    def _load_wbi_keys(self):
        # nav 未登录时 code=-101，但 data.wbi_img 仍然返回，允许通过
        data = self.get_json("https://api.bilibili.com/x/web-interface/nav",
                             allow_codes=(-101,)) or {}
        wbi = data.get("wbi_img")
        if not wbi:
            raise RuntimeError("nav 未返回 wbi_img")
        img_key = wbi["img_url"].rsplit("/", 1)[1].split(".")[0]
        sub_key = wbi["sub_url"].rsplit("/", 1)[1].split(".")[0]
        self.wbi_keys = (img_key, sub_key)

    def _sign_wbi(self, params):
        img_key, sub_key = self.wbi_keys
        mixin = img_key + sub_key
        mixin_key = "".join(mixin[i] for i in MIXIN_KEY_ENC_TAB)[:32]
        p = dict(params)
        p["wts"] = int(time.time())
        p = dict(sorted(p.items()))
        p = {k: "".join(c for c in str(v) if c not in "!'()*") for k, v in p.items()}
        q = urllib.parse.urlencode(p)
        p["w_rid"] = hashlib.md5((q + mixin_key).encode()).hexdigest()
        return p

    # ---------- 采集来源 ----------
    def collect_bvids(self, sources, per_source):
        bvids = []

        def add(bv, src):
            if bv and all(bv != b for b, _ in bvids):
                bvids.append((bv, src))

        if "ranking" in sources:
            try:
                data = self.get_json(
                    "https://api.bilibili.com/x/web-interface/ranking/v2",
                    {"rid": 0, "type": "all"})
                for it in (data.get("list") or [])[:per_source]:
                    add(it.get("bvid"), "ranking")
                print(f"[src] ranking ok, total {len(bvids)}")
            except Exception as e:
                print(f"[src] ranking failed: {e}")

        if "popular" in sources:
            try:
                n0 = len(bvids)
                for pn in (1, 2):
                    if len(bvids) - n0 >= per_source:
                        break
                    data = self.get_json(
                        "https://api.bilibili.com/x/web-interface/popular",
                        {"ps": 20, "pn": pn}, sign_wbi=True)
                    items = data.get("list") or data.get("items") or []
                    for it in items:
                        if len(bvids) - n0 >= per_source:
                            break
                        add(it.get("bvid"), "popular")
                print(f"[src] popular ok +{len(bvids) - n0}, total {len(bvids)}")
            except Exception as e:
                print(f"[src] popular failed: {e}")

        if "feed" in sources:
            try:
                n0 = len(bvids)
                for idx in range(1, 5):
                    if len(bvids) - n0 >= per_source:
                        break
                    data = self.get_json(
                        "https://api.bilibili.com/x/web-interface/index/top/feed/rcmd",
                        {"ps": 12, "fresh_idx": idx, "fresh_idx_1h": idx,
                         "fresh_idx_4h": idx, "fresh_idx_5d": idx}, sign_wbi=True)
                    for it in (data.get("item") or []):
                        if it.get("goto") == "av" and it.get("bvid"):
                            add(it["bvid"], "feed")
                print(f"[src] feed ok +{len(bvids) - n0}, total {len(bvids)}")
            except Exception as e:
                print(f"[src] feed failed: {e}")

        return bvids

    # ---------- 元数据补全 ----------
    def fetch_view(self, bvid):
        data = self.get_json("https://api.bilibili.com/x/web-interface/view", {"bvid": bvid})
        stat = data.get("stat") or {}
        dim = data.get("dimension") or {}
        return {
            "bvid": data.get("bvid"),
            "aid": data.get("aid"),
            "title": data.get("title"),
            "tname": data.get("tname"),
            "pic": data.get("pic"),
            "owner": (data.get("owner") or {}).get("name"),
            "owner_mid": (data.get("owner") or {}).get("mid"),
            "pubdate": data.get("pubdate"),
            "duration": data.get("duration"),
            "dimension": {"width": dim.get("width"), "height": dim.get("height"),
                          "rotate": dim.get("rotate", 0)},
            "stat": {k: stat.get(k) for k in
                     ("view", "danmaku", "reply", "favorite", "coin", "share", "like")},
            "has_honor": bool(data.get("honor")),
        }


def main():
    ap = argparse.ArgumentParser(description="洁净B站 数据采集（仅API元数据）")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "clean.config.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "samples"))
    ap.add_argument("--count", type=int, default=None, help="每来源最多采集多少个 bvid")
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    col = cfg.get("collector", {})
    interval = float(col.get("request_interval_sec", 0.4))
    per_source = args.count or int(col.get("max_videos_per_source", 40))
    sources = col.get("sources", ["ranking", "popular", "feed"])

    cli = BiliClient(interval=interval)
    # 先访问主站拿 buvid3，降低 -412 风控概率
    try:
        req = urllib.request.Request("https://www.bilibili.com/", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            for sc in (resp.headers.get_all("Set-Cookie") or []):
                m = re.match(r"([^=]+)=([^;]*)", sc)
                if m:
                    cli.cookies[m.group(1)] = m.group(2)
        print(f"[cookie] got: {', '.join(cli.cookies.keys()) or 'none'}")
    except Exception as e:
        print(f"[cookie] warmup failed: {e}")

    bvids = cli.collect_bvids(sources, per_source)
    print(f"[collect] unique bvids: {len(bvids)}")

    videos, errors = [], []
    for i, (bv, src) in enumerate(bvids, 1):
        try:
            v = cli.fetch_view(bv)
            v["source"] = src
            videos.append(v)
            s = v["stat"]
            print(f"[enrich {i}/{len(bvids)}] {bv} view={s['view']} fav={s['favorite']} coin={s['coin']}")
        except Exception as e:
            errors.append({"bvid": bv, "source": src, "error": str(e)})
            print(f"[enrich {i}/{len(bvids)}] {bv} FAILED: {e}")

    os.makedirs(args.out, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(args.out, f"sample_{stamp}.json")
    payload = {
        "meta": {
            "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sources": sources,
            "count": len(videos),
            "errors": len(errors),
            "note": "仅API元数据，未下载任何视频；feed来源为未登录态样本",
        },
        "videos": videos,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] saved {len(videos)} videos -> {path}")
    if errors:
        print(f"[warn] {len(errors)} failed fetches: {errors[:3]}...")


if __name__ == "__main__":
    main()
