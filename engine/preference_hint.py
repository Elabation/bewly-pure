"""A small, explicit interest hint from favorite TITLES, never quality labels.

No external model. Character-bigram TF-IDF supplies a reproducible topic overlap.
The hint may move recall priority by at most 0.10 on a 0..1 scale.
"""
from collections import Counter
import math
import re

TASTE_WEIGHT = 0.10


def title_terms(title):
    title = re.sub(r"4k|60fps|60帧|高清|修复|完整版|神级|神作|经典|无损|教程|中字|官方|视频", "", title.lower())
    chunks = re.findall(r"[\u4e00-\u9fff]+|[a-z][a-z0-9+]{1,}", title)
    return set(term for chunk in chunks for term in
               ([chunk] if re.fullmatch(r"[a-z0-9+]+", chunk) else
                [chunk[i:i+2] for i in range(max(0, len(chunk)-1))]))


class PreferenceHint:
    def __init__(self, document):
        unique = {}
        for item in document.get("videos") or []:
            if item.get("bvid") and item.get("title") and "已失效" not in item["title"]:
                unique.setdefault(item["bvid"], item)
        docs = [title_terms(v["title"]) for v in unique.values()]
        freq = Counter(term for terms in docs for term in terms)
        self.idf = {t: math.log((1+len(docs))/(1+n))+1 for t, n in freq.items()}
        centroid = Counter()
        for terms in docs:
            norm = math.sqrt(sum(self.idf[t]**2 for t in terms)) or 1
            for term in terms:
                centroid[term] += self.idf[term] / norm
        norm = math.sqrt(sum(v*v for v in centroid.values())) or 1
        self.vector = {t: v/norm for t, v in centroid.items()}
        self.favorite_ids = set(unique)
        self.meta = {"usable_favorites": len(unique), "raw_entries": len(document.get("videos") or []),
                     "weight": TASTE_WEIGHT, "source_url": document.get("source_url"),
                     "meaning": "Title topic overlap only; favorites supply no quality label or confirmation."}

    def similarity(self, title):
        terms = title_terms(title)
        # Unknown terms remain in the denominator rather than disappearing.
        values = {term: self.idf.get(term, math.log(1+len(self.favorite_ids))+1) for term in terms}
        norm = math.sqrt(sum(v*v for v in values.values())) or 1
        return min(1.0, max(0.0, sum(value*self.vector.get(term, 0) for term, value in values.items())/norm))

    def apply(self, rows):
        for row in rows:
            affinity = self.similarity(row["title"])
            row["taste_hint"] = affinity
            row["in_favorites"] = row["bvid"] in self.favorite_ids
            pct = row["coin_percentile"]
            row["recall_priority"] = ((1-TASTE_WEIGHT)*pct+TASTE_WEIGHT*affinity
                                      if pct is not None and self.favorite_ids else pct)
