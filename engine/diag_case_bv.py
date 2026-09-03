# -*- coding: utf-8 -*-
"""特例分析 BV1cBtc65EQc——匿名通道 3 请求（view 详情 / tags API / 热评指纹）+ 零请求对照库。

输出：F7 / CBI / 带内投币·收藏·点赞百分位 / 诚意比(coin/fav) 在神作分布中的位置 /
v3 规则判档 / 热评引流与感谢指纹 / tags API 的 tname 修复验证（W9）。
"""
import json
import math
import os
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402
from cbi_scale import SCALE, tier_of  # noqa: E402
import v3_rules as _rules  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
TARGET = sys.argv[1] if len(sys.argv) > 1 else "BV1cBtc65EQc"
BAND = 0.2
OWNER_MID = "3494381103352463"

# v3 草案阈值（与 v3_round3_catalog.py 同源）
T_GOD, T_GOOD, T_NORMAL = 0.93, 0.85, 0.72
DUR_EXEC, DUR_CAP = 90, 30
R_FAVCOIN, R_FAVRATE = 8.0, 0.15
R_EDGE_LIKE, R_EDGE_COIN, R_EDGE_FAV = 0.20, 0.02, 0.10


def load_pop():
    """参照人口 = 挖矿库 + 首页样本（与 round3 同口径）。"""
    pop = {}
    for fn in ("sample_20260903_185231.json", "sample_20260903_203054.json"):
        try:
            p = json.load(open(os.path.join(SDIR, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            st = v.get("stat") or {}
            view = st.get("view") or 0
            if view < 3000 or not v.get("bvid"):
                continue
            pop.setdefault(v["bvid"], {"view": view, "dur": v.get("duration") or 0, "src": "home",
                                       "coin": (st.get("coin") or 0) / view,
                                       "fav": (st.get("favorite") or 0) / view,
                                       "like": (st.get("like") or 0) / view})
    n_home = len(pop)
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                if (v.get("view") or 0) >= 3000 and v.get("bvid"):
                    st = v.get("stat") or {}
                    view = max(1, v.get("view") or 1)
                    pop.setdefault(v["bvid"], {"view": view, "dur": v.get("duration") or 0, "src": "mine",
                                               "coin": (st.get("coin") or 0) / view,
                                               "fav": (st.get("favorite") or 0) / view,
                                               "like": (st.get("like") or 0) / view})
    return pop, n_home


def bands_of(pop):
    bands = defaultdict(lambda: defaultdict(list))
    for b, r in pop.items():
        k = round(math.log10(r["view"]) / BAND)
        bands[k]["coin"].append(r["coin"])
        bands[k]["fav"].append(r["fav"])
        bands[k]["like"].append(r["like"])
        f7 = (3 * r["fav"] + 2 * r["coin"] + 0.3 * r["like"])
        bands[k]["f7"].append(f7)
    out = {}
    for k, d in bands.items():
        out[k] = {}
        for axis in ("coin", "fav", "like", "f7"):
            arr = sorted(d[axis])
            out[k][axis] = arr
    return out


def pct_of(arr, x):
    if not arr:
        return None
    lo = sum(1 for a in arr if a < x)
    return lo / max(1, len(arr) - 1) if len(arr) > 1 else 0.5


def v3_verdict(coin_pct, dur, fav_rate, coin_rate, like_rate):
    """委托单一定义源 v3_rules（R9 声援提档版）。"""
    return _rules.v3_tier(coin_pct, dur, fav_rate, coin_rate, like_rate)


LINK_KW = ["http", "QQ", "qq", "微信", "vx", "VX", "公众号", "网盘", "粉丝群", "加群", "私我", "主页群", "置顶", "潜水", "q群", "Q群", "频道", "tg", "TG"]
THX_KW = ["感谢", "谢谢", "感谢分享", "多谢", "thx", "谢谢分享", "收下", "干了", "佬", "大佬牛", "谢谢佬"]


def scan_comments(comments):
    n = len(comments)
    link_hits = [c for c in comments if any(k in c for k in LINK_KW)]
    thx_hits = [c for c in comments if any(k in c for k in THX_KW)]
    return {"n": n, "link_n": len(link_hits), "thx_n": len(thx_hits),
            "link_ratio": len(link_hits) / max(1, n), "thx_ratio": len(thx_hits) / max(1, n),
            "top5": comments[:5]}


def main():
    cli = BiliClient(interval=0.8)
    report = {"target": TARGET}

    # ---- 请求1：view 详情 ----
    v = cli.fetch_view(TARGET)
    st = v.get("stat") or {}
    aid = v.get("aid") or st.get("aid") or v.get("id")
    view = st.get("view") or v.get("view") or 0
    dur = v.get("duration") or 0
    pub = v.get("pubdate") or v.get("pubdate_str") or "?"
    title = v.get("title") or "?"
    owner = v.get("owner") or "?"
    omid = v.get("owner_mid")
    tname = v.get("tname") or "(empty)"
    fav, coin, like = st.get("favorite", 0) or 0, st.get("coin", 0) or 0, st.get("like", 0) or 0
    share = st.get("share", 0) or 0
    reply_n = st.get("reply", 0) or 0
    danmaku = st.get("danmaku", 0) or 0
    print(f"[case] {TARGET} 《{title[:40]}》UP:{owner}(mid={omid}) 分区={tname} 时长={dur}s")
    print(f"[case] 播放 {view:,} 弹幕 {danmaku:,} 评论 {reply_n:,} 藏 {fav:,} 币 {coin:,} 赞 {like:,} 转 {share:,}")
    print(f"[case] 发布 {pub}")

    # ---- 请求2：tags API（W9 修复验证）----
    tags, tags_note = [], "未获取"
    try:
        d = cli.get_json("https://api.bilibili.com/x/tag/archive/tags", {"bvid": TARGET}, tries=1)
        if isinstance(d, list):
            tags = [t.get("tag_name") for t in d if t.get("tag_name")][:12]
            tags_note = "OK"
    except Exception as e:
        tags_note = f"fail: {e}"
    print(f"[case] tags API（W9 验证）: {tags_note} → {tags}")

    # ---- 请求3：热评指纹 ----
    comments = []
    try:
        d = cli.get_json("https://api.bilibili.com/x/v2/reply",
                         {"type": 1, "oid": aid, "ps": 20, "sort": 1}, tries=1)
        reps = ((d or {}).get("replies") or [])
        comments = [(r.get("content") or {}).get("message") or "" for r in reps]
    except Exception as e:
        print(f"[case] 热评获取失败: {e}")
    fp = scan_comments(comments)
    print(f"[case] 热评 {fp['n']} 条：引流特征 {fp['link_n']} 条（{fp['link_ratio']:.0%}），感谢特征 {fp['thx_n']} 条（{fp['thx_ratio']:.0%}）")

    # ---- 零请求：对照库 ----
    pop, n_home = load_pop()
    bands = bands_of(pop)
    k = round(math.log10(view) / BAND) if view else None
    band = bands.get(k)
    vr = max(1, view)
    coin_rate, fav_rate, like_rate = coin / vr, fav / vr, like / vr
    f7 = 3 * fav_rate + 2 * coin_rate + 0.3 * like_rate
    band_f7 = band["f7"] if band else []
    cbi = f7 / (band_f7[len(band_f7) // 2] if band_f7 else 1)
    cbi = cbi if band_f7 else None
    p_coin = pct_of(band["coin"], coin_rate) if band else None
    p_fav = pct_of(band["fav"], fav_rate) if band else None
    p_like = pct_of(band["like"], like_rate) if band else None
    band_n = len(band["coin"]) if band else 0
    print(f"\n[metrics] 视角带 k={k}（10^{k*BAND:.1f}~10^{(k+1)*BAND:.1f} 播放量级），带内样本 {band_n} 条 / 参照人口 {len(pop)}（首页域 {n_home}）")
    print(f"[metrics] F7={f7:.3f} → CBI={cbi:.2f}（{tier_of(cbi, view)}）" if cbi else "[metrics] 无带数据")
    print(f"[metrics] 币率 {coin_rate:.2%} → 带内百分位 {p_coin:.3f} ｜ 藏率 {fav_rate:.2%} → {p_fav:.3f} ｜ 赞率 {like_rate:.2%} → {p_like:.3f}")
    sinc = coin / max(1, fav)
    # 神作诚意比分布（零请求重算，与 diag_sincerity 同口径）
    god_rows = []
    for b, r in pop.items():
        # 从 pop 无法直接拿绝对值，改从 CBI 反推神作集合：仅用于诚意比对照
        pass
    # 直接用 diag_sincerity 的落盘结果
    sinc_q = {"p5": 0.025, "p10": 0.038, "p25": 0.074, "p50": 0.202, "p75": 0.543, "p90": 1.142, "p95": 1.628}
    sinc_n = 1623
    try:
        sj = json.load(open(os.path.join(MINE, "sincerity_summary.json"), encoding="utf-8"))
        sinc_q = sj.get("quantiles", sinc_q)
        sinc_n = sj.get("n_gods", sinc_n)
    except Exception:
        pass
    tier_v3, firings = v3_verdict(p_coin if p_coin is not None else 0, dur, fav_rate, coin_rate, like_rate, title)
    print(f"[metrics] 诚意比 coin/fav = {sinc:.3f}（神作分布 n={sinc_n}: p5={sinc_q['p5']} p25={sinc_q['p25']} p50={sinc_q['p50']} p75={sinc_q['p75']}）")
    if sinc < sinc_q["p10"]:
        sinc_pos = f"低于 p10 —— 收藏远多于投币，档案轴强、表达轴弱"
    elif sinc < sinc_q["p25"]:
        sinc_pos = "低于 p25 —— 偏档案型"
    elif sinc < sinc_q["p75"]:
        sinc_pos = "p25~p75 正常诚意区"
    else:
        sinc_pos = "高于 p75 —— 投币诚意区"
    print(f"[metrics] 诚意比定位: {sinc_pos}")
    print(f"[metrics] 赞/币比 = {like / max(1, coin):.0f}（R8 感谢 farming 信号，>50 高危）")
    print(f"\n[verdict] v3 判档: {tier_v3} ｜ 触发规则: {'；'.join(firings) or '无'}")

    # ---- 主页收藏夹交叉 ----
    mine_owner = {}
    try:
        mo = json.load(open(os.path.join(MINE, f"mine_owner_{OWNER_MID}.json"), encoding="utf-8"))
        mine_owner = {x["bvid"]: x for x in (mo.get("videos") or [])}
    except Exception:
        pass
    in_mine = TARGET in mine_owner
    in_db = TARGET in pop
    print(f"\n[cross] 在您的收藏夹快照(113条)中: {'是 ' + str(mine_owner.get(TARGET, {}).get('folder')) if in_mine else '否'}")
    print(f"[cross] 在参照人口中: {'是' if in_db else '否'}")

    report.update({
        "title": title, "owner": owner, "owner_mid": omid, "tname": tname, "dur": dur, "pub": str(pub),
        "view": view, "fav": fav, "coin": coin, "like": like, "share": share, "danmaku": danmaku, "reply": reply_n,
        "tags": tags, "tags_note": tags_note,
        "fingerprint": fp, "comments_sample": comments[:10],
        "band_k": k, "band_n": band_n, "pop_n": len(pop),
        "f7": f7, "cbi": cbi, "cbi_tier": tier_of(cbi, view) if cbi else None,
        "p_coin": p_coin, "p_fav": p_fav, "p_like": p_like,
        "coin_rate": coin_rate, "fav_rate": fav_rate, "like_rate": like_rate,
        "sincerity": sinc, "sincerity_pos": sinc_pos, "sincerity_q": sinc_q,
        "like_coin_ratio": like / max(1, coin),
        "v3_tier": tier_v3, "v3_firings": firings,
        "in_owner_fav": in_mine, "in_pop": in_db,
    })
    out = os.path.join(MINE, f"case_bv_report_{TARGET}.json")
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n[done] -> {out}")


if __name__ == "__main__":
    main()
