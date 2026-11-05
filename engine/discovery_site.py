"""Small bootstrap + immutable lazy pages. No whole-catalog JSON in the HTML."""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil

VERSION = "bocchi-v9"
CHUNK_SIZE = 96
PAGE_SIZE = 24
DAILY_SIZE = 9
FIELDS = ("bvid", "title", "owner", "pic", "dur", "pubdate", "view",
          "coin_percentile", "first_seen", "motive_cues", "reference_n", "screen_flags",
          "admitted_on", "review_note", "review_basis")


def compact_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def china_now():
    return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S +08:00")


def asset(folder, extension, body):
    encoded = body.encode("utf-8")
    name = hashlib.sha256(encoded).hexdigest()[:20] + extension
    path = folder / name
    if not path.exists():
        path.write_bytes(encoded)
    return "discovery-data/" + name


def load_approvals(root):
    path = root / "data/reference/shelf_approvals.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["items"]


def approved_streams(rows, approvals):
    by_id = {row["bvid"]: row for row in rows}
    selected = {}
    for entry in approvals:
        bvid = entry["bvid"]
        row = by_id.get(bvid)
        if not row or bvid in selected or (row.get("dur") or 0) <= 150:
            continue
        flags = set(row.get("screen_flags") or [])
        if entry.get("number_checked"):
            flags.discard("number_review")
        if flags:
            continue
        admitted_on = entry["admitted_on"]
        datetime.strptime(admitted_on, "%Y%m%d")
        if not (entry["note"].strip() and entry["basis"].strip()):
            raise ValueError("An approval requires a review note and provenance.")
        record = dict(row, admitted_on=admitted_on, review_note=entry["note"], review_basis=entry["basis"])
        if entry.get("owner"):
            record["owner"] = entry["owner"]
        elif re.fullmatch(r"[0-9a-f]{10}", record.get("owner") or ""):
            record["owner"] = ""
        selected[bvid] = record
    archive = sorted(selected.values(), key=lambda row: row["admitted_on"], reverse=True)
    by_day = {}
    for row in archive:
        by_day.setdefault(row["admitted_on"], []).append(row)
    day = max(by_day, default="")
    # 不设时间窗口：本期 = 最近 DAILY_SIZE 部，跨天取；日历仍按上架日记录。
    streams = {"daily": archive[:DAILY_SIZE], "archive": archive}
    streams.update(("day:" + date, items) for date, items in by_day.items())
    return streams, day


def prepare_streams(rows):
    valid_dates = [r.get("first_seen") for r in rows if r.get("first_seen") and r["first_seen"] != "00000000"]
    day = max(valid_dates) if valid_dates else ""
    priority = lambda r: r.get("recall_priority") if r.get("recall_priority") is not None else -1
    archive = sorted(rows, key=lambda r: (r.get("first_seen") or "", priority(r)), reverse=True)
    eligible = lambda r: (r.get("dur",0)>150 and not r.get("motive_cues") and not r.get("screen_flags"))
    daily = sorted([r for r in rows if r.get("first_seen") == day and eligible(r)], key=lambda r:r.get("pubdate") or 0, reverse=True)
    # Diversity changes order, not claims of content quality.
    def diverse(items):
        buckets, overflow = {}, []
        for item in items:
            owner = item.get("owner_mid") or item.get("owner") or item["bvid"]
            if isinstance(owner, dict):
                owner = str(owner.get("mid") or owner.get("name") or item["bvid"])
            if len(buckets.setdefault(owner, [])) < 2:
                buckets[owner].append(item)
            else:
                overflow.append(item)
        return [r for group in zip_longest_rows(buckets.values()) for r in group] + overflow
    picks = [r for r in sorted(rows, key=priority, reverse=True)
             if r.get("coin_percentile") is not None and r["coin_percentile"] >= .85
             and r.get("reference_n", 0) >= 30 and eligible(r)]
    streams = {"daily": diverse(daily), "picks": diverse(picks)[:600], "archive": archive, "editorial": []}
    for date in sorted(set(valid_dates)):
        streams["day:"+date] = sorted([r for r in rows if r.get("first_seen")==date and eligible(r)],key=lambda r:r.get("pubdate") or 0,reverse=True)
    return streams, day


def zip_longest_rows(groups):
    groups = list(groups)
    for i in range(max([len(g) for g in groups] or [0])):
        yield [g[i] for g in groups if len(g) > i]


