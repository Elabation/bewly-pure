# -*- coding: utf-8 -*-
"""洁净B站 · 收藏夹考古挖掘器（「给过，却不再被看见」数据管线）

挖掘逻辑：
  1. 种子：从 data/samples/*.json 抽一批视频 → fetch_view 反查 uploader mid（真实重度用户）
  2. 对每个用户：拉公开收藏夹列表 → 挑一个夹 → 拉条目（自带 pubdate/播放/收藏）
  3. 对条目抽样补 view 详情（coin/like）→ F7 / CBI（内置 28 点基线，与扩展 core.ts 同源）
  4. 入库即匿名：用户 mid → sha1 短哈希，展示层永不出现真实身份

隐私与合规：只访问公开接口与公开收藏夹；私密夹（-403/-404）直接跳过；
不写入任何数据到 B 站；呈现层只出现「视频」不出现「人」。

用法：
  python engine/fav_miner.py --users 6           # 快速试跑
  python engine/fav_miner.py --users 60          # 正式一轮
  python engine/fav_miner.py --analyze data/fav_mine/favmine_xxx.json   # 只分析已挖掘数据
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402

# CBI 基线曲线（28 点 [log10_view, p50_F7]，与扩展 core.ts / data/analysis/cbi_baseline.json 同源）
CBI_CURVE = [
    4.5, 0.2065, 4.6, 0.1745, 4.7, 0.1376, 4.8, 0.1247, 4.9, 0.1154,
    5.0, 0.1057, 5.1, 0.0919, 5.2, 0.083, 5.3, 0.0742, 5.4, 0.0687,
    5.5, 0.0605, 5.6, 0.0577, 5.7, 0.0557, 5.8, 0.058, 5.9, 0.0616,
    6.0, 0.0664, 6.1, 0.0706, 6.2, 0.0779, 6.3, 0.082, 6.4, 0.0839,
    6.5, 0.0848, 6.6, 0.0861, 6.7, 0.0861, 6.8, 0.0861, 6.9, 0.0852,
    7.0, 0.0849, 7.1, 0.0854, 7.2, 0.0863,
]

W_FAV, W_COIN, W_LIKE = 3.0, 2.0, 0.3


def baseline_cbi(log_view: float) -> float:
    c = CBI_CURVE
    if log_view <= c[0]:
        return c[1]
    if log_view >= c[-2]:
        return c[-1]
    for i in range(0, len(c) - 2, 2):
        if c[i] <= log_view <= c[i + 2]:
            t = (log_view - c[i]) / (c[i + 2] - c[i])
            return c[i + 1] + t * (c[i + 3] - c[i + 1])
    return c[-1]


def f7_of(stat: dict) -> float:
    view = stat.get("view") or 0
    if view <= 0:
        return 0.0
    raw = (stat.get("favorite") or 0) * W_FAV + (stat.get("coin") or 0) * W_COIN \
        + (stat.get("like") or 0) * W_LIKE
    return raw / view


def cbi_of(f7: float, view: int) -> float:
    if view <= 0:
        return 0.0
    b = baseline_cbi(__import__("math").log10(max(view, 10)))
    return f7 / b if b > 0 else 0.0


def tier_of(cbi: float, view: int) -> str:
    if view < 3000:
        return "unproven"
    if cbi >= 1.2:
        return "high"
    if cbi >= 1.0:
        return "normal"
    if cbi >= 0.5:
        return "low"
    return "junk"


def anon_mid(mid: int) -> str:
    return hashlib.sha1(f"bili:{mid}".encode()).hexdigest()[:10]


def load_seed_bvids(limit: int) -> list:
    """从现有样本抽种子视频（各自带真实 uploader）。"""
    sdir = os.path.join(ROOT, "data", "samples")
    pool = []
    for fn in sorted(os.listdir(sdir)):
        if fn.startswith("sample_") and fn.endswith(".json"):
            try:
                with open(os.path.join(sdir, fn), encoding="utf-8") as f:
                    payload = json.load(f)
                vids = payload.get("videos") or []
                pool.extend(v.get("bvid") for v in vids if v.get("bvid"))
            except Exception:
                continue
    pool = list(dict.fromkeys(pool))
    random.shuffle(pool)
    return pool[:limit]


def seeds_from_comments(cli: BiliClient, n: int) -> list:
    """从样本视频的评论区抓真实观众 mid（未登录态每视频仅返回~3条，用全量视频补足）。"""
    sdir = os.path.join(ROOT, "data", "samples")
    vids = []
    for fn in sorted(os.listdir(sdir)):
        if fn.startswith("sample_") and fn.endswith(".json"):
            try:
                with open(os.path.join(sdir, fn), encoding="utf-8") as f:
                    vids.extend(v for v in (json.load(f).get("videos") or []) if v.get("aid"))
            except Exception:
                continue
    random.shuffle(vids)
    mids, seen = [], set()
    for v in vids:
        if len(mids) >= n:
            break
        try:
            d = cli.get_json("https://api.bilibili.com/x/v2/reply",
                             {"type": 1, "oid": v["aid"], "ps": 20, "pn": 1, "sort": 1}) or {}
            got = 0
            for r in (d.get("replies") or []):
                m = (r.get("member") or {}).get("mid")
                if m and m not in seen:
                    seen.add(m)
                    mids.append(m)
                    got += 1
                    if len(mids) >= n:
                        break
            if got:
                print(f"[comment-seed] {v.get('bvid')} +{got} (total {len(mids)})")
        except Exception as e:
            print(f"[comment-seed] {v.get('bvid')} failed: {e}")
    return mids


def mine(cli: BiliClient, n_users: int, per_folder: int, sample_ratio: float, out_dir: str, comment_seed_count: int = 0):
    seeds = load_seed_bvids(n_users * 2)
    print(f"[seed] {len(seeds)} candidate seed videos")

    # 已挖用户（本地映射，不入仓）——重复挖无增量价值
    map_path = os.path.join(out_dir, ".mid2hash.json")
    mid2hash = {}
    if os.path.exists(map_path):
        try:
            mid2hash = json.load(open(map_path, encoding="utf-8"))
        except Exception:
            mid2hash = {}
    mined_hashes = set()
    for fn in os.listdir(out_dir):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn:
            try:
                for u in (json.load(open(os.path.join(out_dir, fn), encoding="utf-8")).get("users") or []):
                    mined_hashes.add(u["user_hash"])
            except Exception:
                pass
    print(f"[dedupe] {len(mined_hashes)} users already mined -> will skip")

    # 1) 种子 → 用户 mid：uploader（重度用户）+ 评论区观众（真实用户）
    mids, seen_mid = [], set()
    if comment_seed_count:
        for mid in seeds_from_comments(cli, comment_seed_count):
            if mid not in seen_mid:
                seen_mid.add(mid)
                mids.append(mid)
        print(f"[seed] comment seeds: {len(mids)}")
    for i, bv in enumerate(seeds, 1):
        if len(mids) >= n_users:
            break
        try:
            v = cli.fetch_view(bv)
            mid = (v.get("owner") or {}).get("mid") if isinstance(v.get("owner"), dict) else None
            if not mid:
                data = cli.get_json("https://api.bilibili.com/x/web-interface/view", {"bvid": bv})
                mid = (data.get("owner") or {}).get("mid")
            if mid and mid not in seen_mid:
                seen_mid.add(mid)
                mids.append(mid)
        except Exception:
            continue
    # 过滤已挖
    fresh = []
    for mid in mids:
        h = mid2hash.get(str(mid))
        if h and h in mined_hashes:
            continue
        fresh.append(mid)
    print(f"[dedupe] fresh mids {len(fresh)}/{len(mids)}")
    mids = fresh

    # 2) 每用户：收藏夹列表 → 挑夹 → 条目 → 抽样补 view
    users, videos = [], []
    for ui, mid in enumerate(mids, 1):
        h = mid2hash.get(str(mid))
        anon = h or anon_mid(mid)
        mid2hash[str(mid)] = anon
        try:
            fd = cli.get_json("https://api.bilibili.com/x/v3/fav/folder/created/list-all",
                              {"up_mid": mid, "type": 2, "rid": 0}) or {}
            folders = fd.get("list") or []
        except Exception as e:
            print(f"[user {ui}/{len(mids)}] {anon} folder-list failed: {e}")
            continue
        # attr 位0：0=公开 1=私有 —— 只采公开夹
        folders = [f for f in folders
                   if ((f.get("attr") or 0) & 1) == 0 and (f.get("media_count") or 0) > 3]
        if not folders:
            # 回退：TA 收藏的别人的公开收藏夹（收藏品味同样有效）
            try:
                fd2 = cli.get_json("https://api.bilibili.com/x/v3/fav/folder/collected/list",
                                   {"up_mid": mid, "ps": 20, "pn": 1, "platform": "web"}) or {}
                folders = [f for f in (fd2.get("list") or [])
                           if ((f.get("attr") or 0) & 1) == 0 and (f.get("media_count") or 0) > 3
                           and f.get("state") == 0]
            except Exception:
                pass
        folders.sort(key=lambda f: f.get("media_count") or 0, reverse=True)
        got_folder = 0
        for folder in folders[:3]:  # 每用户最多挖 3 个夹
            media_id = folder.get("id")
            title = folder.get("title") or "?"
            try:
                res = cli.get_json("https://api.bilibili.com/x/v3/fav/resource/list",
                                   {"media_id": media_id, "pn": 1, "ps": 20, "keyword": "",
                                    "order": "mtime", "type": 0, "tid": 0, "platform": "web"},
                                   sign_wbi=True)
            except Exception:
                continue  # 私密/失败 → 试下一个夹
            medias = [m for m in (res.get("medias") or [])
                      if m and m.get("bvid") and m.get("type") == 2]
            if not medias:
                continue
            users.append({"user_hash": anon, "folder_title": title,
                          "media_count": folder.get("media_count"), "entries": len(medias)})
            # 对前 per_folder 条按比例抽样补 view
            targets = medias[:per_folder]
            k = max(1, int(len(targets) * sample_ratio))
            targets = random.sample(targets, min(k, len(targets)))
            enriched = 0
            for m in targets:
                bv = m["bvid"]
                try:
                    v = cli.fetch_view(bv)
                except Exception:
                    continue
                stat = v.get("stat") or {}
                f7 = f7_of(stat)
                view = stat.get("view") or 0
                cbi = cbi_of(f7, view)
                pub = m.get("pubtime") or v.get("pubdate") or 0
                videos.append({
                    "bvid": bv, "title": v.get("title") or m.get("title"),
                    "tname": v.get("tname") or "?",
                    "pubdate": pub,
                    "year": time.strftime("%Y", time.localtime(pub)) if pub else "?",
                    "view": view, "f7": round(f7, 4), "cbi": round(cbi, 3),
                    "tier": tier_of(cbi, view),
                    "duration": v.get("duration"),
                    "stat": {k: stat.get(k) for k in
                             ("view", "danmaku", "reply", "favorite", "coin", "share", "like")},
                    "from_user": anon, "folder": title,
                })
                enriched += 1
            print(f"[user {ui}/{len(mids)}] {anon} 夹「{title}」条目 {len(medias)} 补查 {enriched}")
            got_folder += 1
            if got_folder >= 3:
                break
        if not got_folder:
            print(f"[user {ui}/{len(mids)}] {anon} 无可用公开收藏夹")

    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"favmine_{stamp}.json")
    payload = {
        "meta": {
            "mined_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "users": len(users), "videos": len(videos),
            "weights": {"fav": W_FAV, "coin": W_COIN, "like": W_LIKE},
            "baseline": "cbi_baseline.json n=6734 fit_at=2026-09-01（与扩展 core.ts 同源）",
            "privacy": "用户身份入库即 sha1 匿名；仅公开收藏夹；仅 API 元数据",
        },
        "users": users,
        "videos": videos,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.makedirs(out_dir, exist_ok=True)
    json.dump(mid2hash, open(map_path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[done] users={len(users)} videos={len(videos)} -> {path}")
    return path


def load_merged_mine(out_dir):
    """合并目录下全部挖掘文件，bvid 去重（后文件覆盖前文件）。"""
    merged = {"meta": {"users": 0, "mined_at": ""}, "videos": [], "_user_hashes": set()}
    seen = {}
    for fn in sorted(os.listdir(out_dir)):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn:
            try:
                p = json.load(open(os.path.join(out_dir, fn), encoding="utf-8"))
            except Exception:
                continue
            merged["meta"]["mined_at"] = p["meta"].get("mined_at", merged["meta"]["mined_at"])
            for u in (p.get("users") or []):
                merged["_user_hashes"].add(u["user_hash"])
            for v in (p.get("videos") or []):
                seen[v["bvid"]] = v
    merged["videos"] = list(seen.values())
    merged["meta"]["users"] = len(merged["_user_hashes"])
    merged.pop("_user_hashes")
    return merged


def analyze(path: str, out=None):
    if path in (None, "ALL"):
        merged = load_merged_mine(os.path.join(ROOT, "data", "fav_mine"))
        stamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(ROOT, "data", "fav_mine", f"favmine_merged_{stamp}.json")
        json.dump(merged, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[merge] videos={len(merged['videos'])} users={merged['meta']['users']} -> {path}")
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    videos = payload["videos"]
    meta = {"mined_at": payload["meta"]["mined_at"], "users": payload["meta"]["users"],
            "n": len(videos)}

    # 年代 × 质量矩阵
    by_year = defaultdict(list)
    for v in videos:
        by_year[v.get("year") or "?"].append(v)
    years = sorted(y for y in by_year if y != "?")
    year_rows = []
    for y in years:
        vs = by_year[y]
        n = len(vs)
        hi = sum(1 for v in vs if v["tier"] == "high")
        nm = sum(1 for v in vs if v["tier"] in ("high", "normal"))
        avg_cbi = sum(v["cbi"] for v in vs) / n
        year_rows.append({"year": y, "n": n, "high": hi, "high_rate": round(hi / n, 3),
                          "good": nm, "good_rate": round(nm / n, 3),
                          "avg_cbi": round(avg_cbi, 3)})

    # 对照组：现有样本（2020-2026 采集流）跑同一公式
    ctrl = []
    sdir = os.path.join(ROOT, "data", "samples")
    for fn in sorted(os.listdir(sdir)):
        if fn.startswith("sample_") and fn.endswith(".json"):
            try:
                with open(os.path.join(sdir, fn), encoding="utf-8") as f:
                    for v in (json.load(f).get("videos") or []):
                        st = v.get("stat") or {}
                        view = st.get("view") or 0
                        if view < 3000:
                            continue
                        f7 = f7_of(st)
                        ctrl.append({"cbi": cbi_of(f7, view), "view": view,
                                     "pubdate": v.get("pubdate") or 0})
            except Exception:
                continue
    ctrl_n = len(ctrl)
    ctrl_high = sum(1 for c in ctrl if c["cbi"] >= 1.2)
    ctrl_good = sum(1 for c in ctrl if c["cbi"] >= 1.0)
    ctrl_avg = sum(c["cbi"] for c in ctrl) / ctrl_n if ctrl_n else 0
    ctrl_years = Counter(time.strftime("%Y", time.localtime(c["pubdate"])) for c in ctrl if c["pubdate"])

    mined_high = sum(1 for v in videos if v["tier"] == "high")
    mined_good = sum(1 for v in videos if v["tier"] in ("high", "normal"))
    mined_avg = sum(v["cbi"] for v in videos) / len(videos) if videos else 0

    # 老视频定义：pubdate 距今 ≥ 5 年
    cutoff = time.time() - 5 * 365.25 * 86400
    old = [v for v in videos if v.get("pubdate") and v["pubdate"] < cutoff]
    new = [v for v in videos if v.get("pubdate") and v["pubdate"] >= cutoff]
    def seg(vs):
        if not vs:
            return {"n": 0}
        n = len(vs)
        return {"n": n, "high_rate": round(sum(1 for v in vs if v["tier"] == "high") / n, 3),
                "good_rate": round(sum(1 for v in vs if v["tier"] in ("high", "normal")) / n, 3),
                "avg_cbi": round(sum(v["cbi"] for v in vs) / n, 3)}
    old_seg, new_seg = seg(old), seg(new)

    # 收藏夹内一致性：同一用户夹内 normal+ 比例（夹是不是「质量签名」）
    by_user = defaultdict(list)
    for v in videos:
        by_user[v["from_user"]].append(v)
    folder_rows = []
    for uh, vs in by_user.items():
        n = len(vs)
        folder_rows.append({"user_hash": uh, "n": n,
                            "good_rate": round(sum(1 for v in vs if v["tier"] in ("high", "normal")) / n, 3),
                            "avg_cbi": round(sum(v["cbi"] for v in vs) / n, 3)})
    folder_rows.sort(key=lambda r: r["good_rate"], reverse=True)

    # 明星视频（神作线以上，按 CBI 排序）
    stars = sorted((v for v in videos if v["tier"] == "high"),
                   key=lambda v: v["cbi"], reverse=True)[:20]

    result = {
        "meta": meta,
        "overall": {"n": len(videos), "high": mined_high, "high_rate": round(mined_high / len(videos), 3) if videos else 0,
                    "good_rate": round(mined_good / len(videos), 3) if videos else 0,
                    "avg_cbi": round(mined_avg, 3)},
        "control": {"n": ctrl_n, "high_rate": round(ctrl_high / ctrl_n, 3) if ctrl_n else 0,
                    "good_rate": round(ctrl_good / ctrl_n, 3) if ctrl_n else 0,
                    "avg_cbi": round(ctrl_avg, 3), "year_dist": dict(ctrl_years),
                    "note": "对照=现有 samples 采集流（ranking/popular/feed 2020-2026），同一公式同一基线"},
        "old_vs_new": {"cutoff": "5 年", "old": old_seg, "new": new_seg},
        "by_year": year_rows,
        "folders": folder_rows[:15],
        "stars": stars,
    }
    out = out or os.path.splitext(path)[0] + "_analysis.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"=== 收藏夹考古 · 分析 ===")
    print(f"用户(匿名) {meta['users']} · 视频 {meta['n']}")
    print(f"挖掘组：神作率 {result['overall']['high_rate']} · 优秀率 {result['overall']['good_rate']} · 平均CBI {result['overall']['avg_cbi']}")
    print(f"对照组：神作率 {result['control']['high_rate']} · 优秀率 {result['control']['good_rate']} · 平均CBI {result['control']['avg_cbi']} (n={ctrl_n})")
    print(f"≥5年老视频：{json.dumps(old_seg, ensure_ascii=False)}")
    print(f"<5年新视频：{json.dumps(new_seg, ensure_ascii=False)}")
    print("--- 年代分布 ---")
    for r in year_rows:
        print(f"  {r['year']}: n={r['n']:3d} 神作率 {r['high_rate']} 优秀率 {r['good_rate']} 平均CBI {r['avg_cbi']}")
    print("--- 夹质量 Top5（匿名） ---")
    for r in folder_rows[:5]:
        print(f"  {r['user_hash']} n={r['n']} 优秀率 {r['good_rate']}")
    print(f"[done] -> {out}")
    return out


def main():
    ap = argparse.ArgumentParser(description="洁净B站 · 收藏夹考古挖掘器")
    ap.add_argument("--users", type=int, default=60, help="挖掘多少个用户的收藏夹")
    ap.add_argument("--comment-seeds", type=int, default=0, help="额外从老视频评论区抓多少个种子用户")
    ap.add_argument("--per-folder", type=int, default=20, help="每夹取前多少条")
    ap.add_argument("--sample-ratio", type=float, default=0.6, help="条目里补 view 详情的比例")
    ap.add_argument("--interval", type=float, default=0.45, help="请求间隔秒")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "fav_mine"))
    ap.add_argument("--analyze", default=None, help="只分析已挖掘的 json（ALL=合并全目录）")
    args = ap.parse_args()

    # 登录态（可选）：data/fav_mine/.sessdata 放 SESSDATA cookie 值即启用。
    # 该文件是本机私密凭据：永不打印、永不上传、永不入仓库。
    sess_path = os.path.join(args.out, ".sessdata")

    if args.analyze:
        analyze(args.analyze if args.analyze != "ALL" else None)
        return

    cli = BiliClient(interval=args.interval)
    try:
        req = __import__("urllib.request", fromlist=["urllib.request"]).Request(
            "https://www.bilibili.com/", headers={"User-Agent": BiliClient.__dict__.get("UA", "Mozilla/5.0")})
        with __import__("urllib.request", fromlist=["urllib.request"]).urlopen(req, timeout=15) as resp:
            import re as _re
            for sc in (resp.headers.get_all("Set-Cookie") or []):
                m = _re.match(r"([^=]+)=([^;]*)", sc)
                if m:
                    cli.cookies[m.group(1)] = m.group(2)
    except Exception:
        pass

    if os.path.exists(sess_path):
        val = open(sess_path, encoding="utf-8").read().strip()
        if val:
            cli.cookies["SESSDATA"] = val
            print("[auth] SESSDATA loaded from local file (never printed/committed)")
        else:
            print("[auth] .sessdata 为空，按未登录继续")
    else:
        print("[auth] 无 .sessdata，未登录模式（评论区受限每页~3条）")

    path = mine(cli, args.users + args.comment_seeds, args.per_folder, args.sample_ratio, args.out,
                comment_seed_count=args.comment_seeds)
    analyze(path)


if __name__ == "__main__":
    main()
