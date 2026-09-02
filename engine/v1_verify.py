# -*- coding: utf-8 -*-
"""V1 人工核对判定表（AG 独捞样例 12 条）

判定方法：标题判内容类型 + 行为率结构分析（未观看视频内容，局限见文末）。
三分类：true=真神作（F7 结构性漏掉的好视频）/ normal=普通 / junk=垃圾（含诱导互动）。
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 逐条判定（Elabation 委托 agent 初判，用户可复核）
VERDICTS = {
    "BV1eB4y1N79E": ("normal", "动漫吐槽向；like率6%尚可但内容为『最渣男主』吐槽，AG方向coin-+语义不明"),
    "BV1JM53zmELD": ("true", "旅游攻略 vlog；share率0.80% 远超基线——实用传播型，F7 完全不计 share 的盲区"),
    "BV1X24y1K7iU": ("true", "情感共鸣（亲情）；like率9.8% 极强认可，fav仅0.8%——共鸣型被 coin 权重压低"),
    "BV1dK4y1d7eU": ("true", "爱尔兰歌曲资料；fav率2.5% 高——存档型音乐资料"),
    "BV1E64y1m7Yg": ("true", "绝命毒师解说；coin率3.6%（均值~1%）观众用硬币表态——影视共鸣型"),
    "BV1fU4y1a7rJ": ("true", "绝命毒师大结局；coin率3.3% 高——同上"),
    "BV1Y5411e7hz": ("true", "搞笑梗视频；share率2.2% 极高——病毒传播型，F7 盲区"),
    "BV1nb411r7Tc": ("true", "FATE 战斗合集；fav率1.8% + danmaku率1.1% + share率0.7% 三高——存档型 AMV"),
    "BV1GzmEBxENZ": ("junk", "游戏推广『三连领福利』——诱导互动假阳性；coin率4.2% 是利诱产物，AG需防此构型"),
    "BV1FB4y1c793": ("true", "音乐现场；fav率1.4% + share率0.67% 双高——存档+传播型"),
    "BV19t411W74H": ("true", "音乐剧《蝶》07年珍藏；fav率3.1% + share率3.1% 双极高——教科书级存档型神作，怀旧考古的靶心"),
    "BV1KMf2YcE2V": ("true", "个人叙事；like率7.4% 高——共鸣型偏普通，边界样本计入 true"),
}


def main():
    rows = json.load(open(os.path.join(ROOT, "data", "fav_mine", "v1_verify_rows.json"),
                          encoding="utf-8"))
    out = []
    n_true = n_normal = n_junk = 0
    for r in rows:
        v = VERDICTS.get(r["bvid"], ("unknown", ""))
        n_true += v[0] == "true"
        n_normal += v[0] == "normal"
        n_junk += v[0] == "junk"
        out.append({**r, "verdict": v[0], "reason": v[1]})
    n = len(out)
    prec = n_true / n if n else 0
    summary = {"n": n, "true": n_true, "normal": n_normal, "junk": n_junk,
               "precision_true": round(prec, 3),
               "junk_rate": round(n_junk / n, 3) if n else None,
               "method_note": "标题类型 + 行为率结构判定，未观看内容；判定表供 Elabation 复核",
               "rows": out}
    outp = os.path.join(ROOT, "data", "fav_mine", "v1_verify_verdicts.json")
    json.dump(summary, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"=== V1 人工核对（agent 初判，n={n}）===")
    print(f"  真神作 {n_true} / 普通 {n_normal} / 垃圾 {n_junk}")
    print(f"  AG独捞准确率 = {prec:.0%}   垃圾混入率 = {n_junk/n:.0%}")
    print(f"  垃圾样例特征：诱导三连（游戏福利）——AG 需要『诱导构型』防线，与 V3 构型残差同源")
    print(f"[done] -> {outp}")


if __name__ == "__main__":
    main()
