# -*- coding: utf-8 -*-
"""Neuro-sama 主题挖掘 —— 搜索定位 + 相关推荐聚簇 + v3 带内百分位判档 → 朋友特供小货架。

流程：
  1) 搜索 API（7 关键词，wbi）→ 候选去重，按播放取 top
  2) fetch_view 全量补全（搜索卡无 coin/fav，必须补）+ 拿 aid
  3) 相关推荐一条龙：从币率最高的 2-3 支种子扩挖（related 自带全 stat，免费数据）
  4) 全体打分：带内投币百分位（基线 9,3xx 条冻结）+ v3_tier（R9 声援提档对 Neuro 圈可能连环触发）
  5) docs/personal/neuro-shelf.html + 根目录副本（推给朋友直接看）
产出：data/fav_mine/neuro_hunt_YYYYMMDD.json
"""
import json
import math
import os
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
import v3_rules as _rules  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
OUTD = os.path.join(ROOT, "docs", "personal")
DATE = time.strftime("%Y%m%d")
BAND = 0.2
VIEW_FLOOR = 200
KEYWORDS = ["Neuro-sama", "Neuro 切片", "Neuro 歌曲", "Neuro 直播", "Evil Neuro", "Vedal", "neuro sama"]
FV_BUDGET = 90
REL_BUDGET = 3
REL_SEEDS = 3


def is_neuro(r):
    """Neuro 物种判定：标题/UP 名含生态关键词（防 related 图漂移进泛手书）。"""
    s = (r.get("title") + " " + (r.get("owner") or "")).lower()
    return any(k in s for k in ("neuro", "vedal", "evil", "牛肉", "小牛", "牛牛", "烤肉", "蜂群"))


def band_medians():
    """重建带 → 币率数组（从池文件，带 view）。"""
    bands = defaultdict(list)
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                if (v.get("view") or 0) >= 3000 and v.get("bvid"):
                    st = v.get("stat") or {}
                    view = max(1, v.get("view") or 1)
                    bands[round(math.log10(view) / BAND)].append((st.get("coin") or 0) / view)
    return {k: sorted(v) for k, v in bands.items()}


def pct_of(band_arr, x):
    if not band_arr:
        return None
    lo = sum(1 for a in band_arr if a < x)
    return lo / max(1, len(band_arr) - 1) if len(band_arr) > 1 else 0.5


