"""Offline candidate mining and blinded review for the craft/resonance profile.

Usage:
  python engine/review_miner.py build --output outputs/review
  python engine/review_miner.py build --reviews feedback.json --output outputs/next
  python engine/review_miner.py evaluate --batch outputs/review/batch.json --reviews feedback.json

No video download, credentials, API request, automatic publishing or model service.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import math

from mining_data import (BAND, band_percentile, build_bands, finite_nonnegative,
                         load_flow_nodes, load_population, load_reference,
                         merge_metadata, owner_fields, read_json, reference_manifest)
from preference_hint import PreferenceHint
from title_screen import numeric_title_flag

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "craft_resonance_v1"
SCHEMA = "bili-review-v1"
BVID = re.compile(r"^BV[0-9A-Za-z]{10}$")
REASONS = {"craft_expression", "sentiment_only", "effort_only", "utility_only", "other"}
# Routing hints only. These words do not establish what the content actually is.
MOTIVE_CUES = ("感谢硬币", "硬币之力", "买药", "众筹", "求助", "感动", "泪目", "哭了",
                "耗时", "历时", "历经", "肝了", "爆肝", "熬夜", "花了三年", "花了一年", "坚持了",
                "捐款", "脑瘫", "救助", "白血病", "骨癌", "生活不能自理", "希望以后你的生活", "重建新家")


def checked_reviews(document):
    if not isinstance(document, dict):
        raise ValueError("标注文件必须是一个JSON对象。")
    if document.get("schema") != SCHEMA or document.get("profile_id") != PROFILE:
        raise ValueError("需要本次制作/共鸣版本的标注文件；旧版盖章不会自动变成新标准的正例。")
    reviews = document.get("reviews")
    if not isinstance(reviews, dict):
        raise ValueError("reviews must be an object")
    out = {}
    for bvid, review in reviews.items():
        if not BVID.fullmatch(bvid) or not isinstance(review, dict):
            raise ValueError(f"Invalid review key: {bvid}")
        for axis in ("craft", "resonance"):
            val = review.get(axis)
            if val is not None and (type(val) is not int or not 0 <= val <= 3):
                raise ValueError(f"{bvid}: {axis} must be 0..3 or null")
        if review.get("reason", "") not in REASONS | {""}:
            raise ValueError(f"{bvid}: unknown reason")
        if type(review.get("watched", False)) is not bool:
            raise ValueError(f"{bvid}: watched must be boolean")
        if not isinstance(review.get("evidence", ""), str):
            raise ValueError(f"{bvid}: evidence must be text")
        # Keep only schema fields, never trust a supplied status, tier or score.
        out[bvid] = {key: review.get(key) for key in
                     ("craft", "resonance", "reason", "watched", "evidence")}
    return out


def review_status(review):
    if not review or review.get("watched") is not True:
        return "unreviewed"
    if (type(review.get("craft")) is not int or type(review.get("resonance")) is not int
            or not 0 <= review["craft"] <= 3 or not 0 <= review["resonance"] <= 3
            or review.get("reason") not in REASONS or not str(review.get("evidence") or "").strip()):
        return "incomplete"
    if review["craft"] >= 2 and review["resonance"] >= 2 and review["reason"] == "craft_expression":
        return "confirmed"
    return "not_fit"


def is_blacklisted(rec, blacklist):
    if rec["bvid"] in set(blacklist.get("bvids") or []):
        return True
    return any((o.get("name") and o["name"] == rec.get("owner")) or
               (o.get("mid") and str(o["mid"]) == str(rec.get("owner_mid") or ""))
               for o in blacklist.get("owners") or [])


def catalog(root):
    mine, samples, flow = root / "data/fav_mine", root / "data/samples", root / "data/flow_graph"
    reference = load_reference(mine, samples)
    bands = build_bands(reference)
    population = load_population(mine, samples)
    nodes = load_flow_nodes(flow)
    backfill = read_json(flow / "pool_view_backfill.json")
    pubdates = read_json(flow / "pubdate_backfill.json")
    blacklist = read_json(root / "data/ml/blacklist.json")
    records = dict(population)
    for bvid, node in nodes.items():
        if bvid in records:
            dates = [d for d in (records[bvid].get("first_seen"), node.get("first_seen")) if d and d != "00000000"]
            records[bvid]["first_seen"] = min(dates) if dates else None
            merge_metadata(records[bvid], node)
            continue
        view = node.get("view")
        rates = [node.get(k) for k in ("coin_rate", "fav_rate", "like_rate")]
        if not finite_nonnegative(view) or not all(finite_nonnegative(v) for v in rates):
            continue
        owner, mid = owner_fields(node.get("owner"))
        rec = {"bvid": bvid, "title": node.get("title") or "", "view": view,
               "coin": round(view * rates[0]), "fav": round(view * rates[1]), "like": round(view * rates[2]),
               "dur": node.get("dur") or 0, "pubdate": node.get("pubdate"), "owner": owner,
               "owner_mid": mid, "tname": node.get("tname") or "", "pic": node.get("pic") or "",
               "src": "flow", "snapshot": node["snapshot"], "first_seen": node.get("first_seen"), "approximate_counts": True}
        if node.get("stat"):
            from mining_data import normalize_video
            exact = normalize_video(node, node["snapshot"])
            if exact:
                rec.update(exact)
        records[bvid] = rec
    rows, blocked = [], 0
    for bvid, rec in sorted(records.items()):
        if not BVID.fullmatch(bvid):
            continue
        if isinstance(rec.get("owner"), dict):
            rec["owner"], rec["owner_mid"] = owner_fields(rec["owner"])
        # Undated sidecars fill metadata only, never overwrite dated raw counters.
        for sidecar in (backfill.get(bvid) or {}, pubdates.get(bvid) or {}):
            fill = dict(sidecar)
            if isinstance(fill.get("owner"), dict):
                fill["owner"], fill["owner_mid"] = owner_fields(fill["owner"])
            merge_metadata(rec, fill)
        if is_blacklisted(rec, blacklist):
            blocked += 1
            continue
        pct = band_percentile(bands, rec["view"], rec["coin"] / max(1, rec["view"]))
        band = round(math.log10(rec["view"]) / BAND) if rec["view"] >= 3000 else None
        rec["coin_percentile"] = pct
        rec["reference_n"] = len(bands.get(band, []))
        rec["motive_cues"] = [word for word in MOTIVE_CUES if word in rec["title"]]
        flags = []
        if not rec.get("dur") or rec["dur"] <= 150:
            flags.append("short")
        title = rec["title"]
        if any(word in title for word in ("黑丝", "白丝", "纯欲", "擦边", "性感", "热舞", "福利姬")):
            flags.append("title_review")
        if (rec["like"] / max(1,rec["view"]) > .20 and rec["coin"] / max(1,rec["view"]) < .02
                and rec["fav"] / max(1,rec["view"]) > .10):
            flags.append("interaction_review")
        number_flag = numeric_title_flag(title)
        if number_flag:
            flags.append(number_flag)
        rec["screen_flags"] = flags
        # Even a score of 1.0 cannot certify content quality.
        rec["status"] = "unreviewed"
        rows.append(rec)
    hint = PreferenceHint(read_json(root / "data/preferences/favorites.json"))
    hint.apply(rows)
    # Editorial hypotheses are independent of the user's quality labels.
    # Metadata-only hypotheses may prioritize viewing, never certify a masterpiece.
    editorial = read_json(root / "data/preferences/editorial_shortlist.json")
    notes = {r["bvid"]: r for r in editorial.get("items") or [] if r.get("bvid")}
    for row in rows:
        if row["bvid"] in notes:
            row["editorial"] = notes[row["bvid"]]
    manifest = reference_manifest(mine, samples)
    manifest["reference_n"] = sum(map(len, bands.values()))
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    catalog_id = hashlib.sha256(payload.encode()).hexdigest()
    return rows, {"catalog_id": catalog_id, "profile_id": PROFILE, "reference": manifest,
                  "catalog_n": len(rows), "blocked_n": blocked, "preference_hint": hint.meta,
                  "limits": ["互动排序不是制作/共鸣评分，也不是神作概率。",
                             "参照库来自收藏夹与首页样本，选择偏差和年代/门类差异仍存在。",
                             "标题线索只分流复核，不能判定内容；缺数据不作负例。",
                             "历史人工判断使用旧标准，不能当作本版本独立验证。"]}


def make_batch(rows, reviews, seed=20261103, size=24):
    """Half recall, quarter motive checks, quarter random exploration of remainder.

    The random arm describes the remaining LOCAL catalog, never the entire site.
    Creator cap is best effort; a small catalog need not fill every arm.
    """
    rng = random.Random(seed)
    eligible = [r for r in rows if "series" not in (r.get("screen_flags") or [])
                and review_status(reviews.get(r["bvid"])) in ("unreviewed", "incomplete")]
    rng.shuffle(eligible)  # deterministic tie breaking without rewarding view count
    ranked = sorted(eligible, key=lambda r: r.get("recall_priority", r["coin_percentile"]) if r.get("recall_priority", r["coin_percentile"]) is not None else -1,
                    reverse=True)
    assignments, used, owners = [], set(), Counter()

    def take(candidates, arm, count):
        if count <= 0:
            return
        for r in candidates:
            key = r.get("owner_mid") or r.get("owner") or r["bvid"]
            if r["bvid"] in used or owners[key] >= 2:
                continue
            assignments.append({"bvid": r["bvid"], "arm": arm})
            used.add(r["bvid"])
            owners[key] += 1
            count -= 1
            if count == 0:
                break

    take([r for r in ranked if not r["motive_cues"] and not r.get("screen_flags") and r["reference_n"] >= 30
          and r["coin_percentile"] is not None], "recall", max(1, size // 2))
    take([r for r in ranked if r["motive_cues"]], "motive_check", size // 4)
    remaining = [r for r in eligible if r["bvid"] not in used]
    rng.shuffle(remaining)
    take(remaining, "explore", size - len(assignments))
    rng.shuffle(assignments)  # arm/percentile are hidden until the reviewer reveals them
    identity = json.dumps({"seed": seed, "assignments": assignments}, sort_keys=True)
    return {"id": hashlib.sha256(identity.encode()).hexdigest()[:20], "seed": seed,
            "assignments": assignments, "requested_size": size}


def evaluate(batch, review_document):
    reviews = checked_reviews(review_document)
    if review_document.get("experiment_id") != batch["experiment"]["id"]:
        raise ValueError("标注不属于该盲审批次，不能拼接为同批对照。")
    if review_document.get("catalog_id") != batch["meta"]["catalog_id"]:
        raise ValueError("目录快照不一致，请用生成该标注时的 batch.json。")
    result = {}
    for arm in ("recall", "motive_check", "explore"):
        ids = [a["bvid"] for a in batch["experiment"]["assignments"] if a["arm"] == arm]
        states = Counter(review_status(reviews.get(b)) for b in ids)
        judged = states["confirmed"] + states["not_fit"]
        result[arm] = {"assigned": len(ids), "judged": judged, "confirmed": states["confirmed"],
                       "coverage": judged / len(ids) if ids else None,
                       "precision_among_judged": states["confirmed"] / judged if judged else None}
    return {"arms": result, "conclusion": "仅为该本地批次的人工复核统计；未评条目不算负例，不证明全站提升。"}


def safe_script_json(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def build(root, output, reviews, seed, size):
    rows, meta = catalog(root)
    experiment = make_batch(rows, reviews, seed, size)
    data = {"schema": SCHEMA, "rows": rows, "meta": meta, "experiment": experiment, "reviews": reviews}
    from discovery_site import build_site
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (("batch.json", data), ("reference_manifest.json", meta["reference"])):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    build_site(rows, meta, output, root, filename="制作与共鸣复核.html", experiment=experiment)
    print(json.dumps({"output": str(output), "catalog_n": len(rows), "review_batch_n": len(experiment["assignments"]),
                      "confirmed_n": sum(review_status(r) == "confirmed" for r in reviews.values())}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--root", type=Path, default=ROOT)
    b.add_argument("--output", type=Path, default=ROOT / "data/review/current")
    b.add_argument("--reviews", type=Path)
    b.add_argument("--seed", type=int, default=20261103)
    b.add_argument("--size", type=int, default=24)
    e = sub.add_parser("evaluate")
    e.add_argument("--batch", type=Path, required=True)
    e.add_argument("--reviews", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "evaluate":
        print(json.dumps(evaluate(read_json(args.batch), read_json(args.reviews)), ensure_ascii=False, indent=2))
    else:
        if not 4 <= args.size <= 200:
            parser.error("--size must be between 4 and 200")
        reviews = checked_reviews(read_json(args.reviews)) if args.reviews else {}
        build(args.root, args.output, reviews, args.seed, args.size)


if __name__ == "__main__":
    main()
