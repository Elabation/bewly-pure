# -*- coding: utf-8 -*-
"""作品-推荐流 v1（godflow）——神作起流的图遍历实验，双臂对照。

Elabation 设计（2026-09-03 夜定稿）：
  · 种子 = 神作（round2 用户确认的神作行，跨门类取 5）
  · 每步前沿 5 节点；A 臂定向：神作优先（币率百分位降序），不足 5 用优秀补位；
    B 臂对照：邻域随机挑 5
  · 凑不齐 5 个（神作+优秀，或随机臂池<5）= 流尽；深度/预算截断记 censored，不算枯
  · 前提：新建分门类数据库 data/flow_graph/（不认为相关推荐=同门类，逐节点分类）
  · 全程匿名通道，主账号零请求
输出：data/flow_graph/godflow_<ts>.json（immutable）
"""
import json
import math
import os
import random
import sys
import time
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

random.seed(20260903)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402
import v3_rules as _rules  # noqa: E402  单一定义源（R9 版）

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
OUTDIR = os.path.join(ROOT, "data", "flow_graph")
os.makedirs(OUTDIR, exist_ok=True)

BAND = 0.2
T_GOD, T_GOOD = 0.93, 0.85
DUR_EXEC, DUR_CAP = 90, 30
R_FAVCOIN, R_FAVRATE = 8.0, 0.15
R_EDGE_LIKE, R_EDGE_COIN, R_EDGE_FAV = 0.20, 0.02, 0.10
DEPTH_CAP = 4
FRONTIER = 5
REQ_BUDGET_RELATED = 170
REQ_BUDGET_TAGS = 40
TNAME_UNTESTED = True

# ---------------- 参照库（带内币率百分位的固定基线，冻结于发车时） ----------------
def load_bands():
    bands = defaultdict(list)
    for fn in ("sample_20260903_185231.json", "sample_20260903_203054.json"):
        try:
            p = json.load(open(os.path.join(SDIR, fn), encoding="utf-8"))
        except Exception:
            continue
        for v in (p.get("videos") or []):
            st = v.get("stat") or {}
            vw = st.get("view") or 0
            if vw >= 3000:
                bands[round(math.log10(vw) / BAND)].append((st.get("coin") or 0) / vw)
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                vw = v.get("view") or 0
                if vw >= 3000:
                    st = v.get("stat") or {}
                    bands[round(math.log10(vw) / BAND)].append((st.get("coin") or 0) / max(1, vw))
    return {k: sorted(a) for k, a in bands.items()}


BANDS = load_bands()


def band_pct(view, coin_rate):
    if view < 3000:
        return None
    arr = BANDS.get(round(math.log10(view) / BAND))
    if not arr:
        return None
    lo, hi = 0, len(arr) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] < coin_rate:
            lo = mid + 1
        else:
            hi = mid
    return lo / max(1, len(arr) - 1)


def v3_tier(pct, dur, fav_rate, coin_rate, like_rate, title=""):
    """委托单一定义源 v3_rules（R9 声援 + R10 博同情版）。"""
    return _rules.v3_tier(pct, dur, fav_rate, coin_rate, like_rate, title)


# ---------------- 门类（不假设相关推荐=同门类，逐节点判定） ----------------
TNAME_MAP = [
    (("知识", "科技", "科学", "财经", "人文", "历史"), "知识科普"),
    (("音乐", "演奏", "翻唱", "音乐综合", "音乐选集"), "音乐"),
    (("影视", "电影", "剧", "预告"), "影视剪辑"),
    (("游戏", "电竞"), "游戏"),
    (("动画", "漫画", "番剧", "国创"), "动画漫影"),
    (("舞蹈",), "舞蹈"),
    (("生活", "搞笑", "兴趣", "户外"), "生活日常"),
    (("美食", "烹饪"), "美食"),
    (("动物", "宠物", "萌宠"), "动物萌宠"),
    (("时尚", "美妆", "穿搭"), "时尚颜值"),
    (("情感", "两性"), "情感两性"),
]
KW_PRIORITY = [
    ("擦边颜值", ["美女", "小姐姐", "热舞", "宅舞", "黑丝", "JK", "jk", "制服", "性感", "变装", "女团", "纯欲", "身材", "御姐", "颜值", "擦边", "戳手"]),
    ("养生健康", ["补肾", "肾虚", "养生", "健康", "锻炼", "健身", "医院", "医生", "熬夜", "体液", "老祖宗"]),
    ("动物萌宠", ["猫", "狗", "汪", "喵", "哈基米", "动物", "萌宠", "鹦鹉", "矿工"]),
    ("游戏", ["游戏", "我的世界", "塞尔达", "原神", "王者", "英雄联盟", "决战"]),
    ("动画漫影", ["动画", "漫画", "番剧", "MAD", "AMV", "魔女", "二次元"]),
    ("音乐", ["洛天依", "音乐", "翻唱", "演唱会", "歌曲", "钢琴", "吉他", "小曲", "MV"]),
    ("影视剪辑", ["剪辑", "混剪", "电影", "解说", "名场面", "偷拍"]),
    ("知识科普", ["科普", "科学", "历史", "哲学", "心理", "经济", "法律", "物理", "数学", "阅读", "阿尔都塞"]),
    ("美食", ["美食", "做菜", "吃播", "菜谱"]),
    ("生活日常", ["日常", "vlog", "生活", "滤镜", "挑战", "开箱", "关注"]),
]


