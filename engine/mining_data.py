"""Shared, offline data loading. Engagement is evidence for recall, not quality.

Reference membership is frozen by capture date. Counts always come from one
snapshot; metadata may be filled from another. Never manufacture per-field maxima.
"""
from bisect import bisect_left
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

BAND = 0.2
REFERENCE_CUTOFF = "20260903"
HOME_SAMPLES = ("sample_20260903_185231.json", "sample_20260903_203054.json")
FLOW_PATTERNS = ("godflow_2*.json", "godflowdeep_*.json", "godflowbnopad_*.json",
                 "godflowretro_*.json", "godflowdaily_*.json")


def read_json(path):
    # A missing optional sidecar is normal; corrupt existing data must be visible.
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def capture_key(path):
    match = re.search(r"(20\d{6})(?:_(\d{6}))?", Path(path).name)
    return (match.group(1) + (match.group(2) or "000000")) if match else "00000000000000"


def population_paths(mine, samples, cutoff=None):
    paths = [Path(samples) / name for name in HOME_SAMPLES if (Path(samples) / name).exists()]
    paths += [p for p in Path(mine).glob("favmine_*.json")
              if "_analysis" not in p.name and "merged" not in p.name]
    return sorted((p for p in paths if cutoff is None or capture_key(p)[:8] <= cutoff),
                  key=lambda p: (capture_key(p), p.name))


def owner_fields(owner):
    if isinstance(owner, dict):
        return str(owner.get("name") or ""), str(owner.get("mid") or "")
    return str(owner or ""), ""


def finite_nonnegative(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def normalize_video(video, source):
    stat = video.get("stat") or {}
    view = stat.get("view") if stat.get("view") is not None else video.get("view")
    counts = {"view": view, "coin": stat.get("coin"),
              "fav": stat.get("favorite", stat.get("fav")), "like": stat.get("like")}
    if not video.get("bvid") or not all(finite_nonnegative(v) for v in counts.values()):
        return None
    owner, owner_mid = owner_fields(video.get("owner") or video.get("up"))
    owner_mid = owner_mid or str(video.get("owner_mid") or "")
    return {"bvid": video["bvid"], "title": video.get("title") or "", **counts,
            "dur": video.get("duration") or video.get("dur") or 0,
            "pubdate": video.get("pubdate"), "owner": owner, "owner_mid": owner_mid,
            "tname": video.get("tname") or "", "pic": video.get("pic") or "",
            "src": video.get("src") or ("home" if "daily" in source or "sample_" in source else "mine"),
            "snapshot": source, "approximate_counts": False}


def merge_metadata(new, old):
    for field in ("title", "dur", "pubdate", "owner", "owner_mid", "tname", "pic"):
        if not new.get(field) and old.get(field):
            new[field] = old[field]
    return new


def load_population(mine, samples, cutoff=None):
    population = {}
    for path in population_paths(mine, samples, cutoff):
        for video in read_json(path).get("videos") or []:
            rec = normalize_video(video, path.name)
            if rec is None:
                continue
            old = population.get(rec["bvid"], {})
            rec["first_seen"] = old.get("first_seen") or capture_key(path)[:8]
            population[rec["bvid"]] = merge_metadata(rec, population.get(rec["bvid"], {}))
    return population


def load_reference(mine, samples):
    expected_path = Path(mine).parent / "reference/mining_v4_manifest.json"
    if expected_path.exists():
        expected = read_json(expected_path)
        actual = reference_manifest(mine, samples)
        if expected.get("cutoff") != actual["cutoff"] or expected.get("files") != actual["files"]:
            raise ValueError("Frozen reference changed: inspect raw files and explicitly rebuild the reference manifest.")
    return load_population(mine, samples, REFERENCE_CUTOFF)


def build_bands(population):
    bands = defaultdict(list)
    for rec in population.values():
        if rec["view"] >= 3000:
            bands[round(math.log10(rec["view"]) / BAND)].append(rec["coin"] / rec["view"])
    return {key: sorted(values) for key, values in bands.items()}


def percentile(values, value):
    """Empirical P(X < value), in [0,1]. One/two observations cannot define a band.

    No binomial confidence interval: coin counts are not unique viewers.
    """
    if len(values) < 3 or not finite_nonnegative(value):
        return None
    return bisect_left(values, value) / len(values)


def band_percentile(bands, view, coin_rate):
    if not finite_nonnegative(view) or view < 3000:
        return None
    return percentile(bands.get(round(math.log10(view) / BAND), []), coin_rate)


def reference_manifest(mine, samples):
    return {"cutoff": REFERENCE_CUTOFF, "files": [
        {"path": str(p.parent.name + "/" + p.name), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in population_paths(mine, samples, REFERENCE_CUTOFF)],
        "meaning": "Frozen selected reference sample; not an unbiased Bilibili population or a quality probability."}


def load_flow_nodes(folder):
    nodes = {}
    paths = {p for pattern in FLOW_PATTERNS for p in Path(folder).glob(pattern)}
    for path in sorted(paths, key=lambda p: (capture_key(p), p.name)):
        run = read_json(path)
        flows = list(run.get("flows") or [])
        for arm in (run.get("arms") or {}).values():
            flows.extend(arm.get("flows") or [])
        for flow in flows:
            for raw in flow.get("nodes") or []:
                if not raw.get("bvid"):
                    continue
                rec = deepcopy(raw)
                rec["snapshot"] = path.name
                old = nodes.get(rec["bvid"], {})
                rec["first_seen"] = old.get("first_seen") or capture_key(path)[:8]
                count_fields = ("view", "coin_rate", "fav_rate", "like_rate")
                if (not all(finite_nonnegative(rec.get(k)) for k in count_fields)
                        and all(finite_nonnegative(old.get(k)) for k in count_fields)):
                    for field in count_fields:
                        rec[field] = old[field]
                    rec["snapshot"] = old["snapshot"]
                # Last complete snapshot wins; earlier metadata is still useful.
                nodes[rec["bvid"]] = merge_metadata(rec, nodes.get(rec["bvid"], {}))
    return nodes


def historical_seed_approved(row):
    """Only an explicit, unambiguous human positive; never the machine 'v3' field.

    Historical quality labels are not labels for the new craft/resonance profile.
    """
    verdict = str(row.get("verdict") or "").strip()
    negative = ("不神", "不可能神", "不可能是神", "不是神", "不算神", "不值得神", "不够神",
                "不及神", "但不神", "惩罚", "不评价", "不好评价", "存疑", "有待", "门槛", "边边",
                "感谢类", "肝", "辛苦", "感动", "卖惨", "鼓励")
    return bool(row.get("bvid") and "神作" in verdict and not any(w in verdict for w in negative))
