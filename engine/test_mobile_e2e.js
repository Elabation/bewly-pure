// 端到端验证：v5 真实样本 → 脚本劫持管道 → 过滤率与原因分布
const fs = require('fs');
const path = require('path');

// ---- stub 浏览器 ----
const hidden = [];
global.window = global;
global.document = {
  readyState: 'complete', addEventListener: () => {},
  documentElement: { appendChild() {} }, body: null,
  querySelector: () => null, querySelectorAll: () => [],
  getElementById: () => null,
  createElement: () => ({ style: { setProperty() {}, cssText: '' }, setAttribute() {}, appendChild() {}, classList: { add() {} } }),
};
global.localStorage = { getItem: () => null, setItem: () => {} };
global.MutationObserver = class { observe() {} };
global.Response = class {};
global.fetch = async () => { throw new Error('network off'); };
global.XMLHttpRequest = class { open() {} send() {} addEventListener() {} };

const src = fs.readFileSync(path.join(__dirname, '..', 'userscript', 'bilibili-clean-mobile.user.js'), 'utf8');
new Function(src)();
const CB = global.CleanBili;
const I = CB._internal;

// ---- 构造三股流的响应（v5 真实条目） ----
const payload = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'samples', 'ecosystem_v5_20260901_2050_fix.json'), 'utf8'));
const vs = payload.videos.filter(v => v.stat && (v.stat.view || 0) >= 1000);
const pick = (src, pred, n) => src.filter(pred).slice(0, n);
const related = pick(vs, v => v.source.startsWith('ranking') || v.source.startsWith('series'), 500)
  .map(v => ({ bvid: v.bvid, title: v.title, duration: v.duration, stat: v.stat, tname: v.tname, dimension: v.dimension || null, is_ogv: 0 }));
const regionArch = pick(vs, v => v.source.startsWith('newlist'), 400)
  .map(v => ({ bvid: v.bvid, title: v.title, duration: v.duration, stat: v.stat, tname: v.tname, dimension: v.dimension || null }));
const hotList = pick(vs, v => v.source.startsWith('series') && (v.stat.view || 0) > 1e6, 300)
  .map(v => ({ bvid: v.bvid, title: v.title, duration: v.duration, stat: v.stat, tname: v.tname }));

// ---- 跑管道 ----
const r1 = I.processRelated({ code: 0, data: related });
const r2 = I.processRegion({ code: 0, data: { archives: regionArch } });
const r3 = I.processList({ code: 0, data: { list: hotList } });
console.log('管道命中:', { related: r1, region: r2, list: r3 });
console.log('输入:', { related: related.length, region: regionArch.length, hot: hotList.length });
const hiddenArr = [];
for (const [bv, v] of (global.CleanBili && hiddenVerdictsOf())) hiddenArr.push(v);
function *hiddenVerdictsOf() { /* placeholder */ }
// hiddenVerdicts 是脚本内部 Map——通过重新判一遍统计
let hide = 0, keep = 0;
const reasons = {};
for (const item of [...related, ...regionArch, ...hotList]) {
  const v = CB.test(item.stat, item.title, item.tname, item.is_ogv);
  // CB.test 不含 duration 短视频与同步层 —— 用 reasons 近似统计
  if (v.hide) { hide++; }
  else keep++;
  for (const r of v.reasons) {
    const k = r.startsWith('看过不给') ? '看过不给' : r.startsWith('低播放') ? '低播放' : r.startsWith('低分') ? '低分' : r.startsWith('竖屏') ? '竖屏' : '乞讨标';
    reasons[k] = (reasons[k] || 0) + 1;
  }
}
console.log('本地判定（不含同步层签名/短视频）:', { hide, keep, hidePct: (hide / (hide + keep) * 100).toFixed(1) + '%' });
console.log('原因分布:', reasons);
console.log('同步计数器:', CB.counts);