def categorize(title, tname):
    if tname:
        for keys, bucket in TNAME_MAP:
            if any(k in tname for k in keys):
                return bucket, "tname"
    t = title or ""
    for bucket, kws in KW_PRIORITY:
        if any(k in t for k in kws):
            return bucket, "kw"
    return "其他", "kw"


# ---------------- 种子：round2 用户确认的神作，跨门类取 5 ----------------
def pick_seeds():
    rows = json.load(open(os.path.join(MINE, "round2_labels.json"), encoding="utf-8"))["rows"]
    gods = [r for r in rows if r.get("v3") == "神作" and r.get("bvid")]
    by_bucket = defaultdict(list)
    for r in gods:
        bucket, _ = categorize(r.get("title") or "", None)
        by_bucket[bucket].append(r)
    seeds, used = [], set()
    for bucket, rs in sorted(by_bucket.items(), key=lambda x: -max(float(r.get("coin_pct") or 0) for r in x[1])):
        best = max(rs, key=lambda r: float(r.get("coin_pct") or 0))
        seeds.append({"bvid": best["bvid"], "title": best.get("title") or "?", "bucket": bucket,
                      "coin_pct": best.get("coin_pct")})
        used.add(best["bvid"])
        if len(seeds) == 5:
            break
    for r in sorted(gods, key=lambda r: -float(r.get("coin_pct") or 0)):
        if len(seeds) == 5:
            break
        if r["bvid"] not in used:
            bucket, _ = categorize(r.get("title") or "", None)
            seeds.append({"bvid": r["bvid"], "title": r.get("title") or "?", "bucket": bucket,
                          "coin_pct": r.get("coin_pct")})
            used.add(r["bvid"])
    return seeds


