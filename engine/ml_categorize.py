# -*- coding: utf-8 -*-
"""ML 自动分类 v1 —— 标题字符 n-gram 朴素贝叶斯 + 置信度门槛 + 主动学习闭环。

Elabation 设计（2026-09-04）：
  · 可信种子 = 按门类代表关键词搜索（搜什么标什么）+ 分区排行 typename
  · 特征 = 标题字符 1-3 gram（纯 Python 多项式 NB，零依赖）
  · 置信度 = 后验 top1；低于阈值(0.65) → 待分类 → 网站队列丢给用户
  · 用户纠错(标注导出)回流 → 重训本脚本 → 闭环
输出：data/ml/category_model.json / pool_categories.json / queue.json
"""
import json
import math
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402
from god_pool import build_pool  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MLDIR = os.path.join(ROOT, "data", "ml")
os.makedirs(MLDIR, exist_ok=True)
CONF_THRESHOLD = 0.65

# 每门类的代表搜索词（搜什么标什么 = 可信标签）
SEED_KEYWORDS = {
    "音乐": ["翻唱", "原创音乐", "钢琴演奏", "吉他", "演唱会", "洛天依"],
    "游戏": ["游戏实况", "我的世界", "原神", "单机游戏", "电竞比赛", "游戏解说"],
    "知识科普": ["科普", "历史", "哲学", "心理学", "法律知识", "物理"],
    "颜值/舞蹈/cos": ["宅舞", "cos", "热舞", "舞蹈", "穿搭", "走秀"],
    "动画漫影": ["动画", "MAD", "动漫剪辑", "番剧推荐", "手书", "漫画"],
    "影视剪辑": ["电影解说", "混剪", "影视剪辑", "名场面", "电视剧"],
    "生活日常": ["vlog", "日常记录", "搞笑", "开箱", "大学生活"],
    "美食": ["美食制作", "吃播", "菜谱", "探店", "烘焙"],
    "动物萌宠": ["猫咪", "狗狗", "宠物日常", "哈基米", "动物"],
    "养生健康": ["健身教程", "养生", "健康科普", "锻炼"],
    "情感两性": ["情感", "恋爱观", "两性关系"],
}
ZMAP = {"动画": "动画漫影", "番剧": "动画漫影", "国创": "动画漫影",
        "音乐": "音乐", "舞蹈": "颜值/舞蹈/cos", "游戏": "游戏", "知识": "知识科普",
        "鬼畜": "影视剪辑", "影视": "影视剪辑", "电影": "影视剪辑", "电视剧": "影视剪辑",
        "时尚": "颜值/舞蹈/cos", "生活": "生活日常", "美食": "美食", "动物圈": "动物萌宠",
        "娱乐": "生活日常", "综艺": "影视剪辑", "运动": "生活日常", "汽车": "生活日常",
        "资讯": "知识科普", "科技": "知识科普", "情感": "情感两性"}
KWORD_RE = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+")
EM_RE = re.compile(r"</?em[^>]*>")


def grams(title):
    t = re.sub(r"\s+", "", title or "").lower()
    if not t:
        return []
    out = list(t)
    for i in range(len(t) - 1):
        out.append(t[i:i + 2])
    for i in range(len(t) - 2):
        out.append(t[i:i + 3])
    for w in KWORD_RE.findall(title or ""):
        if len(w) >= 2:
            out.append("W_" + w.lower())
    return out


def fetch_seeds():
    cli = BiliClient(interval=0.55)
    samples = []
    for bucket, kws in SEED_KEYWORDS.items():
        got = 0
        for kw in kws:
            for page in (1, 2):
                try:
                    s = cli.get_json("https://api.bilibili.com/x/web-interface/search/type",
                                     {"search_type": "video", "keyword": kw, "page": page},
                                     sign_wbi=True, tries=1)
                    res = (s or {}).get("result") or []
                except Exception:
                    continue
                for it in res:
                    title = EM_RE.sub("", it.get("title") or "")
                    if not title or it.get("type") not in (None, "video"):
                        continue
                    samples.append({"title": title, "cat": bucket, "kw": kw})
                    got += 1
                time.sleep(0.3)
        print(f"  {bucket}: {got} 条")
    return samples


