# -*- coding: utf-8 -*-
"""R4 盲测第三轮 —— 三分法验证：R4 × 时长 × 真人封面（双盲：选样数值+机器视觉，标题零介入）。

细胞（预测 → 盲判定回填检验）：
  T1 触发·短·真人   r4 & <10万 & dur≤21s & 真人脸≥1      配额12  【定向抓擦边候选：预期擦边率≥60%】
  T2 触发·短·非真人 r4 & <10万 & dur≤21s & 真人脸=0       配额6   【预期低擦边率】
  T3 触发·长·赦免   r4 & <10万 & dur>21s                  配额4   【预期零擦边（两轮16/16）】
  C1 真人·非R4     非r4 & <10万 & 真人脸≥1               配额6   【真人单独基线】
  H1 高带·低诚·真人 view≥30万 & sinc≤0.11 & 真人脸≥1       配额4   【高带+封面能否翻案】
  G  随机对照      非r4 & <10万 随机(seed=43)             配额6
产出：data/fav_mine/r4_blind3_20260905.json + docs/personal/r4-blind3-review.html + 根目录副本
"""
import json
import os
import sys
import tempfile
import time
import urllib.request

import cv2

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
KEY = f"r4_blind3_review_{DATE}"
TMPROOT = os.path.join(tempfile.gettempdir(), "r4coverlab")
CACHE = os.path.join(TMPROOT, "covers")
YUNET = os.path.join(TMPROOT, "models", "face_detection_yunet_2023mar.onnx")
QUOTA = {"T1": 12, "T2": 6, "T3": 4, "C1": 6, "H1": 4, "G": 6}
FV_BUDGET = 90
REL_BUDGET = 8
SEED = 43
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://www.bilibili.com/"}


def fired(lr, cr, fr):
    return lr > 0.20 and cr < 0.02 and fr > 0.10


