# -*- coding: utf-8 -*-
"""R4 擦边识别率 · 人工审核页生成器。

38 支审核对象（fetch_view 刷新封面+数据）→ docs/personal/r4-edge-review.html
  C组 15：R4 触发·重点审核（12 链上存疑 + 3 极端签名种子）
  A组 18：真·擦边搜索热门 · R4 漏报对照（确认内容属性）
  B组  4：R4 触发·疑似无辜抽查
  D组  1：边界贴线未触发
判定存 localStorage(key=r4_edge_review_20260905)，「导出判定」下载 JSON 回传合并。
缓存：data/fav_mine/r4_review_cards_20260905.json（删掉即重抓）。
"""
import json
import os
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
OUTD = os.path.join(ROOT, "docs", "personal")
DATE = "20260905"
KEY = f"r4_edge_review_{DATE}"

C_FIRE = ["BV1FhGR69EXK", "BV1fqtJ6dEu8", "BV1w88u6zEFy", "BV1tQ3d6NETw", "BV1Sqt369EAh",
          "BV16jt36TEyv", "BV1ya8s6pEyG", "BV12XhF6REVM", "BV1kXt36CEZ9", "BV1EAuM61Exi",
          "BV1P3tV6nE59", "BV1uLth6rErU"]
C_SEED = ["BV13sHVzFEby", "BV18H4MzsEFm", "BV1ZtTQ68EDk"]
B_LST = ["BV1qh8z6JEuz", "BV1nWb96tE47", "BV1Qm421G7kh", "BV1RCxJevEHe"]
D_LST = ["BV1wrcLzeEQw"]
GROUP_NOTE = {"C": "R4触发 · 重点审核：软擦边还是萌系/同人被冤枉？",
              "A": "真·擦边搜索热门 · R4漏报对照：确认内容属性（预期「软擦边」坐实漏报）",
              "B": "R4触发 · 疑似无辜抽查：预期「无辜」",
              "D": "边界贴线未触发：三条件都压线"}


def load_A():
    j = json.load(open(os.path.join(MINE, f"r4_edgehunt2_{DATE}.json"), encoding="utf-8"))
    return [(r["bvid"], r.get("kw") or "") for r in j["scored"] if r.get("src") == "search"]


def fmt_dur(s):
    s = int(s or 0)
    return f"{s // 60}:{s % 60:02d}"


def fetch_cards():
    cli = BiliClient(interval=0.5)
    tasks = ([("C", b, "链上命中") for b in C_FIRE] +
             [("C", b, "池内极端签名种子") for b in C_SEED] +
             [("B", b, "疑似无辜抽查") for b in B_LST] +
             [("D", b, "边界贴线未触发") for b in D_LST] +
             [("A", b, kw) for b, kw in load_A()])
    cards = []
    for i, (g, bvid, note) in enumerate(tasks):
        try:
            v = cli.fetch_view(bvid)
        except Exception as e:
            print(f"[{i + 1}/{len(tasks)}] {bvid} fetch fail: {str(e)[:40]}", flush=True)
            continue
        st = v.get("stat") or {}
        view = st.get("view") or 0
        vr = max(1, view)
        lr = (st.get("like") or 0) / vr
        cr = (st.get("coin") or 0) / vr
        fr = (st.get("favorite") or 0) / vr
        r4 = lr > 0.20 and cr < 0.02 and fr > 0.10
        pub = time.strftime("%Y-%m-%d", time.localtime(v.get("pubdate") or 0)) if v.get("pubdate") else "—"
        cards.append({"g": g, "note": note, "bvid": bvid, "title": v.get("title") or "",
                      "owner": (v.get("owner") or {}).get("name") if isinstance(v.get("owner"), dict) else (v.get("owner") or "—"),
                      "tname": v.get("tname") or "", "view": view, "dur": v.get("duration") or 0,
                      "pub": pub, "pic": v.get("pic") or "",
                      "lr": round(lr, 4), "cr": round(cr, 4), "fr": round(fr, 4),
                      "r4": r4, "r8": (st.get("like") or 0) / max(1, st.get("coin") or 1) > 50})
        if (i + 1) % 10 == 0:
            print(f"[{i + 1}/{len(tasks)}] 刷新完成", flush=True)
    return cards


