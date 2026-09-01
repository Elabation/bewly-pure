# -*- coding: utf-8 -*-
"""洁净B站 · 生态调查采集
三层样本回答「火与质量」问题：
  层1 火的：全站+分区排行榜(ranking/v2, 自带完整stat)、热门(popular)
  层2 被投喂的：首页推荐流(feed rcmd, 需逐个补全收藏/投币)
  层3 不火的长尾：分区最新视频(newlist) —— 「高质量但不火」的去处
覆盖主要内容分区。仅API元数据，不下载视频。

用法： python engine/ecosystem_collect.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ZONES = {
    1: "动画", 3: "音乐", 4: "游戏", 5: "娱乐", 11: "电视剧", 13: "番剧", 22: "鬼畜",
    23: "电影", 36: "知识", 129: "舞蹈", 155: "时尚", 160: "生活", 167: "国创",
    177: "纪录片", 181: "影视", 188: "科技", 202: "资讯", 211: "美食", 217: "动物圈",
    223: "汽车", 234: "运动",
}
# 长尾采样只取用户创作内容区（官方内容区的新视频没代表性）
NEWLIST_ZONES = [1, 3, 4, 5, 22, 36, 129, 155, 160, 181, 188, 202, 211, 217, 223, 234]

STAT_KEYS = ("view", "danmaku", "reply", "favorite", "coin", "share", "like")


def norm_stat(st):
    st = dict(st or {})
    # 老接口拼写 favourite
    if "favourite" in st and not st.get("favorite"):
        st["favorite"] = st.pop("favourite")
    return {k: (st.get(k) or 0) for k in STAT_KEYS}


def stat_ok(st):
    return bool(st) and (st.get("view") or 0) > 0 and ((st.get("like") or 0) > 0 or (st.get("coin") or 0) > 0)


def from_item(it, src):
    owner = it.get("owner")
    if isinstance(owner, dict):
        owner = owner.get("name")
    return {
        "bvid": it.get("bvid"),
        "title": it.get("title"),
        "tname": it.get("tname"),
        "owner": owner,
        "pubdate": it.get("pubdate"),
        "duration": it.get("duration"),
        "dimension": it.get("dimension") or {},
        "stat": norm_stat(it.get("stat")),
        "stat_raw_ok": stat_ok(it.get("stat")),
        "source": src,
    }


def main():
    cli = BiliClient(interval=0.4)
    out = []

    def add(it, src):
        bv = it.get("bvid")
        if bv and all(bv != v["bvid"] for v in out):
            out.append(from_item(it, src))
            return True
        return False

    # ---------- 层1：排行榜（全站 + 分区，自带完整 stat，零额外成本） ----------
    for rid, name in [(0, "全站")] + list(ZONES.items()):
        try:
            data = cli.get_json("https://api.bilibili.com/x/web-interface/ranking/v2",
                                {"rid": rid, "type": "all"})
            lst = data.get("list") or []
            n0 = len(out)
            for it in lst:
                add(it, f"ranking:{name}")
            print(f"[ranking] {name}({rid}): {len(out) - n0} 个")
        except Exception as e:
            print(f"[ranking] {name}({rid}) failed: {e}")

    # ---------- 层1b：热门 ----------
    try:
        n0 = len(out)
        for pn in range(1, 6):
            data = cli.get_json("https://api.bilibili.com/x/web-interface/popular",
                                {"ps": 20, "pn": pn}, sign_wbi=True)
            for it in (data.get("list") or data.get("items") or []):
                add(it, "popular")
        print(f"[popular] +{len(out) - n0}")
    except Exception as e:
        print(f"[popular] failed: {e}")

    # ---------- 层3：分区最新视频（长尾） ----------
    for rid in NEWLIST_ZONES:
        name = ZONES.get(rid, str(rid))
        try:
            data = cli.get_json("https://api.bilibili.com/x/web-interface/newlist",
                                {"rid": rid, "ps": 50, "pn": 1})
            archives = data.get("archives") or data.get("list") or data.get("vlist") or []
            n0 = len(out)
            for it in archives:
                add(it, f"newlist:{name}")
            print(f"[newlist] {name}({rid}): {len(out) - n0} 个")
        except Exception as e:
            print(f"[newlist] {name}({rid}) failed: {e}")

    # ---------- 层2：推荐流（feed 卡片缺收藏/投币，逐个补全） ----------
    feed_bvs = []
    try:
        for idx in range(1, 6):
            data = cli.get_json(
                "https://api.bilibili.com/x/web-interface/index/top/feed/rcmd",
                {"ps": 12, "fresh_idx": idx, "fresh_idx_1h": idx,
                 "fresh_idx_4h": idx, "fresh_idx_5d": idx}, sign_wbi=True)
            for it in (data.get("item") or []):
                if it.get("goto") == "av" and it.get("bvid"):
                    feed_bvs.append(it["bvid"])
        print(f"[feed] rcmd bvids: {len(feed_bvs)}")
    except Exception as e:
        print(f"[feed] rcmd failed: {e}")

    for bv in feed_bvs:
        if all(bv != v["bvid"] for v in out):
            try:
                v = cli.fetch_view(bv)
                v["source"] = "feed"
                v["stat_raw_ok"] = True
                out.append(v)
            except Exception as e:
                print(f"[feed] {bv} enrich failed: {e}")
    print(f"[feed] enriched total {sum(1 for v in out if v['source'] == 'feed')}")

    # ---------- 补全：长尾里 stat 缺失的条目（部分接口不带完整 stat） ----------
    broken = [v for v in out if not v.get("stat_raw_ok") and v["source"].startswith("newlist")]
    for v in broken[:250]:
        try:
            full = cli.fetch_view(v["bvid"])
            v.update({k: full[k] for k in ("title", "tname", "owner", "pubdate",
                                           "duration", "dimension", "stat")})
            v["stat_raw_ok"] = True
        except Exception:
            v["stat_raw_ok"] = False
    print(f"[enrich] newlist 补全 {min(len(broken), 250)}/{len(broken)}")

    os.makedirs(os.path.join(ROOT, "data", "samples"), exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M")
    path = os.path.join(ROOT, "data", "samples", f"ecosystem_{stamp}.json")
    by_src = {}
    for v in out:
        key = v["source"].split(":")[0]
        by_src[key] = by_src.get(key, 0) + 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"meta": {"collected_at": time.strftime("%Y-%m-%d %H:%M"),
                            "count": len(out), "by_layer": by_src,
                            "note": "三层生态样本：榜单火/推荐投喂/分区最新长尾；仅API元数据"},
                   "videos": out}, f, ensure_ascii=False, indent=2)
    print(f"[done] {len(out)} videos, layer分布 {by_src} -> {path}")


if __name__ == "__main__":
    main()
