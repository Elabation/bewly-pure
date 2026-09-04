# -*- coding: utf-8 -*-
"""R4 盲测第二轮 —— 数值驱动选样（标题零介入）+ 盲审页生成。

协议：
  · 选样只用数值（率/时长/播放/诚意比），标题/UP 不进入任何选择逻辑
  · 页面隐藏标题与UP名（模糊），判定一张揭示一张；导出后可「揭示全部」
  · 细胞按第一轮假设设计：短时长=擦边? 赞率倒挂? 高带诚意比二分?
挖矿：
  · 首页热门 12 页（数值评分）
  · 池内 205 触发 + 全池零请求扫描（数值）
  · 相关推荐一条龙：种子 = 池内触发按「时长桶 × 诚意比中位」数值选点（深度2，预算15次）
细胞与配额（判定回填后检验第一轮假设）：
  A 触发·短   r4 & view<10万 & dur≤21s            配额10
  B 触发·中   r4 & view<10万 & 21<dur≤45          配额6
  C 触发·长   r4 & view<10万 & dur>45             配额6
  D 高带低诚  view≥30万 & sinc≤0.11 & 未触发       配额10
  E 高带边界  view≥30万 & 0.11<sinc≤0.20          配额3
  F 低带边缘  NM-A（币<2% 藏>10% 赞12~20%）        配额6
  G 随机对照  低带未触发随机（seed=42）             配额8
产出：data/fav_mine/r4_blindhunt_20260905.json + docs/personal/r4-blind-review.html + 根目录副本
"""
import json
import math
import os
import random
import sys
import time
import html as H

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_stats import BiliClient  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "data", "fav_mine")
SDIR = os.path.join(ROOT, "data", "samples")
OUTD = os.path.join(ROOT, "docs", "personal")
DATE = "20260905"
KEY = f"r4_blind_review_{DATE}"
QUOTA = {"A": 10, "B": 6, "C": 6, "D": 10, "E": 3, "F": 6, "G": 8}
FV_BUDGET = 80
REL_BUDGET = 15
SEED = 42


def fired(lr, cr, fr):
    return lr > 0.20 and cr < 0.02 and fr > 0.10


def nma(lr, cr, fr):
    return cr < 0.02 and fr > 0.10 and 0.12 < lr <= 0.20


# ---------- 宇宙构建（数值 only）----------
def universe_add(univ, bvid, view, dur, lr, cr, fr, src):
    if not bvid or bvid in univ or view < 3000:
        return
    univ[bvid] = {"bvid": bvid, "view": view, "dur": dur or 0, "lr": lr, "cr": cr, "fr": fr,
                  "sinc": (cr / fr) if fr > 0 else None, "src": src}