def chip(passed, label, val, delta):
    cls = "c1" if passed else "c0"
    return f'<span class="{cls}"><b>{label} {val}</b>｜{delta}</span>'


def card_html(c):
    bvid = c["bvid"]
    url = f"https://www.bilibili.com/video/{bvid}"
    lr, cr, fr = c["lr"], c["cr"], c["fr"]
    lp, cp, fp = lr > 0.20, cr < 0.02, fr > 0.10
    ch1 = chip(lp, "赞", f"{lr:.1%}", (f"超线{lr - 0.2:.1%}" if lp else f"距线{0.2 - lr:.1%}"))
    ch2 = chip(cp, "币", f"{cr:.1%}", ("低于2%线" if cp else f"超线{cr - 0.02:.1%}"))
    ch3 = chip(fp, "藏", f"{fr:.1%}", (f"超线{fr - 0.1:.1%}" if fp else f"距线{0.1 - fr:.1%}"))
    r8 = '<span class="c1"><b>R8</b>｜赞/币&gt;50</span>' if c["r8"] else ""
    verdict = '<span class="v1">R4 触发</span>' if c["r4"] else '<span class="v0">R4 未触发</span>'
    name = "j_" + bvid
    return f'''<div class="card" data-g="{c["g"]}" id="c_{bvid}">
<a class="cov" href="{url}" target="_blank" rel="noreferrer"><img src="{H.escape(c["pic"] or "", True)}" referrerpolicy="no-referrer" loading="lazy" alt=""></a>
<div class="inf">
<div class="ti"><a href="{url}" target="_blank" rel="noreferrer">{H.escape(c["title"])}</a></div>
<div class="mt">{H.escape(str(c["owner"]))} · {H.escape(c["tname"] or "—")} · 播放 {c["view"]:,} · {fmt_dur(c["dur"])} · {c["pub"]} · {H.escape(c["note"])}</div>
<div class="ch">{ch1}{ch2}{ch3}{r8}</div>
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
document.querySelectorAll('input[type=radio]').forEach(function(r){
 var id=r.name.slice(2);
 if(J[id]&&J[id].v===r.value)r.checked=true;
 r.addEventListener('change',function(){J[id]={v:r.value,t:Date.now()};save()})});
function setF(f){document.querySelectorAll('.card').forEach(function(c){
 var show=f==='ALL'||c.dataset.g===f||(f==='TODO'&&!J[c.id.slice(2)]);
 c.style.display=show?'':'none'});
 document.querySelectorAll('.tab').forEach(function(t){t.classList.toggle('on',t.dataset.f===f)})}
function exportJ(){var out={date:'2026-09-05',page:'r4-edge-review',total:TOTAL,judgments:J};
 var b=new Blob([JSON.stringify(out,null,1)],{type:'application/json'});
 var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='r4_review_judged_2026-09-05.json';a.click()}
function wipe(){if(confirm('清空本页全部判定？')){localStorage.removeItem(KEY);location.reload()}}
prog();
""".replace("__KEY__", json.dumps(KEY)).replace("__TOTAL__", "38")


def build_html(cards):
    cards.sort(key=lambda c: ({"C": 0, "A": 1, "B": 2, "D": 3}[c["g"]], -c["lr"]))
    n = {"C": 0, "A": 0, "B": 0, "D": 0}
    for c in cards:
        n[c["g"]] += 1
    parts = [f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>R4 擦边识别率 · 人工审核台</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#F7F2EB;color:#081F5C;
 font-family:system-ui,-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;font-size:13.5px}}
.top{{position:sticky;top:0;background:#F7F2EB;border-bottom:1px solid #D0E3FF;padding:14px 18px 10px;z-index:9}}
h1{{font-family:'KaiTi','STKaiti',serif;font-size:20px;margin:0 0 2px;font-weight:800}}
.lead{{font-size:12px;color:#7096D1;margin:0 0 8px}}
.barw{{height:4px;background:#D0E3FF;border-radius:2px;margin:6px 0 10px}}
#bar{{height:4px;background:#081F5C;border-radius:2px;width:0;transition:width .3s}}
.tab{{display:inline-block;border:1px dashed #7096D1;border-radius:999px;padding:3px 12px;margin:0 6px 6px 0;
 font-size:11px;color:#334EAC;cursor:pointer;background:none}}
.tab.on{{background:#081F5C;color:#F7F2EB;border-style:solid;border-color:#081F5C}}
.btn{{border:1px solid #334EAC;border-radius:6px;background:none;color:#081F5C;padding:4px 12px;
 font-size:12px;cursor:pointer;margin-right:8px}}
.wrap{{max-width:860px;margin:0 auto;padding:14px 16px 60px}}
.grp{{font-size:14px;font-weight:700;margin:22px 0 4px;color:#334EAC;border-left:3px solid #081F5C;padding-left:8px}}
.gnote{{font-size:11.5px;color:#7096D1;margin:0 0 8px}}
.card{{display:flex;background:#fff;border:1px solid #D0E3FF;border-radius:8px;margin:10px 0;overflow:hidden}}
.cov{{flex:0 0 200px}}.cov img{{width:200px;height:125px;object-fit:cover;display:block}}
.inf{{flex:1;padding:9px 12px;min-width:0}}
.ti{{font-size:13.5px;font-weight:600;line-height:1.4}}
.ti a{{color:#081F5C;text-decoration:none}}.ti a:hover{{text-decoration:underline dotted #7096D1}}
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
<div class="top"><h1>R4 擦边识别率 · 人工审核台</h1>
<p class="lead">结论先行：R4 对真·擦边物种 18/18 全漏报；一条龙 187/578 触发的是「萌系视觉消费」（cos/MMD/萌图集）。请逐卡点开看内容，判「软擦边 / 无辜 / 存疑」——判定自动存本地，判完点「导出判定JSON」回传合并。已判 <b id="prog">0 / {len(cards)}</b></p>
<div class="barw"><div id="bar"></div></div>
<button class="tab on" data-f="ALL" onclick="setF('ALL')">全部 {len(cards)}</button>
<button class="tab" data-f="C" onclick="setF('C')">C 重点审核 {n["C"]}</button>
<button class="tab" data-f="A" onclick="setF('A')">A 漏报对照 {n["A"]}</button>
<button class="tab" data-f="B" onclick="setF('B')">B 无辜抽查 {n["B"]}</button>
<button class="tab" data-f="D" onclick="setF('D')">D 边界 {n["D"]}</button>
<button class="tab" data-f="TODO" onclick="setF('TODO')">未判</button>
<button class="btn" onclick="exportJ()">导出判定JSON</button>
<button class="btn" onclick="wipe()">清空本地</button>
</div><div class="wrap">''']
    cur = None
    for c in cards:
        if c["g"] != cur:
            cur = c["g"]
            parts.append(f'<div class="grp">{cur}组 · {n[cur]} 支</div><p class="gnote">{GROUP_NOTE[cur]}</p>')
        parts.append(card_html(c))
    parts.append('</div><script>' + JS + '</script></body></html>')
    out = os.path.join(OUTD, "r4-edge-review.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    print(f"[done] {out}（{len(cards)} 卡）", flush=True)


def main():
    cache = os.path.join(MINE, f"r4_review_cards_{DATE}.json")
    if os.path.exists(cache):
        cards = json.load(open(cache, encoding="utf-8"))
        print(f"[cache] 复用 {len(cards)} 张卡（删除缓存文件可重抓）", flush=True)
    else:
        cards = fetch_cards()
        json.dump(cards, open(cache, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[fetch] 落盘 {cache}", flush=True)
    build_html(cards)


if __name__ == "__main__":
    main()
