# -*- coding: utf-8 -*-
"""E3 剪枝曲线 · AG-Flow 多跳流式挖掘（第二跳）

设计（appreciation-geometry.md §4.5/§4.6）：
  第一跳 = E1 臂①（神作评论区用户 → 收藏夹）已完成。
  第二跳 = 取臂①产物中的「汇流神作」（被多个臂①用户独立收藏，入度=汇流度），
           流向它们的评论区，抓新一轮用户，再挖收藏夹。
  混合模式：评论区抓取走主号（25 请求），收藏夹/详情全部匿名（海量请求）——
           主号暴露面缩至最小（数据纪律：账号风险与数据量产分离）。
剪枝：记录每个新用户的「流强度」（指向它的不同汇流神作数）与发现顺序，
      离线生成预算-产出曲线与 α∈{0.3,0.5,0.7} 三档截断对比。
产出：favmine_flowE3_<stamp>.json + flow_e3_summary.json
用法： python engine/flow_mine.py [--max-gods 25] [--max-users 120]
"""
import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402
from fav_miner import f7_of, cbi_of, anon_mid  # noqa: E402
from cbi_scale import SCALE, GOOD_TIERS, tier_of  # noqa: E402

MINE_DIR = os.path.join(ROOT, "data", "fav_mine")
ARM1_FILE = os.path.join(MINE_DIR, "favmine_20260902_222620.json")  # E1 臂①