def scan_pool(univ):
    n0 = len(univ)
    for fn in os.listdir(SDIR):
        if fn.startswith("sample_") and fn.endswith(".json"):
            try:
                p = json.load(open(os.path.join(SDIR, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                st = v.get("stat") or {}
                view = st.get("view") or v.get("view") or 0
                if view < 3000 or not v.get("bvid"):
                    continue
                vr = max(1, view)
                universe_add(univ, v["bvid"], view, v.get("duration") or 0,
                             (st.get("like") or 0) / vr, (st.get("coin") or 0) / vr, (st.get("favorite") or 0) / vr, "home")
    for fn in os.listdir(MINE):
        if fn.startswith("favmine_") and fn.endswith(".json") and "_analysis" not in fn and "merged" not in fn:
            try:
                p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            except Exception:
                continue
            for v in (p.get("videos") or []):
                if (v.get("view") or 0) < 3000 or not v.get("bvid"):
                    continue
                st = v.get("stat") or {}
                view = v.get("view") or 0
                vr = max(1, view)
                universe_add(univ, v["bvid"], view, v.get("duration") or 0,
                             (st.get("like") or 0) / vr, (st.get("coin") or 0) / vr, (st.get("favorite") or 0) / vr, "mine")
    return len(univ) - n0


def main():
    # --page-only：跳过网络挖掘，从已落盘的卡片 JSON 直接重建页面
    if "--page-only" in sys.argv:
        path = os.path.join(MINE, f"r4_blindhunt_{DATE}.json")
        data = json.load(open(path, encoding="utf-8"))
        build_page(data["cards"], data["counts"])
        return
    rng = random.Random(SEED)
    cli = BiliClient(interval=0.5)
    univ = {}
    n_pool = scan_pool(univ)
    print(f"[universe] 池+样本 {n_pool} 支", flush=True)

    # 排除第一轮已审 38 支
    excl = set()
    try:
        old = json.load(open(os.path.join(MINE, f"r4_review_cards_{DATE}.json"), encoding="utf-8"))
        excl = {c["bvid"] for c in old}
    except Exception:
        pass

    # 断点续填：已有卡片直接复用，只补缺额细胞
    out_path = os.path.join(MINE, f"r4_blindhunt_{DATE}.json")
    picked = []
    if os.path.exists(out_path):
        try:
            picked = json.load(open(out_path, encoding="utf-8")).get("cards") or []
        except Exception:
            picked = []
    if picked:
        have = {k: sum(1 for c in picked if c["cell"] == k) for k in QUOTA}
        print(f"[resume] 已有 {len(picked)} 张: " + " ".join(f"{k}={have[k]}" for k in QUOTA), flush=True)

    # ---- A) 首页热门（数值评分）----
    pop_hits = 0
    for pn in range(1, 13):
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/popular", {"ps": 20, "pn": pn}, tries=2)
            items = (d or {}).get("list") or []
        except Exception:
            continue
        for it in items:
            st = it.get("stat") or {}
            view = st.get("view") or 0
            vr = max(1, view)
            lr, cr, fr = (st.get("like") or 0) / vr, (st.get("coin") or 0) / vr, (st.get("favorite") or 0) / vr
            universe_add(univ, it.get("bvid"), view, it.get("duration") or 0, lr, cr, fr, "popular")
            if fired(lr, cr, fr):
                pop_hits += 1
    print(f"[popular] 12页扫完，触发 {pop_hits}，宇宙 {len(univ)}", flush=True)

    # ---- B) 一条龙（数值选种子：时长桶内诚意比中位点）----
    rel_left = REL_BUDGET
    fires_pool = sorted([u for u in univ.values() if fired(u["lr"], u["cr"], u["fr"]) and u["dur"] > 0 and u["bvid"] not in excl],
                        key=lambda x: x["dur"])
    buckets = {"short": [u for u in fires_pool if u["dur"] <= 21],
               "mid": [u for u in fires_pool if 21 < u["dur"] <= 45],
               "long": [u for u in fires_pool if u["dur"] > 45]}
    seeds = []
    for name, lst in buckets.items():
        if lst:
            lst2 = sorted(lst, key=lambda x: x["sinc"] if x["sinc"] is not None else 9)
            seeds.append(lst2[len(lst2) // 2]["bvid"])  # 桶内 sinc 中位点，纯数值
    nmas = sorted([u for u in univ.values() if nma(u["lr"], u["cr"], u["fr"]) and u["bvid"] not in excl],
                  key=lambda x: x["lr"])
    if nmas:
        seeds.append(nmas[len(nmas) // 2]["bvid"])
    seeds = list(dict.fromkeys(seeds))[:5]
    print(f"[chain] 数值种子 {len(seeds)}（短/中/长桶 sinc 中位 + NM-A 中位）", flush=True)

    def fetch_related(aid):
        nonlocal rel_left
        if rel_left <= 0 or not aid:
            return None
        rel_left -= 1
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/archive/related", {"aid": aid}, tries=2)
            return d if isinstance(d, list) else ((d or {}).get("list") or [])
        except Exception:
            return None

    chain_nodes = 0
    for sbv in seeds:
        # 种子需要 aid：数值宇宙没有 aid，fetch_view 拿（计入预算外——种子必需）
        try:
            sv = cli.fetch_view(sbv)
            aid = sv.get("aid")
        except Exception:
            continue
        items = fetch_related(aid) or []
        for it in items:
            st = it.get("stat") or {}
            view = st.get("view") or 0
            vr = max(1, view)
            lr, cr, fr = (st.get("like") or 0) / vr, (st.get("coin") or 0) / vr, (st.get("favorite") or 0) / vr
            before = len(univ)
            universe_add(univ, it.get("bvid"), view, it.get("duration") or 0, lr, cr, fr, "chain")
            chain_nodes += len(univ) - before
    print(f"[chain] related 余 {rel_left}，新节点 {chain_nodes}，宇宙 {len(univ)}", flush=True)

    # ---- C) 细胞候选（只用池内数值预筛，random(42) 盲序）----
    pool_only = {b: u for b, u in univ.items() if b not in excl and u["bvid"] not in excl}
    cands = {
        "A": [u for u in pool_only.values() if fired(u["lr"], u["cr"], u["fr"]) and u["dur"] > 0 and u["dur"] <= 21 and u["view"] < 100000],
        "B": [u for u in pool_only.values() if fired(u["lr"], u["cr"], u["fr"]) and 21 < u["dur"] <= 45 and u["view"] < 100000],
        "C": [u for u in pool_only.values() if fired(u["lr"], u["cr"], u["fr"]) and u["dur"] > 45 and u["view"] < 100000],
        "D": [u for u in pool_only.values() if (not fired(u["lr"], u["cr"], u["fr"])) and u["view"] >= 300000 and u["sinc"] is not None and u["sinc"] <= 0.11],
        "E": [u for u in pool_only.values() if (not fired(u["lr"], u["cr"], u["fr"])) and u["view"] >= 300000 and u["sinc"] is not None and 0.11 < u["sinc"] <= 0.20],
        "F": [u for u in pool_only.values() if nma(u["lr"], u["cr"], u["fr"]) and u["view"] < 100000],
    }
    used = set()
    for k in cands:
        lst = [u["bvid"] for u in cands[k] if u["bvid"] not in used]
        rng.shuffle(lst)
        cands[k] = lst
        used.update(lst)
    g_cands = [b for b, u in pool_only.items()
               if u["view"] < 100000 and not fired(u["lr"], u["cr"], u["fr"]) and not nma(u["lr"], u["cr"], u["fr"])]
    rng.shuffle(g_cands)
    print("[cands] 候选池: " + " ".join(f"{k}={len(v)}" for k, v in cands.items()) + f" G={len(g_cands)}", flush=True)

    # ---- D) 刷新并按新鲜数值落细胞 ----
    cells = []
    budget = FV_BUDGET
    picked = []

    def cell_of(view, dur, lr, cr, fr, sinc):
        f = fired(lr, cr, fr)
        if f and view < 100000 and dur > 0 and dur <= 21:
            return "A"
        if f and view < 100000 and 21 < dur <= 45:
            return "B"
        if f and view < 100000 and dur > 45:
            return "C"
        if (not f) and view >= 300000 and sinc is not None and sinc <= 0.11:
            return "D"
        if (not f) and view >= 300000 and sinc is not None and 0.11 < sinc <= 0.20:
            return "E"
        if (not f) and nma(lr, cr, fr) and view < 100000:
            return "F"
        if (not f) and view < 100000:
            return "G"
        return None

    def try_fill(cell, cands_list, quota):
        nonlocal budget
        got = [c for c in picked if c["cell"] == cell]
        for bvid in cands_list:
            if len(got) >= quota or budget <= 0:
                break
            if bvid in {c["bvid"] for c in picked}:
                continue
            try:
                v = cli.fetch_view(bvid)
            except Exception:
                continue
            budget -= 1
            st = v.get("stat") or {}
            view = st.get("view") or 0
            if view < 3000:
                continue
            vr = max(1, view)
            lr, cr, fr = (st.get("like") or 0) / vr, (st.get("coin") or 0) / vr, (st.get("favorite") or 0) / vr
            sinc = (cr / fr) if fr > 0 else None
            c = cell_of(view, v.get("duration") or 0, lr, cr, fr, sinc)
            if c != cell:
                continue
            pub = time.strftime("%Y-%m-%d", time.localtime(v.get("pubdate") or 0)) if v.get("pubdate") else "—"
            picked.append({"cell": cell, "bvid": bvid, "title": v.get("title") or "",
                           "owner": (v.get("owner") or {}).get("name") if isinstance(v.get("owner"), dict) else (v.get("owner") or "—"),
                           "tname": v.get("tname") or "", "view": view, "dur": v.get("duration") or 0,
                           "pub": pub, "pic": v.get("pic") or "",
                           "lr": round(lr, 4), "cr": round(cr, 4), "fr": round(fr, 4),
                           "sinc": round(sinc, 4) if sinc is not None else None,
                           "r4": fired(lr, cr, fr),
                           "r8": (st.get("like") or 0) / max(1, st.get("coin") or 1) > 50})
            got = [c for c in picked if c["cell"] == cell]
        print(f"[fill] {cell}: {len(got)}/{quota}（预算余 {budget}）", flush=True)

    for cell in ("A", "B", "C", "D", "F", "E"):
        try_fill(cell, cands[cell], QUOTA[cell])
    g_block = {c["bvid"] for c in picked}
    try_fill("G", [b for b in g_cands if b not in g_block], QUOTA["G"])

    counts = {k: sum(1 for c in picked if c["cell"] == k) for k in QUOTA}
    print("[cells] " + " ".join(f"{k}={counts[k]}" for k in QUOTA) + f" 共{len(picked)}", flush=True)

    out = {"meta": {"date": DATE, "protocol": "blind-numeric", "seed": SEED,
                    "universe": len(univ), "chain_nodes": chain_nodes, "budget_left": budget},
           "quota": QUOTA, "counts": counts, "cards": picked}
    json.dump(out, open(os.path.join(MINE, f"r4_blindhunt_{DATE}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # ---- 页面 ----
    build_page(picked, counts)


CELL_LBL = {"A": "触发·短 ≤21s", "B": "触发·中 22~45s", "C": "触发·长 >45s",
            "D": "高带低诚 sinc≤0.11", "E": "高带边界 0.11~0.20", "F": "低带边缘 NM-A", "G": "随机对照"}
GROUP_NOTE = {"A": "检验：短时长（≤21s）触发是否=软擦边（第一轮 10/10）",
              "B": "触发中等时长——第一轮的空档区", "C": "检验：长时长触发是否=无辜（第一轮 0/4 擦边）",
              "D": "检验：高带低诚意比（≤0.11）是否=擦边（第一轮 12/12）", "E": "诚意比边界带对照",
              "F": "赞率贴线未触发——第一轮漏网形状", "G": "盲对照基线"}


def card_html(c):
    bvid = c["bvid"]
    url = f"https://www.bilibili.com/video/{bvid}"
    lr, cr, fr = c["lr"], c["cr"], c["fr"]
    lp, cp, fp = lr > 0.20, cr < 0.02, fr > 0.10

    def chip(passed, label, val, delta):
        cls = "c1" if passed else "c0"
        return f'<span class="{cls}"><b>{label} {val}</b>｜{delta}</span>'

    ch1 = chip(lp, "赞", f"{lr:.1%}", (f"超线{lr - 0.2:.1%}" if lp else f"距线{0.2 - lr:.1%}"))
    ch2 = chip(cp, "币", f"{cr:.1%}", ("低于2%线" if cp else f"超线{cr - 0.02:.1%}"))
    ch3 = chip(fp, "藏", f"{fr:.1%}", (f"超线{fr - 0.1:.1%}" if fp else f"距线{0.1 - fr:.1%}"))
    sinc = "—" if c["sinc"] is None else f"{c['sinc']:.3f}"
    ch4 = f'<span class="c0"><b>sinc</b>｜{sinc}</span><span class="c0"><b>时长</b>｜{int(c["dur"] or 0)}s</span>'
    r8 = '<span class="c1"><b>R8</b>｜赞/币&gt;50</span>' if c["r8"] else ""
    verdict = '<span class="v1">R4 触发</span>' if c["r4"] else '<span class="v0">R4 未触发</span>'
    name = "j_" + bvid
    return f'''<div class="card" data-g="{c["cell"]}" id="c_{bvid}">
<a class="cov" href="{url}" target="_blank" rel="noreferrer"><img src="{H.escape(c["pic"] or "", True)}" referrerpolicy="no-referrer" loading="lazy" alt=""></a>
<div class="inf">
<div class="ti hid" id="ti_{bvid}"><a href="{url}" target="_blank" rel="noreferrer">{H.escape(c["title"])}</a><span class="up">UP：{H.escape(str(c["owner"]))}</span></div>
<div class="mt">{H.escape(c["tname"] or "—")} · 播放 {c["view"]:,} · {c["pub"]} · 细胞 {c["cell"]}（{CELL_LBL[c["cell"]]}）</div>
<div class="ch">{ch1}{ch2}{ch3}{ch4}{r8}</div>
<div class="jd">{verdict} 判定：
<label><input type="radio" name="{name}" value="软擦边">软擦边</label>
<label><input type="radio" name="{name}" value="无辜">无辜</label>
<label><input type="radio" name="{name}" value="存疑">存疑</label>
</div></div></div>'''


JS = """
var KEY=__KEY__, TOTAL=__TOTAL__;
var J={};try{J=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
function save(){localStorage.setItem(KEY,JSON.stringify(J));prog()}
function prog(){var n=Object.keys(J).length;document.getElementById('prog').textContent=n+' / '+TOTAL;
 var b=document.getElementById('bar');b.style.width=(100*n/TOTAL)+'%'}
function reveal(id){var t=document.getElementById('ti_'+id);if(t)t.classList.remove('hid')}
document.querySelectorAll('input[type=radio]').forEach(function(r){
 var id=r.name.slice(2);
 if(J[id]&&J[id].v===r.value){r.checked=true;reveal(id)}
 r.addEventListener('change',function(){J[id]={v:r.value,t:Date.now()};save();reveal(id)})});
function setF(f){document.querySelectorAll('.card').forEach(function(c){
 var id=c.id.slice(2);
 var show=f==='ALL'||c.dataset.g===f||(f==='TODO'&&!J[id]);
 c.style.display=show?'':'none'});
 document.querySelectorAll('.tab').forEach(function(t){t.classList.toggle('on',t.dataset.f===f)})}
function revealAll(){document.querySelectorAll('.card').forEach(function(c){reveal(c.id.slice(2))})}
function exportJ(){var out={date:'2026-09-05',page:'r4-blind-review',protocol:'blind-numeric',total:TOTAL,judgments:J};
 var b=new Blob([JSON.stringify(out,null,1)],{type:'application/json'});
 var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='r4_blind_review_judged_2026-09-05.json';a.click()}
function wipe(){if(confirm('清空本页全部判定？')){localStorage.removeItem(KEY);location.reload()}}
prog();
""".replace("__KEY__", json.dumps(KEY))


def build_page(cards, counts):
    order = sorted(cards, key=lambda c: ("ABCDEFG".index(c["cell"]), -c["lr"]))
    tabs = "".join(
        f'<button class="tab{" on" if k == "ALL" else ""}" data-f="{k}" onclick="setF(\'{k}\')">{lbl} {counts.get(k, 0) if k != "ALL" and k != "TODO" else ""}</button>'
        for k, lbl in [("ALL", "全部")] + [(k, f"{k} {CELL_LBL[k]}") for k in QUOTA] + [("TODO", "未判")])
    parts = [f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>R4 盲测第二轮 · 数值选样人工审核台</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#F7F2EB;color:#081F5C;
 font-family:system-ui,-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;font-size:13.5px}}
.top{{position:sticky;top:0;background:#F7F2EB;border-bottom:1px solid #D0E3FF;padding:14px 18px 10px;z-index:9}}
h1{{font-family:'KaiTi','STKaiti',serif;font-size:20px;margin:0 0 2px;font-weight:800}}
.lead{{font-size:12px;color:#7096D1;margin:0 0 8px;line-height:1.6}}
.barw{{height:4px;background:#D0E3FF;border-radius:2px;margin:6px 0 10px}}
#bar{{height:4px;background:#081F5C;border-radius:2px;width:0;transition:width .3s}}
.tab{{display:inline-block;border:1px dashed #7096D1;border-radius:999px;padding:3px 12px;margin:0 6px 6px 0;
 font-size:11px;color:#334EAC;cursor:pointer;background:none}}
.tab.on{{background:#081F5C;color:#F7F2EB;border-style:solid;border-color:#081F5C}}
.btn{{border:1px solid #334EAC;border-radius:6px;background:none;color:#081F5C;padding:4px 12px;
 font-size:12px;cursor:pointer;margin-right:8px}}
.wrap{{max-width:860px;margin:0 auto;padding:14px 16px 60px}}
.card{{display:flex;background:#fff;border:1px solid #D0E3FF;border-radius:8px;margin:10px 0;overflow:hidden}}
.cov{{flex:0 0 200px}}.cov img{{width:200px;height:125px;object-fit:cover;display:block}}
.inf{{flex:1;padding:9px 12px;min-width:0}}
.ti{{font-size:13.5px;font-weight:600;line-height:1.4;transition:filter .4s}}
.ti a{{color:#081F5C;text-decoration:none}}.ti a:hover{{text-decoration:underline dotted #7096D1}}
.ti .up{{font-size:11px;color:#7096D1;font-weight:400;margin-left:8px}}
.ti.hid{{filter:blur(7px);pointer-events:none;user-select:none}}
.mt{{font-size:11px;color:#7096D1;margin:3px 0 6px}}
.ch{{margin-bottom:6px}}
.c1,.c0{{display:inline-block;border-radius:4px;padding:2px 7px;font-size:11px;margin:0 6px 4px 0;font-variant-numeric:tabular-nums}}
.c1{{background:#081F5C;color:#F7F2EB}}
.c0{{background:#D0E3FF;color:#334EAC}}
.c1 b,.c0 b{{font-weight:700}}
.v1,.v0{{display:inline-block;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px}}
.v1{{background:#334EAC;color:#fff}}.v0{{background:none;color:#7096D1;border:1px dashed #7096D1}}
.jd{{font-size:12.5px}}.jd label{{margin-right:12px;cursor:pointer}}
.jd input{{accent-color:#081F5C;vertical-align:-2px;margin-right:3px}}
@media(max-width:640px){{.card{{flex-direction:column}}.cov{{flex:none}}.cov img{{width:100%;height:170px}}}}
</style></head><body>
<div class="top"><h1>R4 盲测第二轮 · 数值选样人工审核台</h1>
<p class="lead">协议：本页选样只用数值（率/时长/播放/诚意比），标题与UP名已模糊——<b>先看封面与视频内容判「软擦边 / 无辜 / 存疑」，判定后该卡标题自动揭示</b>。七个细胞检验第一轮三个假设。已判 <b id="prog">0 / {len(cards)}</b></p>
<div class="barw"><div id="bar"></div></div>
{tabs}
<button class="btn" onclick="exportJ()">导出判定JSON</button>
<button class="btn" onclick="revealAll()">揭示全部</button>
<button class="btn" onclick="wipe()">清空本地</button>
</div><div class="wrap">''']
    cur = None
    for c in order:
        if c["cell"] != cur:
            cur = c["cell"]
            parts.append(f'<p class="lead" style="margin:18px 0 0">细胞 {cur} · {CELL_LBL[cur]} —— {GROUP_NOTE[cur]}</p>')
        parts.append(card_html(c))
    js = JS.replace("__KEY__", json.dumps(KEY)).replace("__TOTAL__", str(len(cards)))
    parts.append('</div><script>' + js + '</script></body></html>')
    out = os.path.join(OUTD, "r4-blind-review.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    print(f"[done] {out}（{len(cards)} 卡）", flush=True)


if __name__ == "__main__":
    main()