def main():
    t0 = time.time()
    cli = BiliClient(interval=0.5)
    bands = band_medians()
    n_base = sum(len(v) for v in bands.values())
    print(f"[base] 带基线 {n_base} 支", flush=True)

    universe = {}

    def add(item, src, kw=None):
        bvid = item.get("bvid")
        if not bvid:
            return None
        st = item.get("stat") or {}
        view = st.get("view") or item.get("view") or 0
        if view < VIEW_FLOOR or bvid in universe:
            return None
        vr = max(1, view)
        coin, fav, like = st.get("coin") or 0, st.get("favorite") or 0, st.get("like") or 0
        title = re.sub(r'<em class="keyword">|</em>', "", item.get("title") or "")
        k = round(math.log10(view) / BAND)
        p = pct_of(bands.get(k), coin / vr)
        tier, firings = _rules.v3_tier(p if p is not None else 0.5, item.get("duration") or 0,
                                       fav / vr, coin / vr, like / vr, title)
        rec = {"bvid": bvid, "aid": item.get("aid"), "title": title,
               "owner": (item.get("owner") or {}).get("name") if isinstance(item.get("owner"), dict) else (item.get("owner") or "?"),
               "tname": item.get("tname") or "", "view": view, "dur": item.get("duration") or 0,
               "pubdate": item.get("pubdate"), "pic": item.get("pic") or "",
               "coin_rate": round(coin / vr, 5), "fav_rate": round(fav / vr, 5), "like_rate": round(like / vr, 5),
               "pct": round(p, 4) if p is not None else None, "tier": tier, "firings": firings,
               "src": src, "kw": kw}
        universe[bvid] = rec
        return rec

    # ---- 1) 种子直取（外部搜索定位的 Neuro 物种锚点；B站搜索通道今日 412 风控）----
    SEEDS = ["BV1tWb3zqEib", "BV1oCt96SE3T", "BV1Q1vyBAEvE", "BV1n98k6wEwf", "BV1fbdQBSErf",
             "BV1tZ8u6JEUS", "BV1LH4y1L7LZ", "BV1FFzYYhEce", "BV1GqJj6DEhs", "BV1JK41187Lb",
             "BV1KE421j7Hq", "BV1bbbo6DEg3"]
    for bvid in SEEDS:
        try:
            v = cli.fetch_view(bvid)
        except Exception as e:
            print(f"[seed] {bvid} fail: {str(e)[:60]}", flush=True)
            continue
        st = v.get("stat") or {}
        v["view"] = st.get("view") or 0
        add(v, "seed")
        print(f"[seed] {bvid} 《{(v.get('title') or '')[:26]}》 播放{v['view']:,}", flush=True)
    print(f"[seed] 种子入库 {len(universe)} 支", flush=True)

    # ---- 2) 相关推荐两跳聚簇（Neuro 物种在 related 空间高度互链）----
    rel_left = REL_BUDGET * 2
    expanded = set()

    def related_of(aid):
        nonlocal rel_left
        if rel_left <= 0 or not aid:
            return []
        rel_left -= 1
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/archive/related",
                             {"aid": aid}, tries=2)
            return d if isinstance(d, list) else []
        except Exception:
            return []

    hop1 = sorted([r for r in universe.values() if r.get("aid")], key=lambda x: -(x["coin_rate"] or 0))[:3]
    hop2_cands = []
    for s in hop1:
        items = related_of(s["aid"])
        n0 = len(universe)
        for it in items:
            r = add(it, "related")
            if r and r.get("aid") and is_neuro(r):
                hop2_cands.append(r)
        expanded.add(s["bvid"])
        print(f"[related] hop1《{s['title'][:22]}》 +{len(universe) - n0}", flush=True)
    for s in sorted(hop2_cands, key=lambda x: -(x["coin_rate"] or 0))[:3]:
        if s["bvid"] in expanded or rel_left <= 0:
            continue
        items = related_of(s["aid"])
        n0 = len(universe)
        for it in items:
            add(it, "related")
        print(f"[related] hop2《{s['title'][:22]}》 +{len(universe) - n0}", flush=True)
    print(f"[related] 完成，宇宙 {len(universe)} 支", flush=True)

    # ---- 4) 汇总 ----
    from collections import Counter

    rows = sorted(universe.values(), key=lambda r: ({"神作候选": 0, "优秀候选": 1, "一般候选": 2, "垃圾候选": 3}.get(r["tier"], 4),
                                                    -(r["pct"] or 0)))
    neuro_rows = [r for r in rows if is_neuro(r)]
    drift = [r for r in rows if not is_neuro(r)]
    tiers = Counter(r["tier"] for r in neuro_rows)
    print(f"\n=== 汇总：宇宙 {len(rows)} 支，其中 Neuro 物种 {len(neuro_rows)}（外围漂移 {len(drift)} 已剔除）===", flush=True)
    for t in ("神作候选", "优秀候选", "一般候选", "垃圾候选"):
        print(f"  {t}: {tiers.get(t, 0)}", flush=True)
    print("\nTop 15：", flush=True)
    for r in neuro_rows[:15]:
        r9 = [f for f in r["firings"] if f.startswith("R9")]
        print(f"  [{r['tier'][:2]}] pct={r['pct']:.2f} 《{r['title'][:34]}》 币{r['coin_rate']:.1%} 播放{r['view']:,} {r['owner'][:12]}" + (f" ｜{r9[0][:22]}" if r9 else ""), flush=True)

    out = {"meta": {"date": DATE, "keywords": KEYWORDS, "n": len(rows), "baseline": n_base},
           "tiers": dict(tiers), "rows": rows}
    json.dump(out, open(os.path.join(MINE, f"neuro_hunt_{DATE}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    build_page(neuro_rows, n_base)
    print(f"[done] {time.time() - t0:.0f}s", flush=True)


def build_page(rows, n_base):
    god = [r for r in rows if r["tier"] == "神作候选"]
    good = [r for r in rows if r["tier"] == "优秀候选"]
    rest = [r for r in rows if r["tier"] not in ("神作候选", "优秀候选")]
    rest.sort(key=lambda r: -(r["pct"] or 0))

    def card(r):
        url = f"https://www.bilibili.com/video/{r['bvid']}"
        d = time.localtime(r["pubdate"]) if r.get("pubdate") else None
        pub = time.strftime("%Y-%m-%d", d) if d else "—"
        r9 = "｜R9声援" if any(str(f).startswith("R9") for f in (r.get("firings") or [])) else ""
        tcolor = {"神作候选": "#B8912F", "优秀候选": "#334EAC"}.get(r["tier"], "#7096D1")
        return f'''<div class="card" data-g="{r["tier"]}">
<a class="cov" href="{url}" target="_blank" rel="noreferrer"><img src="{r["pic"]}" referrerpolicy="no-referrer" loading="lazy" alt=""></a>
<div class="inf">
<div class="ti"><a href="{url}" target="_blank" rel="noreferrer">{r["title"]}</a></div>
<div class="mt">{r["owner"]} · 播放 {r["view"]:,} · {int(r["dur"] or 0)//60}:{int(r["dur"] or 0)%60:02d} · {pub}</div>
<div class="ch"><span class="b" style="background:{tcolor};color:#F7F2EB">{r["tier"]}</span>
<span class="b"><b>pct</b>｜{(r["pct"] or 0):.2f}</span>
<span class="b"><b>币率</b>｜{r["coin_rate"]:.1%}</span>
<span class="b"><b>藏率</b>｜{r["fav_rate"]:.1%}</span><span class="b">播放带内投币排位{r9}</span></div>
</div></div>'''

    def sec(title, lst, note=""):
        if not lst:
            return ""
        return f'<p class="lead" style="margin:18px 0 0"><b>{title} · {len(lst)} 支</b> {note}</p>' + "".join(card(r) for r in lst)

    tabs = "".join(f'<button class="tab{" on" if k == "ALL" else ""}" data-f="{k}" onclick="setF(\'{k}\')">{lbl} {n}</button>'
                   for k, lbl, n in [("ALL", "全部", len(rows)), ("G", "神作", len(god)), ("E", "优秀", len(good)), ("R", "其余", len(rest))])
    html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Neuro-sama 神作小货架</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#F7F2EB;color:#081F5C;
 font-family:system-ui,-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;font-size:13.5px}}
.top{{position:sticky;top:0;background:#F7F2EB;border-bottom:1px solid #D0E3FF;padding:14px 18px 10px;z-index:9}}
h1{{font-family:'KaiTi','STKaiti',serif;font-size:20px;margin:0 0 2px;font-weight:800}}
.lead{{font-size:12px;color:#7096D1;margin:0 0 8px;line-height:1.6}}
.tab{{display:inline-block;border:1px dashed #7096D1;border-radius:999px;padding:3px 12px;margin:0 6px 6px 0;
 font-size:11px;color:#334EAC;cursor:pointer;background:none}}
.tab.on{{background:#081F5C;color:#F7F2EB;border-style:solid;border-color:#081F5C}}
.wrap{{max-width:860px;margin:0 auto;padding:14px 16px 60px}}
.card{{display:flex;background:#fff;border:1px solid #D0E3FF;border-radius:8px;margin:10px 0;overflow:hidden}}
.cov{{flex:0 0 200px}}.cov img{{width:200px;height:125px;object-fit:cover;display:block}}
.inf{{flex:1;padding:9px 12px;min-width:0}}
.ti{{font-size:13.5px;font-weight:600;line-height:1.4}}
.ti a{{color:#081F5C;text-decoration:none}}.ti a:hover{{text-decoration:underline dotted #7096D1}}
.mt{{font-size:11px;color:#7096D1;margin:3px 0 6px}}
.ch{{margin-bottom:2px}}
.b{{display:inline-block;border-radius:4px;padding:2px 7px;font-size:11px;margin:0 6px 4px 0;
 background:#D0E3FF;color:#334EAC;font-variant-numeric:tabular-nums}}
.b b{{font-weight:700}}
@media(max-width:640px){{.card{{flex-direction:column}}.cov{{flex:none}}.cov img{{width:100%;height:170px}}}}
</style></head><body>
<div class="top"><h1>Neuro-sama 神作小货架 · 朋友特供</h1>
<p class="lead">甄选口径与主货架一致：带内投币百分位（Δlog₁₀=0.2 排位，基线 {n_base:,} 支）+ R9 声援提档。
Neuro 圈的切片/翻译/二创靠「真金投币」说话——pct 越高越是粉丝用币投票的硬货。已判 {len(rows)} 支：神作 {len(god)} / 优秀 {len(good)}。点卡片直达 B 站。</p>
{tabs}</div><div class="wrap">
{sec("神作候选", god, "· 带内投币排位 top，闭眼入")}
{sec("优秀候选", good, "· 稳了好吗")}
{sec("其余入库", rest, "· 备播")}
</div><script>
function setF(f){{document.querySelectorAll('.card').forEach(function(c){{
 var show=f==='ALL'||c.dataset.g===(f==='G'?'神作候选':f==='E'?'优秀候选':'一般候选')||(f==='R'&&c.dataset.g!=='神作候选'&&c.dataset.g!=='优秀候选');
 c.style.display=show?'':'none'}});
 document.querySelectorAll('.tab').forEach(function(t){{t.classList.toggle('on',t.dataset.f===f)}})}}
</script></body></html>'''
    out = os.path.join(OUTD, "neuro-shelf.html")
    open(out, "w", encoding="utf-8").write(html)
    print(f"[page] {out}（{len(rows)} 卡）", flush=True)


if __name__ == "__main__":
    main()