# ---------------- 图遍历 ----------------
class Flow:
    def __init__(self, cli, arm, seed, budget):
        self.cli = cli
        self.arm = arm
        self.seed = seed
        self.budget = budget  # 共享 dict: {"related": n, "tags": n}
        self.nodes = {}
        self.edges = []
        self.hops = []
        self.status = "running"
        self.dry = None
        self.visited = set()
        self.n_god_total = 0
        self.n_good_total = 0

    def rec(self, bvid, title, view, dur, fav, coin, like, hop, parent, tname):
        st = self.nodes.get(bvid)
        if st:
            return st
        vr = max(1, view)
        fr, cr, lr = fav / vr, coin / vr, like / vr
        pct = band_pct(view, cr)
        tier, firings = v3_tier(pct, dur, fr, cr, lr, title)
        bucket, csrc = categorize(title, tname)
        st = {"bvid": bvid, "title": (title or "")[:42], "view": view, "dur": dur,
              "fav_rate": round(fr, 5), "coin_rate": round(cr, 5), "like_rate": round(lr, 5),
              "coin_pct": None if pct is None else round(pct, 4), "tier": tier,
              "rules": firings, "category": bucket, "cat_src": csrc, "hop": hop,
              "parent": parent, "arm": self.arm, "flow_seed": self.seed["bvid"]}
        self.nodes[bvid] = st
        return st

    def expand(self, bvid, aid, hop):
        self.budget["related"] += 1
        items, err = None, None
        for attempt, wait in enumerate((0, 2)):
            if wait:
                time.sleep(wait)
            try:
                d = self.cli.get_json("https://api.bilibili.com/x/web-interface/archive/related",
                                      {"aid": aid, "related": "true"}, tries=1)
                items = d if isinstance(d, list) else []
                err = None
                break
            except Exception as e:
                items, err = None, str(e)
        return items, err

    def run(self):
        # 种子详情（拿 aid + 实时 stat；重试 3 次防瞬时抖动）
        v = None
        for attempt, wait in enumerate((0, 2, 4)):
            if wait:
                time.sleep(wait)
            try:
                v = self.cli.fetch_view(self.seed["bvid"])
                break
            except Exception as e:
                v = None
                last_err = str(e)
        if v is None:
            self.status, self.dry = "seed_fail", {"reason": f"fetch_view fail x3: {last_err}"}
            return
        aid = v.get("aid") or (v.get("stat") or {}).get("aid") or v.get("id")
        st = v.get("stat") or {}
        self.budget["related"] += 1
        seed_rec = self.rec(self.seed["bvid"], v.get("title"), st.get("view") or 0, v.get("duration") or 0,
                            st.get("favorite") or 0, st.get("coin") or 0, st.get("like") or 0, 0, None,
                            v.get("tname") or None)
        seed_rec["seed"] = True
        self.visited.add(self.seed["bvid"])
        frontier = [(self.seed["bvid"], aid)]
        depth_reached = 0
        for hop in range(1, DEPTH_CAP + 1):
            if self.budget["related"] >= REQ_BUDGET_RELATED:
                self.status, depth_reached = "censored_budget", hop - 1
                break
            hop_neigh, n_gods, n_good = 0, 0, 0
            pool = []
            expanded_this_hop = []
            for bvid, a in frontier:
                if self.budget["related"] >= REQ_BUDGET_RELATED:
                    break
                items, err = self.expand(bvid, a, hop)
                expanded_this_hop.append(bvid)
                if items is None:
                    self.hops.append({"hop": hop, "expand_fail": str(err)[:60], "parent": bvid})
                    continue
                for it in items:
                    cb = it.get("bvid")
                    if not cb:
                        continue
                    cst = it.get("stat") or {}
                    cv = cst.get("view") or 0
                    hop_neigh += 1
                    self.edges.append({"src": bvid, "dst": cb, "hop": hop})
                    if cb in self.visited:
                        continue
                    self.visited.add(cb)
                    rec = self.rec(cb, it.get("title"), cv, it.get("duration") or 0,
                                   cst.get("favorite") or 0, cst.get("coin") or 0, cst.get("like") or 0,
                                   hop, bvid, it.get("tname") or None)
                    rec["aid"] = it.get("aid")
                    if rec["tier"] == "神作候选":
                        n_gods += 1
                        pool.append(rec)
                    elif rec["tier"] == "优秀候选":
                        n_good += 1
                        pool.append(rec)
            depth_reached = hop
            if self.arm == "target":
                gods = sorted([p for p in pool if p["tier"] == "神作候选"],
                              key=lambda p: -(p["coin_pct"] or 0))
                goods = [p for p in pool if p["tier"] == "优秀候选"]
                random.shuffle(goods)
                sel = gods[:FRONTIER]
                if len(sel) < FRONTIER:
                    sel += goods[:FRONTIER - len(sel)]
                ok = (len(gods) + len(goods)) >= FRONTIER
                dry_reason = f"神作+优秀={len(gods) + len(goods)} < {FRONTIER}"
            else:
                ok = len(pool) >= FRONTIER
                dry_reason = f"可跳池={len(pool)} < {FRONTIER}"
                sel = random.sample(pool, FRONTIER) if ok else []
            self.hops.append({"hop": hop, "n_expanded": len(expanded_this_hop), "n_neighbors": hop_neigh,
                              "n_gods": n_gods, "n_good": n_good, "n_pool": len(pool),
                              "selected": [p["bvid"] for p in sel], "ok": ok, "dry_reason": None if ok else dry_reason})
            if not ok:
                self.status, self.dry = "dry", {"hop": hop, "reason": dry_reason}
                break
            if hop == DEPTH_CAP:
                self.status = "censored_depth"
                break
            frontier = [(p["bvid"], p.get("aid")) for p in sel]
        if self.status == "running":
            self.status = "censored_depth"
        # 丰满度：神作发现总量
        self.n_god_total = sum(1 for n in self.nodes.values() if n["tier"] == "神作候选")
        self.n_good_total = sum(1 for n in self.nodes.values() if n["tier"] == "优秀候选")


