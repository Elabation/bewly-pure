# -*- coding: utf-8 -*-
"""把人工确认过的候选写进上架名单，然后重建并发布（半自动闭环的最后一步）。

用法：
    python engine/accept_picks.py --bvid BV1xx --bvid BV1yy --note "为什么收"
    python engine/accept_picks.py --bvid BV1xx --no-publish      # 只写名单并重建
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

DEFAULT_BASIS = "人工确认（维护者逐条挑选）"


def china_today():
    return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y%m%d")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bvid", action="append", required=True, help="可重复，写几条就传几次")
    parser.add_argument("--admitted", default=china_today(), help="上架日，默认北京时间今天")
    parser.add_argument("--basis", default=DEFAULT_BASIS)
    parser.add_argument("--note", default="", help="具体理由；留空则用标题兜底")
    parser.add_argument("--no-publish", action="store_true", help="只写名单并重建，不推送")
    args = parser.parse_args()

    from review_miner import catalog
    from discovery_site import load_approvals

    rows, _ = catalog(ROOT)
    by = {row["bvid"]: row for row in rows}
    path = ROOT / "data/reference/shelf_approvals.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) else data
    have = {entry["bvid"] for entry in items}

    added, skipped = [], []
    for bvid in args.bvid:
        if bvid in have:
            skipped.append((bvid, "已在名单"))
            continue
        row = by.get(bvid)
        if not row:
            skipped.append((bvid, "不在候选库"))
            continue
        if (row.get("dur") or 0) <= 150:
            skipped.append((bvid, "时长不足 150 秒"))
            continue
        note = args.note.strip() or (row.get("title") or "")[:80]
        items.append({"bvid": bvid, "admitted_on": args.admitted, "basis": args.basis, "note": note,
                      "owner": (row.get("owner") or "")})
        have.add(bvid)
        added.append((bvid, row.get("dur"), row.get("title", "")[:34]))

    if added:
        data["items"] = items if isinstance(data, dict) else items
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("新增上架 %d 条：" % len(added))
        for bvid, duration, title in added:
            print("  + %s %s 秒 %s" % (bvid, duration, title))
    else:
        print("没有新增条目。")
    for bvid, reason in skipped:
        print("  - %s 跳过：%s" % (bvid, reason))

    from publish_discovery import rebuild, publish
    summary = rebuild(ROOT)
    print("重建完成：", json.dumps(summary, ensure_ascii=False))
    if args.no_publish:
        print("未推送（--no-publish）。")
        return
    commit = publish(ROOT, "复核并收录 " + args.admitted + " 的作品")
    print("已推送：", commit)


if __name__ == "__main__":
    main()