def nma(lr, cr, fr):
    return cr < 0.02 and fr > 0.10 and 0.12 < lr <= 0.20


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
                vr = max(1, view)
                universe_add(univ, v.get("bvid"), view, v.get("duration") or 0,
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


def load_yunet():
    det = cv2.FaceDetectorYN.create(YUNET, "", (320, 320), 0.5, 0.3)
    return det


def cover_real(bvid, pic, det):
    """下载封面并检测真人脸 → (n_real, maxconf)；失败 (-1, 0)。"""
    dest = os.path.join(CACHE, bvid + ".jpg")
    try:
        if not (os.path.exists(dest) and os.path.getsize(dest) > 1000):
            url = pic if pic.startswith("http") else ("https:" + pic)
            req = urllib.request.Request(url, headers=UA)
            data = urllib.request.urlopen(req, timeout=15).read()
            if len(data) <= 1000:
                return -1, 0.0
            open(dest, "wb").write(data)
        img = cv2.imread(dest)
        if img is None:
            return -1, 0.0
        h, w = img.shape[:2]
        if max(h, w) > 1280:
            s = 1280 / max(h, w)
            img = cv2.resize(img, (int(w * s), int(h * s)))
            h, w = img.shape[:2]
        det.setInputSize((w, h))
        _, faces = det.detect(img)
        if faces is None:
            return 0, 0.0
        confs = [float(f[14]) for f in faces if float(f[14]) > 0.5]
        return len(confs), (max(confs) if confs else 0.0)
    except Exception:
        return -1, 0.0


def main():
    t0 = time.time()
    rng_seed = SEED
    import random
    rng = random.Random(rng_seed)
    cli = BiliClient(interval=0.5)
    if not os.path.exists(YUNET):
        print("[fatal] YuNet 模型缺失，先跑 diag_r4_coverlab.py", flush=True)
        return
    det = load_yunet()

    univ = {}
    scan_pool(univ)
    excl = set()
    for fn in ("r4_review_cards_20260905.json", "r4_blindhunt_20260905.json"):
        try:
            p = json.load(open(os.path.join(MINE, fn), encoding="utf-8"))
            items = p if isinstance(p, list) else p.get("cards") or []
            excl |= {c["bvid"] for c in items}
        except Exception:
            pass
    print(f"[universe] 池 {len(univ)} | 排除已审 {len(excl)}", flush=True)

    # ---- 新鲜挖矿：popular 6页 + 一条龙4种子（数值选点）----
    for pn in range(1, 7):
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/popular", {"ps": 20, "pn": pn}, tries=2)
            for it in (d or {}).get("list") or []:
                st = it.get("stat") or {}
                view = st.get("view") or 0
                vr = max(1, view)
                universe_add(univ, it.get("bvid"), view, it.get("duration") or 0,
                             (st.get("like") or 0) / vr, (st.get("coin") or 0) / vr, (st.get("favorite") or 0) / vr, "popular")
        except Exception:
            pass
    fires_u = sorted([u for u in univ.values() if fired(u["lr"], u["cr"], u["fr"]) and u["dur"] > 0
                      and u["bvid"] not in excl], key=lambda x: x["dur"])
    seeds = []
    for lo, hi in ((0, 21), (22, 45), (46, 10000)):
        lst = sorted([u for u in fires_u if lo <= u["dur"] <= hi], key=lambda x: (x["sinc"] if x["sinc"] is not None else 9))
        if lst:
            seeds.append(lst[len(lst) // 2]["bvid"])
    nmas = sorted([u for u in univ.values() if nma(u["lr"], u["cr"], u["fr"]) and u["bvid"] not in excl], key=lambda x: x["lr"])
    if nmas:
        seeds.append(nmas[len(nmas) // 2]["bvid"])
    rel_left = REL_BUDGET
    chain_new = 0
    for sbv in list(dict.fromkeys(seeds))[:4]:
        try:
            aid = cli.fetch_view(sbv).get("aid")
        except Exception:
            continue
        if rel_left <= 0 or not aid:
            break
        rel_left -= 1
        try:
            d = cli.get_json("https://api.bilibili.com/x/web-interface/archive/related", {"aid": aid}, tries=2)
            items = d if isinstance(d, list) else ((d or {}).get("list") or [])
        except Exception:
            continue
        for it in items:
            st = it.get("stat") or {}
            view = st.get("view") or 0
            vr = max(1, view)
            before = len(univ)
            universe_add(univ, it.get("bvid"), view, it.get("duration") or 0,
                         (st.get("like") or 0) / vr, (st.get("coin") or 0) / vr, (st.get("favorite") or 0) / vr, "chain")
            chain_new += len(univ) - before
    print(f"[mine] popular6+chains 新节点 {chain_new}，宇宙 {len(univ)}", flush=True)

    # ---- 候选预筛（池内数值）+ 盲序 ----
    pool_only = {b: u for b, u in univ.items() if b not in excl}
    pre = {
        "T1": [u for u in pool_only.values() if fired(u["lr"], u["cr"], u["fr"]) and u["view"] < 100000 and 0 < u["dur"] <= 21],
        "T2": [u for u in pool_only.values() if fired(u["lr"], u["cr"], u["fr"]) and u["view"] < 100000 and 0 < u["dur"] <= 21],
        "T3": [u for u in pool_only.values() if fired(u["lr"], u["cr"], u["fr"]) and u["view"] < 100000 and u["dur"] > 21],
        "C1": [u for u in pool_only.values() if not fired(u["lr"], u["cr"], u["fr"]) and u["view"] < 100000],
        "H1": [u for u in pool_only.values() if not fired(u["lr"], u["cr"], u["fr"]) and u["view"] >= 300000
               and u["sinc"] is not None and u["sinc"] <= 0.11],
        "G": [u for u in pool_only.values() if not fired(u["lr"], u["cr"], u["fr"]) and u["view"] < 100000],
    }
    for k in pre:
        lst = [u["bvid"] for u in pre[k]]
        rng.shuffle(lst)
        pre[k] = lst
    print("[cands] " + " ".join(f"{k}={len(v)}" for k, v in pre.items()), flush=True)

    picked = []
    budget = FV_BUDGET

    def fill(cell, cands_list, quota):
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
            dur = v.get("duration") or 0
            n_real, conf = cover_real(bvid, v.get("pic") or "", det)
            f = fired(lr, cr, fr)
            ok = False
            if cell == "T1":
                ok = f and view < 100000 and 0 < dur <= 21 and n_real >= 1
            elif cell == "T2":
                ok = f and view < 100000 and 0 < dur <= 21 and n_real == 0
            elif cell == "T3":
                ok = f and view < 100000 and dur > 21
            elif cell == "C1":
                ok = (not f) and view < 100000 and n_real >= 1
            elif cell == "H1":
                ok = (not f) and view >= 300000 and fr > 0 and (cr / fr) <= 0.11 and n_real >= 1
            elif cell == "G":
                ok = (not f) and view < 100000
            if not ok:
                continue
            pub = time.strftime("%Y-%m-%d", time.localtime(v.get("pubdate") or 0)) if v.get("pubdate") else "—"
            picked.append({"cell": cell, "bvid": bvid, "title": v.get("title") or "",
                           "owner": (v.get("owner") or {}).get("name") if isinstance(v.get("owner"), dict) else (v.get("owner") or "—"),
                           "tname": v.get("tname") or "", "view": view, "dur": dur, "pub": pub,
                           "pic": v.get("pic") or "",
                           "lr": round(lr, 4), "cr": round(cr, 4), "fr": round(fr, 4),
                           "sinc": round(cr / fr, 4) if fr > 0 else None,
                           "n_real": n_real, "conf": round(conf, 3),
                           "r4": f, "r8": (st.get("like") or 0) / max(1, st.get("coin") or 1) > 50})
            got = [c for c in picked if c["cell"] == cell]
        print(f"[fill] {cell}: {len(got)}/{quota}（预算余 {budget}）", flush=True)

    for cell in ("T1", "T2", "C1", "T3", "H1"):
        fill(cell, pre[cell], QUOTA[cell])
    g_block = {c["bvid"] for c in picked}
    fill("G", [b for b in pre["G"] if b not in g_block], QUOTA["G"])

    counts = {k: sum(1 for c in picked if c["cell"] == k) for k in QUOTA}
    print("[cells] " + " ".join(f"{k}={counts[k]}" for k in QUOTA) + f" 共{len(picked)}", flush=True)

    json.dump({"meta": {"date": DATE, "protocol": "blind3-ternary", "seed": rng_seed,
                        "universe": len(univ), "budget_left": budget},
               "quota": QUOTA, "counts": counts, "cards": picked},
              open(os.path.join(MINE, f"r4_blind3_{DATE}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    build_page(picked, counts)
    print(f"[done] {time.time() - t0:.0f}s", flush=True)


CELL_LBL = {"T1": "触发·短·真人", "T2": "触发·短·非真人", "T3": "触发·长·赦免",
            "C1": "真人·非R4基线", "H1": "高带·低诚·真人", "G": "随机对照"}
CELL_PRED = {"T1": "定向抓擦边候选：若擦边率≥60%，方法成立", "T2": "预期低擦边率（对照）",
             "T3": "赦免条款：预期零擦边（两轮 16/16）", "C1": "真人封面单独用应≈无辜（防裸判）",
             "H1": "高带+封面能否翻案（第一轮已判死，复核）", "G": "盲对照基线"}


def card_html(c):
    bvid = c["bvid"]
    url = f"https://www.bilibili.com/video/{bvid}"
    lr, cr, fr = c["lr"], c["cr"], c["fr"]
    lp, cp, fp = lr > 0.20, cr < 0.02, fr > 0.10

    def chip(passed, label, val, delta):
        cls = "c1" if passed else "c0"
        return f'<span class="{cls}"><b>{label} {val}</b>｜{delta}</span>'

    sinc = "—" if c["sinc"] is None else f"{c['sinc']:.3f}"
    face = "有" if c["n_real"] >= 1 else ("无" if c["n_real"] == 0 else "?")
    ch1 = chip(lp, "赞", f"{lr:.1%}", (f"超线{lr - 0.2:.1%}" if lp else f"距线{0.2 - lr:.1%}"))
    ch2 = chip(cp, "币", f"{cr:.1%}", ("低于2%线" if cp else f"超线{cr - 0.02:.1%}"))
    ch3 = chip(fp, "藏", f"{fr:.1%}", (f"超线{fr - 0.1:.1%}" if fp else f"距线{0.1 - fr:.1%}"))
    ch4 = (f'<span class="c0"><b>sinc</b>｜{sinc}</span><span class="c0"><b>时长</b>｜{int(c["dur"] or 0)}s</span>'
           f'<span class="c1"><b>真脸</b>｜{face}({c["conf"]:.2f})</span>')
    verdict = '<span class="v1">R4 触发</span>' if c["r4"] else '<span class="v0">R4 未触发</span>'
    name = "j_" + bvid
    return f'''<div class="card" data-g="{c["cell"]}" id="c_{bvid}">
<a class="cov" href="{url}" target="_blank" rel="noreferrer"><img src="{c["pic"]}" referrerpolicy="no-referrer" loading="lazy" alt=""></a>
<div class="inf">
<div class="ti hid" id="ti_{bvid}"><a href="{url}" target="_blank" rel="noreferrer">{c["title"]}</a><span class="up">UP：{c["owner"]}</span></div>
<div class="mt">{c["tname"] or "—"} · 播放 {c["view"]:,} · {c["pub"]} · 细胞 {c["cell"]}（{CELL_LBL[c["cell"]]}）</div>
<div class="ch">{ch1}{ch2}{ch3}{ch4}</div>
<div class="jd">{verdict} 判定：
<label><input type="radio" name="{name}" value="软擦边">软擦边</label>
<label><input type="radio" name="{name}" value="无辜">无辜</label>
<label><input type="radio" name="{name}" value="存疑">存疑</label>
</div></div></div>'''


JS_TMPL = """
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
function exportJ(){var out={date:'2026-09-05',page:'r4-blind3-review',protocol:'blind3-ternary',total:TOTAL,judgments:J};
 var b=new Blob([JSON.stringify(out,null,1)],{type:'application/json'});
 var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='r4_blind3_review_judged_2026-09-05.json';a.click()}
function wipe(){if(confirm('清空本页全部判定？')){localStorage.removeItem(KEY);location.reload()}}
prog();
"""


def build_page(cards, counts):
    order = sorted(cards, key=lambda c: ("T1T2T3C1H1G".index(c["cell"]), -c["lr"]))
    tabs = "".join(
        f'<button class="tab{" on" if k == "ALL" else ""}" data-f="{k}" onclick="setF(\'{k}\')">{lbl} {counts.get(k, 0) if k not in ("ALL", "TODO") else ""}</button>'
        for k, lbl in [("ALL", "全部")] + [(k, f"{k} {CELL_LBL[k]}") for k in QUOTA] + [("TODO", "未判")])
    parts = [f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>R4 盲测第三轮 · 三分法验证台</title>
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
<div class="top"><h1>R4 盲测第三轮 · 三分法验证台</h1>
<p class="lead">双盲协议：选样=数值+机器视觉（YuNet 真人脸），标题 UP 名模糊，<b>判定后揭示</b>。本轮验证「定向抓擦边」：T1（触发·短·真人）若擦边率≥60% 则方法成立。已判 <b id="prog">0 / {len(cards)}</b></p>
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
            parts.append(f'<p class="lead" style="margin:18px 0 0">细胞 {cur} · {CELL_LBL[cur]} —— {CELL_PRED[cur]}</p>')
        parts.append(card_html(c))
    js = JS_TMPL.replace("__KEY__", json.dumps(KEY)).replace("__TOTAL__", str(len(cards)))
    parts.append('</div><script>' + js + '</script></body></html>')
    out = os.path.join(OUTD, "r4-blind3-review.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    print(f"[done] {out}（{len(cards)} 卡）", flush=True)


if __name__ == "__main__":
    main()