def build_site(rows, meta, output, root, filename="god-shelf.html", experiment=None, approvals=None):
    output, root = Path(output), Path(root)
    output.mkdir(parents=True, exist_ok=True)
    folder = output / "discovery-data"
    folder.mkdir(exist_ok=True)
    curated = experiment is None
    if curated:
        if approvals is None:
            approvals = load_approvals(root)
        streams, day = approved_streams(rows, approvals)
    else:
        streams, day = prepare_streams(rows)
    cover_folder = "assets/selected-covers/" if curated else "assets/covers/"
    def public(r):
        record = dict(r)
        cover = root / (cover_folder + r["bvid"] + ".webp")
        if cover.exists():
            record["pic"] = cover_folder + cover.name
            if output.resolve()!=root.resolve():
                dest = output / record["pic"]
                dest.parent.mkdir(parents=True,exist_ok=True)
                if not dest.exists():shutil.copy2(cover,dest)
        return [record.get(field) for field in FIELDS]
    stream_meta = {}
    for key, items in streams.items():
        # The latest date uses the daily stream. Avoid duplicating its manifest
        # in the bootstrap; older dates keep independent lazy streams.
        if key == "day:" + day:
            continue
        chunks = []
        for offset in range(0, len(items), CHUNK_SIZE):
            values = [public(r) for r in items[offset:offset+CHUNK_SIZE]]
            # File:// and HTTP both support lazy script pages. Data are JSON-escaped.
            body = "window.BiliDiscovery.receive(document.currentScript.dataset.key," + compact_json(values) + ");"
            chunks.append(asset(folder, ".js", body))
        stream_meta[key] = {"count": len(items), "chunks": chunks}
    index = asset(folder, ".json", compact_json([public(r) for r in streams["archive"]]))
    worker = "const INDEX=" + json.dumps(index.split("/")[-1]) + ";\n" + (root / "engine/discovery_search.js").read_text(encoding="utf-8")
    worker_path = asset(folder, ".worker.js", worker)
    playlist_path = root / "assets/music/playlist.json"
    music = json.loads(playlist_path.read_text(encoding="utf-8")) if playlist_path.exists() else []
    images = {"assets/bocchi-livehouse-approved.webp", "assets/livehouse-room-v8.webp",
              "assets/calendar-ticket-v1.jpg"}
    for track in music:
        if not re.fullmatch(r"assets/music/tracks/[a-d][0-9]{2}\.mp3", track["src"]):
            raise ValueError("Playlist audio must be bundled with the site.")
        if not (root / track["src"]).is_file():
            raise FileNotFoundError(track["src"])
        images.add(track["art"])
    if output.resolve() != root.resolve():
        media = images | {track["src"] for track in music}
        for relative in sorted(media):
            source = root / relative
            if source.is_file():
                destination = output / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
    boot = {"version": VERSION, "curated": curated, "fields": FIELDS, "pageSize": PAGE_SIZE, "chunkSize": CHUNK_SIZE,
            "catalog_id": meta["catalog_id"], "experiment_id": (experiment or {}).get("id"),
            "generated_at": china_now(), "latest_day": day, "total": len(streams["archive"]), "streams": stream_meta,
            "initial": [public(r) for r in streams["daily"][:PAGE_SIZE]], "worker": worker_path,
            "calendar": {key[4:]:len(value) for key,value in streams.items() if key.startswith("day:")},
            "music": music,
            "collection": json.loads((root / "data/review/last_success.json").read_text(encoding="utf-8"))
            if (root / "data/review/last_success.json").exists() else None}
    template = (root / "engine/discovery_template.html").read_text(encoding="utf-8")
    style = (root / "engine/discovery.css").read_text(encoding="utf-8")
    js = (root / "engine/discovery_ui.js").read_text(encoding="utf-8")
    companion = (root / "engine/discovery_companion.js").read_text(encoding="utf-8") if (root / "engine/discovery_companion.js").exists() else ""
    html = template.replace("__STYLE__", style).replace("__BOOT__", compact_json(boot)).replace("__UI__", js+"\n"+companion)
    encoded = html.encode("utf-8")
    if len(encoded) > 150000:
        raise ValueError("Bootstrap exceeds 150 KB performance budget")
    (output / filename).write_bytes(encoded)
    # Public builds purge stale chunks so a withdrawn title also leaves search.
    # Private builds keep one prior generation for in-flight page loads.
    current = {p.split("/")[-1] for s in stream_meta.values() for p in s["chunks"]}
    current.update((index.split("/")[-1], worker_path.split("/")[-1]))
    manifest_path = output / "discovery-assets.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    preceding = [] if curated else previous.get("current", [])
    keep = current | set(preceding)
    for path in folder.iterdir():
        if path.name not in keep and path.is_file() and re.fullmatch(r"[a-f0-9]{20}\.(?:js|json|worker\.js)", path.name):
            path.unlink()
    manifest_path.write_text(json.dumps({"current": sorted(current), "previous": preceding}), encoding="utf-8")
    summary = {"version": VERSION, "html_bytes": len(encoded), "initial_rows": len(boot["initial"]),
               "catalog_rows": len(rows), "published_rows": len(streams["archive"]),
               "daily_rows": len(streams["daily"]), "latest_day": day}
    (output / "discovery-status.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    return summary
