"""Reproduce the 2026-09-01 title-screen audit from the frozen sample."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from html import escape
import json
import math
from pathlib import Path
import random
import re
from statistics import median

from ecosystem_analysis import score
from title_screen import numeric_title_flag


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = "data/samples/ecosystem_v5_20260901_2050_fix.json"
LIMITS = (.35, .60, .45)


def sample_rows(document):
    captured = datetime.strptime(document["meta"]["collected_at"], "%Y-%m-%d %H:%M:%S")
    sampled_at = captured.replace(tzinfo=timezone(timedelta(hours=8))).timestamp()
    rows = {}
    for video in document["videos"]:
        counts = video.get("stat") or {}
        if not video.get("stat_raw_ok") or (counts.get("view") or 0) < 1000:
            continue
        if any(counts.get(field) is None for field in ("like", "coin", "favorite")):
            continue
        bvid = video.get("bvid")
        age = (sampled_at - (video.get("pubdate") or sampled_at)) / 86400
        duration = video.get("duration") or 0
        if not bvid or age <= 0 or duration <= 0:
            continue
        source = video["source"].split(":")[0]
        group = (source, video.get("tname") or "未知分区")
        rows[bvid] = {
            "id": bvid, "group": group,
            "creator": video.get("owner") or bvid,
            "flag": numeric_title_flag(video["title"]),
            "legacy_episode": bool(re.search(r"第\s*\d+\s*[集话]", video["title"])),
            "covariates": (math.log10(counts["view"]), math.log10(1 + age), math.log10(duration)),
            "f7": 100 * score(video, {"favorite": 3, "coin": 2, "like": .3}, "view"),
            "coin": 100 * counts["coin"] / counts["view"]
        }
    return list(rows.values())


def match(focal, controls, limits):
    """Match each title to a distinct control in the same source and category."""
    by_group = defaultdict(list)
    for control in controls:
        by_group[control["group"]].append(control)
    choices = []
    for row in focal:
        neighbors = []
        for control in by_group[row["group"]]:
            distance = [abs(a - b) / limit for a, b, limit in
                        zip(row["covariates"], control["covariates"], limits)]
            if max(distance) <= 1:
                neighbors.append((sum(x * x for x in distance), control["id"], control))
        if neighbors:
            neighbors.sort()
            choices.append((len(neighbors), neighbors[0][0], row["id"], row, neighbors))
    used = set()
    pairs = []
    for _, _, _, row, neighbors in sorted(choices):
        for _, bvid, control in neighbors:
            if bvid not in used:
                used.add(bvid)
                pairs.append((row, control))
                break
    return pairs


def paired_effect(pairs, metric, replicates=2000):
    by_creator = defaultdict(list)
    for focal, control in pairs:
        by_creator[focal["creator"]].append(focal[metric] - control[metric])
    clusters = list(by_creator.values())
    if not clusters:
        return {"estimate": None, "interval": None, "creators": 0}
    effect = median([value for cluster in clusters for value in cluster])
    interval = None
    if len(clusters) >= 5:
        rng = random.Random(20261103)
        boot = []
        for _ in range(replicates):
            picked = rng.choices(clusters, k=len(clusters))
            boot.append(median([value for cluster in picked for value in cluster]))
        boot.sort()
        interval = [boot[int(.025 * (replicates - 1))], boot[int(.975 * (replicates - 1))]]
    return {"estimate": effect, "interval": interval, "creators": len(clusters)}


def examine(rows, flag):
    if flag == "legacy_episode":
        focal = [row for row in rows if row["legacy_episode"]]
        controls = [row for row in rows if not row["legacy_episode"]]
    else:
        focal = [row for row in rows if row["flag"] == flag]
        controls = [row for row in rows if row["flag"] is None]
    pairs = match(focal, controls, LIMITS)
    narrow = match(focal, controls, tuple(.75 * limit for limit in LIMITS))
    return {
        "flagged": len(focal), "matched": len(pairs),
        "unadjusted_f7": median(r["f7"] for r in focal) - median(r["f7"] for r in controls)
        if focal and controls else None,
        "f7": paired_effect(pairs, "f7"),
        "coin": paired_effect(pairs, "coin"),
        "narrow_matched": len(narrow),
        "narrow_f7": paired_effect(narrow, "f7"),
        "source_mix": dict(Counter(a["group"][0] for a, _ in pairs)),
        "median_log_gaps": [
            median(abs(a["covariates"][i] - b["covariates"][i]) for a, b in pairs)
            for i in range(3)
        ] if pairs else []
    }


def signed(x):
    return "—" if x is None else f"{x:+.2f}"


def interval_text(metric):
    interval = metric["interval"]
    return "—" if interval is None else "至".join(signed(value) for value in interval)


def render(result):
    table = []
    labels = {"legacy_episode": "原规则 · 第 N 集或话",
              "series": "新版 · 明确编号", "number_review": "新版 · 可疑数字"}
    for flag, audit in result["groups"].items():
        f7 = audit["f7"]
        row = [labels[flag], f'{audit["matched"]} / {audit["flagged"]}',
               signed(audit["unadjusted_f7"]), signed(f7["estimate"]), interval_text(f7),
               signed(audit["coin"]["estimate"]), str(f7["creators"])]
        table.append("<tr>" + "".join("<td>" + escape(value) + "</td>" for value in row) + "</tr>")
    robustness = []
    for flag, audit in result["groups"].items():
        label = labels[flag]
        gaps = " / ".join(f"{value:.3f}" for value in audit["median_log_gaps"]) or "—"
        robustness.append(f'<li>{label}匹配后，播放、稿龄、时长的对数绝对差中位数为 {gaps}。'
                          f'缩窄匹配范围后剩 {audit["narrow_matched"]} 对，F7 差为 {signed(audit["narrow_f7"]["estimate"])}。</li>')
    legacy = result["groups"]["legacy_episode"]
    if legacy["matched"]:
        comparison = (
            f'原来的标题规则命中 {legacy["flagged"]} 条，混合样本的 F7 中位差为 '
            f'{signed(legacy["unadjusted_f7"])}。匹配成功的 {legacy["matched"]} 对作品中，'
            f'配对差的中位数为 {signed(legacy["f7"]["estimate"])}，'
            f'95% 重抽样区间为 {interval_text(legacy["f7"])}。'
            '两种比较覆盖的作品与统计量不同，单靠这份样本不足以确认集数标题普遍互动偏低。'
        )
    else:
        comparison = "原标题规则缺少满足条件的对照，配对差暂无法估计。"
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>标题筛选复核 · 看过，却不给</title>
<style>
  :root{{color-scheme:light;font:16px/1.7 "Microsoft YaHei UI","Microsoft YaHei",system-ui,sans-serif;color:#33272e;background:#f5eeeb}}
  body{{max-width:900px;margin:auto;padding:34px 22px 56px}}header{{border-bottom:2px solid #45323c;padding-bottom:16px}}
  h1{{font-size:clamp(26px,5vw,42px);line-height:1.25;margin:.4em 0}}h2{{font-size:20px;margin:1.45em 0 .35em}}
  .meta{{color:#76636b;font-size:13px}}.table{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:13px}}
  th,td{{border-bottom:1px solid #d9cbd0;padding:9px 8px;text-align:right;white-space:nowrap}}
  th:first-child,td:first-child{{text-align:left}}th{{font-weight:600;color:#713d55}}a{{color:#78405a}}
  code{{overflow-wrap:anywhere}}small{{display:block;color:#76636b;font-size:12px}}
</style></head><body>
<header><div class="meta">《看过，却不给》方法复核 · 2026-11-04</div>
<h1>标题里的数字能说明什么</h1>
<p>原报告发现，带集数的标题在混合样本里互动偏低。这里用同一份数据检查，在采集来源、分区、播放规模、稿龄和时长接近的作品之间，差异有多大。</p>
<a href="ecosystem-report.html">原调查报告</a> · <a href="../god-shelf.html">视频目录</a></header>
<main>
<h2>同条件比较</h2>
<p>原始快照含 {raw:,} 条记录。复核保留 {kept:,} 条具备完整互动计数、有效稿龄和时长、播放至少 1,000 的去重记录。首行沿用原报告分组，与所有未命中原规则的作品比较。后两行使用新版规则，分别与 {controls:,} 条未触发新版信号的记录比较。</p>
<div class="table"><table><thead><tr><th>标题线索</th><th>匹配 / 命中</th><th>未匹配 F7 中位差</th><th>配对 F7 中位差</th><th>95% 重抽样区间</th><th>配对投币率差</th><th>命中作者数</th></tr></thead><tbody>
{rows}
</tbody></table></div>
<small>单位为每百次播放的加权互动点数或投币数。F7 = 100 ×（3 × 收藏 + 2 × 投币 + 0.3 × 点赞）/ 播放。配对差先逐对相减，再取中位数。</small>
<p>{comparison}</p>
<h2>覆盖范围与敏感性</h2>
<ul>{robustness}</ul>
<p>同来源、同分区的候选对需满足播放、稿龄、时长的常用对数差分别不超过 0.35、0.60、0.45。稿龄由样本记录的采集时间减去投稿时间，再加一天后取对数。这样复跑时文件的修改时间不会改变稿龄。每个对照只用一次，先匹配可选对照较少的标题。区间将配对固定后，对命中作品的作者分组重抽样 2,000 次。</p>
<p>估计仅覆盖成功配对的作品。对照作者的相关性、匹配本身的不确定性与推荐流选择偏差仍然存在。报告中的标题分组对应规则命中，作品内容质量需要独立观看标注。</p>
<h2>目录怎么使用这些数字</h2>
<p>明确连载按本次目录的单篇规则排除。其余可疑编号进入复核，结合标题和作品上下文判断。比如“第484集”是序号，“261103 打歌舞台”是日期，“731”在历史题材中可能是讨论对象。公开上架还需要有明确的复核记录。</p>
<p>下一次验证可从同一采集批次随机抽取普通标题与筛中标题，隐藏互动和筛选状态，让两位观看者独立记录是否为连载、制作和表达是否成立。再报告命中精确率、漏判率与分歧率。</p>
<p class="meta">复跑：<code>python engine/ecosystem_audit.py</code>。样本为 {sample}。</p>
</main></body></html>
""".format(raw=result["raw"], kept=result["kept"], controls=result["controls"],
           rows="\n".join(table), comparison=escape(comparison),
           robustness="".join(robustness), sample=SAMPLE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=ROOT / SAMPLE)
    parser.add_argument("--output", type=Path, default=ROOT / "web/ecosystem-audit.html")
    args = parser.parse_args()
    document = json.loads(args.sample.read_text(encoding="utf-8"))
    rows = sample_rows(document)
    result = {"raw": len(document["videos"]), "kept": len(rows),
              "controls": sum(row["flag"] is None for row in rows),
              "groups": {flag: examine(rows, flag) for flag in ("legacy_episode", "series", "number_review")}}
    args.output.write_text(render(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