def main():
    cli = BiliClient(interval=0.8)
    budget = {"related": 0, "tags": 0}
    seeds = pick_seeds()
    print(f"[seeds] {len(seeds)} 个神作种子：")
    for s in seeds:
        print(f"   · [{s['bucket']}] pct={s['coin_pct']} {s['title'][:32]} {s['bvid']}")
    run = {"meta": {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "version": "godflow-v1",
                    "depth_cap": DEPTH_CAP, "frontier": FRONTIER,
                    "budget_related": REQ_BUDGET_RELATED, "budget_tags": REQ_BUDGET_TAGS,
                    "bands_baseline_n": sum(len(a) for a in BANDS.values()),
                    "tname_available": None},
           "seeds": seeds, "arms": {}}
    consec_fail = 0
    for arm in ("target", "random"):
        flows = []
        print(f"\n===== 臂 {arm} =====")
        for seed in seeds:
            if budget["related"] >= REQ_BUDGET_RELATED or consec_fail >= 15:
                break
            print(f"\n[flow] {arm} ← {seed['bucket']} {seed['title'][:30]}")
            time.sleep(2.5)
            f = Flow(cli, arm, seed, budget)
            f.run()
            consec_fail = consec_fail + 1 if f.status == "seed_fail" else 0
            if run["meta"]["tname_available"] is None:
                has_tn = any(n.get("cat_src") == "tname" for n in f.nodes.values())
                run["meta"]["tname_available"] = has_tn
            print(f"   状态={f.status} 深度={len([h for h in f.hops if 'n_neighbors' in h])} "
                  f"节点={len(f.nodes)} 神作={getattr(f, 'n_god_total', 0)} 优秀={getattr(f, 'n_good_total', 0)} "
                  f"请求={budget['related']}" + (f" 枯因={f.dry['reason']}" if f.dry else ""))
            for h in f.hops:
                if "n_neighbors" in h:
                    print(f"   hop{h['hop']}: 邻居{h['n_neighbors']} 神{h['n_gods']} 优{h['n_good']} "
                          f"选{len(h['selected'])} {'OK' if h['ok'] else 'DRY:' + str(h['dry_reason'])}")
            flows.append({"seed": seed, "status": f.status, "dry": f.dry, "hops": f.hops,
                          "nodes": list(f.nodes.values()), "edges": f.edges,
                          "n_god_total": f.n_god_total, "n_good_total": f.n_good_total})
        # 神作节点 tags 精修（预算内）
        if run["meta"]["tname_available"] is False and budget["tags"] < REQ_BUDGET_TAGS:
            for fl in flows:
                for n in fl["nodes"]:
                    if n["tier"] == "神作候选" and budget["tags"] < REQ_BUDGET_TAGS and n.get("bvid"):
                        try:
                            budget["tags"] += 1
                            td = cli.get_json("https://api.bilibili.com/x/tag/archive/tags",
                                              {"bvid": n["bvid"]}, tries=1)
                            tags = [t.get("tag_name") for t in (td or []) if isinstance(t, dict) and t.get("tag_name")]
                            n["tags"] = tags[:8]
                            nb, _src = categorize(n["title"], None)
                            for t in tags:
                                tb, _ = categorize("", t)
                                if tb != "其他":
                                    nb = tb
                                    break
                            if nb != n["category"]:
                                n["category_kw"] = n["category"]
                                n["category"] = nb
                                n["cat_src"] = "tags"
                        except Exception:
                            pass
        run["arms"][arm] = {"flows": flows}
    run["meta"]["requests"] = budget
    out = os.path.join(OUTDIR, f"godflow_{time.strftime('%Y%m%d_%H%M%S')}.json")
    json.dump(run, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n[done] -> {out}")
    # 总判读
    for arm, a in run["arms"].items():
        nodes = [n for fl in a["flows"] for n in fl["nodes"]]
        gods = [n for n in nodes if n["tier"] == "神作候选"]
        cats = defaultdict(int)
        for n in gods:
            cats[n["category"]] += 1
        print(f"[{arm}] 节点 {len(nodes)} 神作 {len(gods)} 门类分布 {dict(cats)}")


if __name__ == "__main__":
    main()