def train(samples):
    docs = [(s["title"], s["cat"]) for s in samples if s["title"]]
    import random as _rd
    _rd.seed(7)
    _rd.shuffle(docs)
    cut = int(len(docs) * 0.8)
    tr, te = docs[:cut], docs[cut:]
    tf = defaultdict(Counter)
    cls_n = Counter()
    vocab = set()
    tr_titles = []
    for title, c in tr:
        cls_n[c] += 1
        gs = set(grams(title))
        tr_titles.append((title, c))
        for g in gs:
            tf[c][g] += 1
            vocab.add(g)
    V = max(1, len(vocab))
    logp, lp_missing, prior = {}, {}, {}
    for c in cls_n:
        tot = sum(tf[c].values())
        logp[c] = {g: math.log((tf[c][g] + 0.5) / (tot + 0.5 * V)) for g in tf[c]}
        lp_missing[c] = math.log(0.5 / (tot + 0.5 * V))
        prior[c] = math.log(cls_n[c] / max(1, len(tr)))

    def predict(title):
        gs = set(grams(title))
        if not gs or not cls_n:
            return None, 0.0
        scores = {}
        for c in cls_n:
            s = prior[c]
            lp, lm = logp[c], lp_missing[c]
            for g in gs:
                s += lp.get(g, lm)
            scores[c] = s
        m = max(scores.values())
        exp = {c: math.exp(s - m) for c, s in scores.items()}
        z = sum(exp.values())
        post = {c: e / z for c, e in exp.items()}
        top = max(post, key=post.get)
        return top, post[top]

    correct = n = conf_n = conf_correct = 0
    for title, c in te:
        p, conf = predict(title)
        n += 1
        if p == c:
            correct += 1
        if conf >= CONF_THRESHOLD:
            conf_n += 1
            if p == c:
                conf_correct += 1
    acc = correct / max(1, n)
    conf_prec = conf_correct / max(1, conf_n)
    return {"prior": prior, "logp": logp, "lp_missing": lp_missing, "classes": list(cls_n),
            "acc_holdout": acc, "n_train": len(tr), "n_test": n,
            "conf_prec": conf_prec, "conf_n": conf_n}, predict, acc, n


def main():
    print("[1] 按门类关键词拉取可信种子...")
    samples = fetch_seeds()
    cnt = Counter(s["cat"] for s in samples)
    print(f"[1] 种子 {len(samples)} 条：{dict(cnt)}")
    if len(samples) < 300:
        print("[abort] 种子不足，中止")
        return
    print("[2] 训练字符 n-gram 朴素贝叶斯...")
    model, predict, acc, n_te = train(samples)
    print(f"[2] 留出集准确率 {acc:.1%}（n={n_te}）")
    print("[3] 预测公共池...")
    pool, meta = build_pool()
    cats_out, queue = {}, []
    dist = Counter()
    for b, r in pool.items():
        top, conf = predict(r.get("title") or "")
        if top and conf >= CONF_THRESHOLD:
            cats_out[b] = {"cat": top, "conf": round(conf, 3)}
            dist[top] += 1
        else:
            cats_out[b] = {"cat": "待分类", "conf": round(conf or 0, 3)}
            queue.append({"bvid": b, "title": (r.get("title") or "")[:50], "conf": round(conf or 0, 3),
                          "tier": r.get("tier"), "view": r.get("view"), "pct": r.get("pct")})
    print(f"[3] 自动分类 {len(pool)-len(queue)} ｜ 待分类队列 {len(queue)}：{dict(dist)}")
    json.dump(model, open(os.path.join(MLDIR, "category_model.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(cats_out, open(os.path.join(MLDIR, "pool_categories.json"), "w", encoding="utf-8"), ensure_ascii=False)
    queue.sort(key=lambda q: -q["view"])
    json.dump({"threshold": CONF_THRESHOLD, "acc_holdout": acc, "queue": queue},
              open(os.path.join(MLDIR, "queue.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[done] -> data/ml/ (model {os.path.getsize(os.path.join(MLDIR, 'category_model.json')) // 1024}KB)")


if __name__ == "__main__":
    main()
