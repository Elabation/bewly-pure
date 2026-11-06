# -*- coding: utf-8 -*-
"""每日 12:00 采集之后自动执行：从当天新候选里挑出 5 条，写成半自动短名单。

只读候选库，不写名单、不发布。上架由人确认后执行 accept_picks.py。
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from title_screen import anime_game_flag, numeric_title_flag  # noqa: E402

PICK_COUNT = 5
SERIES = re.compile(r"第\s*[0-9一二三四五六七八九十百零〇]+\s*[集话期季回夜章节]|合集|全集|连载|更新至")
NOT_WORK = re.compile(r"直播|回放|录播|解说|集锦|盘点|锐评|课程|公开课|讲座|教程|教学|复盘|赛事|新闻|采访")
FORMS = (
    ("手书", re.compile(r"手书|描改")),
    ("定格", re.compile(r"定格|逐帧")),
    ("原创曲", re.compile(r"原创曲|原创音乐|VOCALOID|vocaloid|初音|洛天依|诗岸|重音|言和|乐正")),
    ("短片", re.compile(r"短片|微电影|剧情片")),
    ("动画", re.compile(r"动画|CG|3D|渲染")),
    ("MV", re.compile(r"\bMV\b|PV")),
    ("演奏", re.compile(r"演奏|钢琴|吉他|小提琴|二胡|古筝|贝斯")),
    ("手作", re.compile(r"手作|模型|黏土|木工|手工|改造")),
)


def china_today():
    return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y%m%d")


def form_of(title):
    for name, pattern in FORMS:
        if pattern.search(title or ""):
            return name
    return "其他"


def build_picks(root=ROOT, count=PICK_COUNT, day=None):
    from review_miner import catalog

    day = day or china_today()
    rows, _ = catalog(root)
    approvals_path = root / "data/reference/shelf_approvals.json"
    data = json.loads(approvals_path.read_text(encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) else data
    approved = {entry["bvid"] for entry in items}

    funnel = {"day": day, "fresh": 0, "approved": 0, "short": 0, "long": 0,
              "series": 0, "not_work": 0, "game": 0, "small": 0, "kept": 0}
    pool = []
    for row in rows:
        if row.get("first_seen") == day:
            funnel["fresh"] += 1
        if row["bvid"] in approved:
            funnel["approved"] += 1
            continue
        duration = row.get("dur") or 0
        if duration <= 150:
            funnel["short"] += 1
            continue
        if duration > 1800:
            funnel["long"] += 1
            continue
        title = row.get("title") or ""
        if SERIES.search(title):
            funnel["series"] += 1
            continue
        if NOT_WORK.search(title):
            funnel["not_work"] += 1
            continue
        if anime_game_flag(title):
            funnel["game"] += 1
            continue
        view = row.get("view") or 0
        coin = row.get("coin") or 0
        if view < 30000:
            funnel["small"] += 1
            continue
        row["_ratio"] = coin / view if view else 0
        row["_form"] = form_of(title)
        src = (row.get("src") or "")
        row["_src"] = ("search" if "search" in src else
                       "ranking" if "rank" in src else
                       "homefeed" if "feed" in src else "home")
        row["_new"] = row.get("first_seen") == day
        row["_numflag"] = numeric_title_flag(title) == "number_review"
        pool.append(row)

    for row in pool:
        row["_motive"] = bool(row.get("motive_cues"))
    order = {"search": 0, "ranking": 1, "homefeed": 2, "home": 3}
    pool.sort(key=lambda row: (order.get(row["_src"], 9), row["_motive"], -row["_ratio"]))
    picked, owners, forms = [], set(), {}
    for row in pool:
        owner = (row.get("owner") or "").strip()
        if owner and owner in owners:
            continue
        if forms.get(row["_form"], 0) >= 2:
            continue
        picked.append(row)
        if owner:
            owners.add(owner)
        forms[row["_form"]] = forms.get(row["_form"], 0) + 1
        if len(picked) >= count:
            break
    funnel["pool"] = len(pool)
    funnel["from_search"] = sum(1 for r in pool if r["_src"] == "search")
    funnel["new_today"] = sum(1 for r in pool if r["_new"])
    funnel["kept"] = len(picked)
    return day, funnel, picked


def write_picks(root=ROOT, count=PICK_COUNT, day=None):
    day, funnel, picked = build_picks(root, count, day)
    folder = Path(root) / "data/review"
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["# 今日候选（半自动）%s" % day, "",
             "当天新入候选 %d 条 → 硬筛后剩 %d → 取 %d 条" % (
                 funnel["fresh"], funnel["pool"], len(picked)), "",
             "**全部未观看**，只做了标题/标签层筛选。", "",
             "| # | 标题 | UP | 时长 | 投币率 | 形态 |", "|---|---|---|---|---|---|"]
    for index, row in enumerate(picked, 1):
        flag = " ⚠感动线索" if row.get("_motive") else ""
        lines.append("| %d | %s | %s | %d 秒 | %.1f%% | %s / %s%s |" % (
            index, row.get("title", ""), (row.get("owner") or "").strip()[:16],
            row.get("dur") or 0, row["_ratio"] * 100, row["_form"],
            row["_src"] + ("·今日" if row["_new"] else "·存量"), flag))
        lines.append("| | https://www.bilibili.com/video/%s | | | | |" % row["bvid"])
    lines += ["", "## 确认后执行", "",
              "```powershell",
              "python engine/accept_picks.py --bvid %s --note \"理由\"" % " --bvid ".join(r["bvid"] for r in picked[:1]),
              "```", "",
              "或直接回复「第 1、3 条过」。", "",
              "## 漏斗", ""]
    for key, label in (("fresh", "当天新候"), ("approved", "已上架"), ("short", "≤150 秒"),
                       ("long", ">1800 秒"), ("series", "连载"), ("not_work", "解说/直播"),
                       ("game", "二次元游戏"), ("small", "播放<3 万"), ("kept", "入选短名单")):
        lines.append("- %s：%d" % (label, funnel.get(key, 0)))
    path = folder / ("daily_picks_%s.md" % day)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = {"day": day, "funnel": funnel,
               "picks": [{"bvid": row["bvid"], "title": row.get("title"), "owner": row.get("owner"),
                          "dur": row.get("dur"), "ratio": round(row["_ratio"], 4), "form": row["_form"]}
                         for row in picked]}
    (folder / ("daily_picks_%s.json" % day)).write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return path, funnel, payload["picks"]


if __name__ == "__main__":
    path, funnel, picks = write_picks()
    print("短名单已生成：%s（%d 条）" % (path, len(picks)))
    print("漏斗：", json.dumps(funnel, ensure_ascii=False))
    for index, item in enumerate(picks, 1):
        print("  %d. %-13s %4ds %5.1f%%  %s" % (
            index, item["bvid"], item["dur"], item["ratio"] * 100, item["title"][:40]))