def load_state():
    """全库已挖 bvid / 已挖用户 hash / mid2hash 映射。"""
    bvids, hashes = set(), set()
    for fn in os.listdir(MINE_DIR):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn:
            try:
                j = json.load(open(os.path.join(MINE_DIR, fn), encoding="utf-8"))
                bvids |= {v["bvid"] for v in (j.get("videos") or [])}
                hashes |= {u["user_hash"] for u in (j.get("users") or [])}
            except Exception:
                continue
    map_path = os.path.join(MINE_DIR, ".mid2hash.json")
    mid2hash = json.load(open(map_path, encoding="utf-8")) if os.path.exists(map_path) else {}
    return bvids, hashes, mid2hash


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-gods", type=int, default=25, help="汇流神作上限")
    ap.add_argument("--max-users", type=int, default=120, help="第二跳挖掘用户上限")
    ap.add_argument("--per-folder", type=int, default=20)
    ap.add_argument("--sample-ratio", type=float, default=0.85)
    ap.add_argument("--interval", type=float, default=0.45)
    ap.add_argument("--source", default=ARM1_FILE, help="上游跳产物文件（默认 E1 臂①）")
    ap.add_argument("--hop", type=int, default=2, help="本轮跳数编号")
    ap.add_argument("--min-inflow", type=int, default=2, help="汇流度门槛")
    ap.add_argument("--top-cbi-fill", type=int, default=0,
                    help="汇流不足 max-gods 时，用 CBI 最高的神作补足 N 个（稀疏采样下汇流被低估）")
    ap.add_argument("--flowmap-out", default="", help="种子→用户映射旁证文件（.flowmap.json 键）")
    args = ap.parse_args()

    src = json.load(open(args.source, encoding="utf-8"))
    mined_bvids, mined_hashes, mid2hash = load_state()

    # ── 1) 汇流神作：上游合格视频中 tier=high，按汇流度（不同收藏者数）排序 ──
    inflow = defaultdict(set)
    for v in src.get("videos") or []:
        if (v.get("view") or 0) >= 3000 and tier_of(v.get("cbi", 0), v.get("view") or 0) == "high":
            inflow[v["bvid"]].add(v.get("from_user"))
    gods = sorted(((bv, len(us)) for bv, us in inflow.items() if len(us) >= args.min_inflow),
                  key=lambda x: -x[1])[:args.max_gods]
    if args.top_cbi_fill and len(gods) < args.max_gods:
        have = {b for b, _ in gods}
        by_cbi = sorted(((v["bvid"], round(v.get("cbi", 0), 2)) for v in src.get("videos") or []
                         if (v.get("view") or 0) >= 3000 and v.get("tier") == "high"
                         and v["bvid"] not in have),
                        key=lambda x: -x[1])
        gods += by_cbi[:args.max_gods - len(gods)]
        print(f"[hop{args.hop}] 汇流不足，CBI 补足 {min(args.max_gods - len(gods), len(by_cbi))} 个")
    print(f"[hop{args.hop}] 种子神作 {len(gods)} 个: {[(b, n) for b, n in gods[:5]]}...")

    cli_anon = BiliClient(interval=args.interval)
    cli_auth = BiliClient(interval=args.interval)
    sess_path = os.path.join(MINE_DIR, ".sessdata")
    if os.path.exists(sess_path) and open(sess_path, encoding="utf-8").read().strip():
        cli_auth.cookies["SESSDATA"] = open(sess_path, encoding="utf-8").read().strip()
        print("[auth] 主号仅用于评论区抓取；收藏夹/详情全匿名")

    # ── 2) 汇流神作 → aid（匿名 fetch_view，顺带记录最新 tier）──
    god_meta, req = [], 0
    for bv, inflow_n in gods:
        try:
            v = cli_anon.fetch_view(bv)
            req += 1
            st = v.get("stat") or {}
            aid = v.get("aid")
            if not aid:
                continue
            view = st.get("view") or 0
            cbi = cbi_of(f7_of(st), view)
            god_meta.append({"bvid": bv, "aid": aid, "inflow": inflow_n,
                             "cbi": round(cbi, 3), "tier": tier_of(cbi, view),
                             "title": (v.get("title") or "")[:40]})
        except Exception as e:
            print(f"[hop{args.hop}] {bv} fetch failed: {e}")
    print(f"[hop{args.hop}] 有效汇流神作 {len(god_meta)} 个（{req} 匿名请求）")

    # ── 3) 评论区抓人（主号，唯一登录态环节）──
    user_flow = defaultdict(set)   # mid -> 指向它的汇流神作 bvid 集合
    for g in god_meta:
        try:
            d = cli_auth.get_json("https://api.bilibili.com/x/v2/reply",
                                  {"type": 1, "oid": g["aid"], "ps": 20, "pn": 1, "sort": 1}) or {}
            req += 1
            for r in (d.get("replies") or []):
                m = (r.get("member") or {}).get("mid")
                if m:
                    user_flow[m].add(g["bvid"])
        except Exception as e:
            print(f"[hop{args.hop}] reply {g['bvid']} failed: {e}")
    print(f"[hop{args.hop}] 评论区用户 {len(user_flow)} 人（主号请求 {req} 次截止）")
    user_flow_src = defaultdict(list)
    for m, srcs in user_flow.items():
        for b in srcs:
            user_flow_src[b].append(m)

    # ── 4) dedupe + 流强度排序 + 截断（α 剪枝的实挖掘预算档）──
    # 流强度 v2（2026-09-02 修复 Elabation 指出的剪枝缺陷）：
    #   旧定义 = 指向用户的种子计数 —— 每人只评论一个种子时恒为 1，信号死亡，截断沦为任意砍。
    #   新定义 = 用户所评种子的 CBI 总和（流经用户的水的浓度）—— 连续、有区分度、语义严格更强。
    god_cbi = {g["bvid"]: max(3.0, g.get("cbi") or 3.0) for g in god_meta}
    candidates = []
    for mid, srcs in user_flow.items():
        h = mid2hash.get(str(mid))
        if h and h in mined_hashes:
            continue
        strength = sum(god_cbi.get(b, 3.0) for b in srcs)
        candidates.append((mid, round(strength, 2)))
    candidates.sort(key=lambda x: -x[1])
    mids = candidates[:args.max_users]
    if candidates:
        ss = sorted(s for _, s in candidates)
        print(f"[prune] 新用户 {len(candidates)}，流强度分布 min={ss[0]} 中位={ss[len(ss)//2]} "
              f"max={ss[-1]}；实挖 top {len(mids)}（强度 {mids[0][1]}~{mids[-1][1]}）"
              f"——真剪枝：砍 {len(candidates)-len(mids)} 个低浓度候选")

    # ── 5) 匿名挖收藏夹（复用 mine() 的二跳逻辑 + 请求计数 + 发现顺序）──
    users, videos = [], []
    curve = []          # 预算-产出曲线: {req, users, high, good, cbi_sum, cbi_n}
    n_high = n_good = 0
    for ui, (mid, strength) in enumerate(mids, 1):
        anon = mid2hash.get(str(mid)) or anon_mid(mid)
        mid2hash[str(mid)] = anon
        u_req0 = req
        try:
            fd = cli_anon.get_json("https://api.bilibili.com/x/v3/fav/folder/created/list-all",
                                   {"up_mid": mid, "type": 2, "rid": 0}) or {}
            req += 1
            folders = [f for f in (fd.get("list") or [])
                       if ((f.get("attr") or 0) & 1) == 0 and (f.get("media_count") or 0) > 3]
        except Exception:
            folders = []
        if not folders:
            try:
                fd2 = cli_anon.get_json("https://api.bilibili.com/x/v3/fav/folder/collected/list",
                                        {"up_mid": mid, "ps": 20, "pn": 1, "platform": "web"}) or {}
                req += 1
                folders = [f for f in (fd2.get("list") or [])
                           if ((f.get("attr") or 0) & 1) == 0 and (f.get("media_count") or 0) > 3
                           and f.get("state") == 0]
            except Exception:
                pass
        folders.sort(key=lambda f: f.get("media_count") or 0, reverse=True)
        got = 0
        for folder in folders[:3]:
            try:
                res = cli_anon.get_json("https://api.bilibili.com/x/v3/fav/resource/list",
                                        {"media_id": folder.get("id"), "pn": 1, "ps": 20, "keyword": "",
                                         "order": "mtime", "type": 0, "tid": 0, "platform": "web"},
                                        sign_wbi=True)
                req += 1
            except Exception:
                continue
            medias = [m for m in (res.get("medias") or [])
                      if m and m.get("bvid") and m.get("type") == 2]
            if not medias:
                continue
            users.append({"user_hash": anon, "seed_type": f"flow_hop{args.hop}", "flow_strength": strength,
                          "discovered_at": ui, "folder_title": folder.get("title") or "?",
                          "media_count": folder.get("media_count"), "entries": len(medias)})
            targets = random.sample(medias[:args.per_folder],
                                    max(1, int(min(len(medias), args.per_folder) * args.sample_ratio)))
            for m in targets:
                try:
                    v = cli_anon.fetch_view(m["bvid"])
                    req += 1
                except Exception:
                    continue
                st = v.get("stat") or {}
                view = st.get("view") or 0
                cbi = cbi_of(f7_of(st), view)
                t = tier_of(cbi, view)
                n_high += t == "high"
                n_good += t in GOOD_TIERS
                pub = m.get("pubtime") or v.get("pubdate") or 0
                videos.append({"bvid": m["bvid"], "title": v.get("title") or m.get("title"),
                               "tname": v.get("tname") or "?", "pubdate": pub,
                               "year": time.strftime("%Y", time.localtime(pub)) if pub else "?",
                               "view": view, "f7": round(f7_of(st), 4), "cbi": round(cbi, 3),
                               "tier": t, "duration": v.get("duration"),
                               "stat": {k: st.get(k) for k in
                                        ("view", "danmaku", "reply", "favorite", "coin", "share", "like")},
                               "from_user": anon, "folder": folder.get("title") or "?"})
            print(f"[u{ui}/{len(mids)}] {anon} 强度{strength} 夹「{folder.get('title')}」补查 {len(targets)}")
            got += 1
            if got >= 3:
                break
        curve.append({"req": req, "users": ui, "high": n_high, "good": n_good,
                      "user_req": req - u_req0, "flow_strength": strength})
        if ui % 20 == 0:
            rate = n_high / max(1, sum(1 for v2 in videos if (v2.get("view") or 0) >= 3000))
            print(f"[progress] 用户 {ui}  请求 {req}  神作 {n_high}（合格神作率 {rate:.3f}）")

    # ── 6) 落盘（immutable 原始文件 + E3 分析产物）──
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(MINE_DIR, f"favmine_flowH{args.hop}_{stamp}.json")
    json.dump({"meta": {"mined_at": time.strftime("%Y-%m-%d %H:%M:%S"), "users": len(users),
                        "videos": len(videos), f"arm": "flow_hop{args.hop}", "hop": args.hop,
                        "seeds": god_meta, "anon_requests": req,
                        "privacy": "同 fav_miner；主号仅评论区抓取"},
               "users": users, "videos": videos},
              open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(mid2hash, open(os.path.join(MINE_DIR, ".mid2hash.json"), "w", encoding="utf-8"))
    # 种子→用户映射旁证（可恢复流拓扑；2026-09-02 教训：缺失导致动画/分析无法回溯评论边）
    fm_path = os.path.join(MINE_DIR, ".flowmap.json")
    flowmap = json.load(open(fm_path, encoding="utf-8")) if os.path.exists(fm_path) else {}
    flowmap[f"hop{args.hop}"] = {g["bvid"]: sorted(mid2hash.get(str(m), "") for m in mids_src
                                                   if mid2hash.get(str(m)))[:0] or
                                 sorted({mid2hash.get(str(m), "") for m in mids_src} - {""})
                                 for g, mids_src in [(gd, user_flow_src.get(g["bvid"], [])) for gd in god_meta]}
    json.dump(flowmap, open(fm_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 分析：合格神作率 / α 三档 / 曲线拐点（简化：每 10% 预算的边际产出）
    qual = [v for v in videos if (v.get("view") or 0) >= 3000]
    hop2_rate = sum(1 for v in qual if v["tier"] == "high") / max(1, len(qual))
    hop2_good = sum(1 for v in qual if v["tier"] in GOOD_TIERS) / max(1, len(qual))
    alphas = {}
    for a in (0.3, 0.5, 0.7):
        k = max(1, int(len(mids) * a))
        sub = [u for u in users if u["discovered_at"] <= k]
        sub_hashes = {u["user_hash"] for u in sub}
        sq = [v for v in qual if v.get("from_user") in sub_hashes]
        alphas[str(a)] = {
            "users": len(sub_hashes), "requests": curve[k - 1]["req"] if curve else 0,
            "high_n": sum(1 for v in sq if v["tier"] == "high"),
            "high_rate": round(sum(1 for v in sq if v["tier"] == "high") / max(1, len(sq)), 3),
            "good_rate": round(sum(1 for v in sq if v["tier"] in GOOD_TIERS) / max(1, len(sq)), 3),
            "efficiency": round(sum(1 for v in sq if v["tier"] == "high") / max(1, curve[k - 1]["req"]), 4),
        }
    # 流强度 → 用户神作率 的单调性（流强度作为剪枝信号是否有效）
    strata = defaultdict(lambda: [0, 0])
    for u in users:
        sv = [v for v in qual if v.get("from_user") == u["user_hash"]]
        strata[min(u["flow_strength"], 4)][0] += sum(1 for v in sv if v["tier"] == "high")
        strata[min(u["flow_strength"], 4)][1] += len(sv)
    monotone = {f"强度{ s if s < 4 else '4+'}": round(h / max(1, n), 3) for s, (h, n) in sorted(strata.items())}

    outp = os.path.join(MINE_DIR, f"flow_h{args.hop}_summary.json")
    json.dump({"hop2_high_rate": round(hop2_rate, 3), "hop2_good_rate": round(hop2_good, 3),
               "hop1_high_rate": 0.259, "baseline": 0.059,
               "n_users": len(users), "n_videos": len(videos), "n_qual": len(qual),
               "anon_requests": req, "auth_requests": len(god_meta),
               "alpha_cutoffs": alphas, "flow_strength_monotonicity": monotone,
               "curve": curve, "seeds": god_meta},
              open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n=== 第 {args.hop} 跳结果 ===")
    print(f"  用户 {len(users)}  合格视频 {len(qual)}  匿名请求 {req} + 主号 {len(god_meta)}")
    print(f"  本跳神作率 {hop2_rate:.3f}（第一跳 0.259，基线 0.059）  优秀率 {hop2_good:.3f}")
    print(f"  α 截断: {json.dumps(alphas, ensure_ascii=False)}")
    print(f"  流强度单调性: {json.dumps(monotone, ensure_ascii=False)}")
    print(f"[done] -> {outp}\n         -> {path}")


if __name__ == "__main__":
    main()
