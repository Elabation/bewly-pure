// ==UserScript==
// @name         洁净B站 Clean Bilibili · Mobile
// @namespace    dsh-bilibili-clean
// @version      0.1.0
// @description  手机版（m.bilibili.com）过滤：首页热榜 SSR 同步判定 + 频道流 region/feed/rcmd + 视频页相关流 archive/related。CBI 感谢指数（R2）+ F7 加权感谢率（R3）+ 硬偏好（R1）+ 标题签名（R7）+ 乞讨打标（R8）+ 官方内容豁免（R4）。拒绝 log 分母（R5）、拒绝文体歧视（R6）。判定核心与 config/clean.config.json / PC 版逐字段一致。
// @author       CleanBili
// @match        https://m.bilibili.com/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

/* 洁净B站 Mobile v0.1 —— 判定顺序（报告 §13，与 PC 版一致）：
 *   同步层（响应即删/渲染前删）：直播 R1 / 短视频 R1 / 命中标题签名 R7
 *   异步层：
 *     1. 竖屏           R1  hide（dimension 缺失时走 view API 补全）
 *     2. 播放 < 1000    R1  hide
 *     3. 官方区豁免      R4  tname 命中白名单 或 is_ogv=1 → 跳过 CBI
 *     4. CBI 判定       R2  播放 ≥ 5万 且 CBI < 0.5 → junk，hide（看过不给）
 *     5. 全局 tier 兜底      播放 3千~5万段用 v1 全局阈值
 *     6. 乞讨打标        R8  badge 标记，不惩罚
 *
 * 移动版三条流（2026-09-01 探测确认，engine/probe_mobile*.py）：
 *   A. 首页 = 热榜 SSR：window.__INITIAL_STATE__.home.hotList（stat 全字段，100 条）
 *   B. 频道流 = GET /x/web-interface/region/feed/rcmd（data.archives[]，参数页面自带）
 *   C. 视频页相关流 = GET /x/web-interface/archive/related（data[]，stat+dimension 全字段）
 *   热榜/相关流 stat 完整可现场判定；频道流 archives 同构，缺 dimension 时 enrich 补。
 */
(function () {
  'use strict';

  // ============ CONFIG：手动同步自 config/clean.config.json（v2，与 PC 版一致） ============
  const CONFIG = {
    scoring: {
      weights: { favorite: 3.0, coin: 2.0, like: 0.3 },   // R3
      denominator_mode: 'view',                            // R5：锁定
      min_view_threshold: 3000,
      tiers: { high: 0.107, normal: 0.064, low: 0.042 },
    },
    cbi: {                                                  // R2
      enabled: true,
      min_view: 50000,
      threshold: 0.5,
      // 滑窗分位回归 P50 基线（n=6734，2026-09-01 拟合，data/analysis/cbi_baseline.json）
      curve: [4.5,0.2065,4.6,0.1745,4.7,0.1376,4.8,0.1247,4.9,0.1154,5.0,0.1057,5.1,0.0919,5.2,0.083,5.3,0.0742,5.4,0.0687,5.5,0.0605,5.6,0.0577,5.7,0.0557,5.8,0.058,5.9,0.0616,6.0,0.0664,6.1,0.0706,6.2,0.0779,6.3,0.082,6.4,0.0839,6.5,0.0848,6.6,0.0861,6.7,0.0861,6.8,0.0861,6.9,0.0852,7.0,0.0849,7.1,0.0854,7.2,0.0863],
    },
    filters: {
      short_video_max_duration_sec: 75,                    // R1
      portrait: { enabled: true, wh_ratio_min: 0.9 },      // R1
      live: true,                                          // R1
      min_views: 1000,                                     // R1
      block_keywords: [                                    // R7（§14 p<0.01）
        '第[0-9一二三四五六七八九十百]+[集话]',
        '挑战[^，。！？\\s]{1,12}(？|\\?|成功的可能性|能成吗)',
      ],
      zone_whitelist: ['电影', '电视剧', '纪录片'],          // R4（§7 指纹；另含 is_ogv 豁免）
      beggar_patterns: ['投币.{0,6}更新', '三连.{0,6}更新', '点赞过.{0,6}更新'],  // R8
      hide_tiers: ['junk'],
      hide_unproven: false,
    },
    enrich: { enabled: true, concurrency: 3, cache_minutes: 60 },
    ui: { show_counter: true, show_badge: true },
  };
  // =====================================================================

  const RE_REGION = /region\/feed\/rcmd/;
  const RE_RELATED = /archive\/related/;
  const RE_HOTPAGE = /ranking\/v2|x\/web-interface\/popular/;
  const counts = { 短视频: 0, 竖屏: 0, 直播: 0, 看过不给: 0, 低分: 0, 低播放: 0, 签名: 0, 乞讨标: 0 };
  const hiddenVerdicts = new Map();
  const enrichQueue = [];
  let enrichActive = 0;

  const log = (...a) => console.log('%c[CleanBili·M]', 'color:#2196f3;font-weight:bold', ...a);

  // ---------- 评分核心（与 PC 版/engine/scoring.py 逐字段一致） ----------
  function f7Of(stat) {
    const w = CONFIG.scoring.weights;
    const view = stat.view || 0;
    const raw = (stat.favorite || 0) * w.favorite + (stat.coin || 0) * w.coin + (stat.like || 0) * w.like;
    return { f7: view > 0 ? raw / view : 0, view, raw };
  }
  function baselineCBI(logv) {
    const c = CONFIG.cbi.curve;
    if (logv <= c[0]) return c[1];
    if (logv >= c[c.length - 2]) return c[c.length - 1];
    for (let i = 0; i < c.length - 2; i += 2) {
      if (logv >= c[i] && logv <= c[i + 2]) {
        const t = (logv - c[i]) / (c[i + 2] - c[i]);
        return c[i + 1] + t * (c[i + 3] - c[i + 1]);
      }
    }
    return c[c.length - 1];
  }
  function tierOf(ratio, view) {
    const sc = CONFIG.scoring;
    if (view < sc.min_view_threshold) return 'unproven';
    const t = sc.tiers;
    return ratio >= t.high ? 'high' : ratio >= t.normal ? 'normal' : ratio >= t.low ? 'low' : 'junk';
  }
  function effWH(dim) {
    let w = dim.width || 0, h = dim.height || 0;
    if (dim.rotate === 90 || dim.rotate === 270) [w, h] = [h, w];
    return [w, h];
  }
  function matchesAny(title, patterns) {
    for (const p of patterns) {
      try { if (new RegExp(p).test(title)) return true; } catch (e) { if (title.includes(p)) return true; }
    }
    return false;
  }

  // ---------- 同步层判定 ----------
  function syncReasons(item) {
    const r = [];
    const f = CONFIG.filters;
    if (item.goto && item.goto !== 'av') {
      if (item.goto === 'live' && f.live) r.push('直播');
      else if (item.goto) r.push('其他');
      return r;
    }
    const dur = item.duration || 0;
    if (dur && dur <= f.short_video_max_duration_sec) r.push(`短视频(${dur}s)`);
    const title = item.title || '';
    if (f.block_keywords.length && matchesAny(title, f.block_keywords)) r.push('签名');
    return r;
  }

  // ---------- 异步层判定（输入：view 形态 {stat, dimension, title, tname, is_ogv?}） ----------
  function asyncVerdict(data) {
    const f = CONFIG.filters;
    const reasons = [];
    const stat = data.stat || {};
    const view = stat.view || 0;
    const { f7 } = f7Of(stat);
    let tier = tierOf(f7, view);
    let cbi = null;
    let beggar = false;

    if (f.portrait.enabled && data.dimension) {
      const [w, h] = effWH(data.dimension);
      if (w && h && w / h < f.portrait.wh_ratio_min) reasons.push('竖屏');
    }
    if (f.min_views && view < f.min_views) reasons.push(`低播放(${view})`);

    const tname = data.tname || '';
    const whitelisted = f.zone_whitelist.some((z) => tname.includes(z)) || data.is_ogv === 1;

    if (CONFIG.cbi.enabled && view >= CONFIG.cbi.min_view && !whitelisted) {
      cbi = f7 / baselineCBI(Math.log10(view));
      if (cbi < CONFIG.cbi.threshold) {
        tier = 'junk';
        reasons.push(`看过不给(CBI ${cbi.toFixed(2)})`);
      }
    }
    const hideTiers = [...f.hide_tiers, ...(f.hide_unproven ? ['unproven'] : [])];
    if (CONFIG.cbi.enabled && view >= CONFIG.cbi.min_view) {
      if (!(cbi !== null && cbi >= CONFIG.cbi.threshold) && !whitelisted && hideTiers.includes(tier) && !reasons.some((x) => x.startsWith('看过不给'))) {
        reasons.push(`低分(${tier})`);
      }
    } else if (!whitelisted && hideTiers.includes(tier) && !reasons.some((x) => x.startsWith('低播放'))) {
      reasons.push(`低分(${tier})`);
    }
    const title = data.title || '';
    if (f.beggar_patterns.length && matchesAny(title, f.beggar_patterns)) { beggar = true; reasons.push('乞讨标'); }

    return { hide: reasons.some((x) => !x.startsWith('乞讨标')), tier, f7, cbi, beggar, reasons, view, tname };
  }

  // ---------- 标准化：把各流 item 统一成 view 形态 ----------
  function toViewLike(item) {
    return {
      stat: item.stat || {},
      dimension: item.dimension || null,
      title: item.title || '',
      tname: item.tname || (item.type_name || ''),
      is_ogv: item.is_ogv,
      duration: item.duration || 0,
      bvid: item.bvid,
    };
  }

  // ---------- 异步 enrich（view API：补 dimension/tname/权威 stat） ----------
  function enrich(bvid) {
    return new Promise((resolve) => {
      const ck = 'cleanbili_m_' + bvid;
      try {
        const c = JSON.parse(localStorage.getItem(ck) || 'null');
        if (c && Date.now() - c.t < CONFIG.enrich.cache_minutes * 60000) return resolve(c.verdict);
      } catch (e) { /* ignore */ }
      enrichQueue.push({ bvid, ck, resolve });
      pump();
    });
  }
  function pump() {
    while (enrichActive < CONFIG.enrich.concurrency && enrichQueue.length) {
      const { bvid, ck, resolve } = enrichQueue.shift();
      enrichActive++;
      fetch(`https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`, { credentials: 'include' })
        .then((r) => r.json())
        .then((j) => {
          const verdict = j && j.code === 0 ? asyncVerdict(j.data) : nullVerdict();
          try { localStorage.setItem(ck, JSON.stringify({ t: Date.now(), verdict })); } catch (e) { /* ignore */ }
          resolve(verdict);
        })
        .catch(() => resolve(nullVerdict()))
        .finally(() => { enrichActive--; pump(); });
    }
  }
  const nullVerdict = () => ({ hide: false, tier: 'unknown', f7: 0, cbi: null, beggar: false, reasons: [], view: 0, tname: '' });

  // ---------- 判定入口：先本地同步判，字段不全再 enrich 补 ----------
  function judge(item, source) {
    const v = toViewLike(item);
    const bv = v.bvid;
    if (!bv || hiddenVerdicts.has(bv)) return;
    const local = asyncVerdict(v);
    if (local.hide) { applyVerdict(bv, local, source); return; }
    if (!CONFIG.enrich.enabled) { if (local.beggar) applyVerdict(bv, local, source); return; }
    // dimension 缺失（竖屏未判）或 stat 缺失 → enrich 权威复判
    if (!v.dimension || !statFull(v.stat)) {
      enrich(bv).then((verdict) => { if (verdict) applyVerdict(bv, verdict, source); });
    } else if (local.beggar) {
      applyVerdict(bv, local, source);
    }
  }
  function statFull(st) {
    return st && st.view != null && st.like != null && st.coin != null && st.favorite != null;
  }

  // ---------- 各流响应处理 ----------
  // B. 频道流 region/feed/rcmd：{data:{archives:[...]}}
  function processRegion(json) {
    const arch = json && json.data && json.data.archives;
    if (!Array.isArray(arch)) return false;
    const kept = [];
    for (const item of arch) {
      const reasons = syncReasons(item);
      if (reasons.length) {
        for (const r of reasons) bump(r.includes('短视频') ? '短视频' : r);
        log('sync-filtered', (item.title || '').slice(0, 22), reasons.join(','));
        continue;
      }
      kept.push(item);
    }
    json.data.archives = kept;
    kept.forEach((it) => judge(it, 'region'));
    updateCounter();
    return true;
  }
  // C. 视频页相关流 archive/related：data 为数组
  function processRelated(json) {
    const list = json && json.data;
    if (!Array.isArray(list)) return false;
    const kept = [];
    for (const item of list) {
      const reasons = syncReasons(item);
      if (reasons.length) {
        for (const r of reasons) bump(r.includes('短视频') ? '短视频' : r);
        log('sync-filtered', (item.title || '').slice(0, 22), reasons.join(','));
        continue;
      }
      kept.push(item);
    }
    json.data = kept;
    kept.forEach((it) => judge(it, 'related'));
    updateCounter();
    return true;
  }
  // 兜底：ranking/v2 / popular（list 形态）
  function processList(json) {
    const list = json && json.data && (json.data.list || json.data.item);
    if (!Array.isArray(list)) return false;
    const kept = [];
    for (const item of list) {
      const reasons = syncReasons(item);
      if (reasons.length) {
        for (const r of reasons) bump(r.includes('短视频') ? '短视频' : r);
        continue;
      }
      kept.push(item);
    }
    if (json.data.list) json.data.list = kept; else json.data.item = kept;
    kept.forEach((it) => judge(it, 'list'));
    updateCounter();
    return true;
  }

  function bump(key) { counts[key] = (counts[key] || 0) + 1; }

  // ---------- A. 首页热榜 SSR 处理 ----------
  function handleSSRHot() {
    try {
      const st = window.__INITIAL_STATE__;
      const hot = st && st.home && st.home.hotList;
      if (!hot) return;
      const items = [...(hot.result || []), ...(hot.extra && hot.extra.list || [])];
      let n = 0;
      for (const item of items) {
        if (!item || !item.bvid) continue;
        n++;
        const reasons = syncReasons(item);
        if (reasons.length) {
          for (const r of reasons) bump(r.includes('短视频') ? '短视频' : r);
          hiddenVerdicts.set(item.bvid, { hide: true, tier: 'junk', f7: 0, cbi: null, beggar: false, reasons, view: (item.stat || {}).view || 0, tname: item.tname || '' });
        } else {
          judge(item, 'hot-ssr');
        }
      }
      log(`SSR hot list: ${n} 条入队`);
      updateCounter();
    } catch (e) { log('SSR parse fail', e); }
  }

  // ---------- DOM 层 ----------
  function findCard(bvid) {
    const a = document.querySelector(`a[href*="/video/${bvid}"], a[href*="bvid=${bvid}"]`);
    if (!a) return null;
    return a.closest('.v-card, .video-card, .card-box, .bili-video-card') || a.parentElement;
  }
  function applyVerdict(bvid, verdict, source) {
    hiddenVerdicts.set(bvid, verdict);
    for (const r of verdict.reasons) {
      if (r.startsWith('乞讨标')) { counts['乞讨标'] = (counts['乞讨标'] || 0) + 1; break; }
      const key = r.startsWith('短视频') ? '短视频' : r.startsWith('看过不给') ? '看过不给'
        : r.startsWith('低播放') ? '低播放' : r.startsWith('低分') ? '低分' : r;
      if (!r.startsWith('乞讨标')) counts[key] = (counts[key] || 0) + 1;
    }
    const card = findCard(bvid);
    if (verdict.hide && card) {
      card.style.setProperty('display', 'none', 'important');
      card.dataset.cleanbili = 'hidden';
      log('hide', source, (verdict.reasons || []).join(','), 'view=' + verdict.view);
    }
    if (CONFIG.ui.show_badge && card && !card.querySelector('.cleanbili-badge')) {
      const badge = document.createElement('div');
      badge.className = 'cleanbili-badge';
      const main = verdict.cbi !== null ? `CBI ${verdict.cbi.toFixed(2)}` : `F7 ${verdict.f7.toFixed(3)}`;
      badge.textContent = main + (verdict.beggar ? ' · 乞' : '') + (verdict.tname ? ' · ' + verdict.tname : '');
      const color = { high: '#1b9e77', normal: '#666', low: '#d95f02', junk: '#e41a1c', unproven: '#999', unknown: '#999' }[verdict.tier] || '#999';
      badge.style.cssText = `position:absolute;top:4px;right:4px;z-index:9;background:#000a;color:#fff;` +
        `font-size:10px;line-height:1;padding:2px 5px;border-radius:3px;border:1px solid ${color};pointer-events:none;`;
      card.style.position = card.style.position || 'relative';
      card.appendChild(badge);
    }
    updateCounter();
  }
  function updateCounter() {
    if (!CONFIG.ui.show_counter) return;
    let chip = document.getElementById('cleanbili-counter');
    if (!chip) {
      chip = document.createElement('div');
      chip.id = 'cleanbili-counter';
      chip.style.cssText = 'position:fixed;left:6px;bottom:70px;z-index:99999;background:#1f2937cc;color:#e5e7eb;' +
        'font:10px/1.6 system-ui;padding:4px 8px;border-radius:6px;pointer-events:none;white-space:pre-line;max-width:46vw;';
      (document.body || document.documentElement).appendChild(chip);
    }
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    if (!total) { chip.style.display = 'none'; return; }
    chip.style.display = 'block';
    chip.textContent = '洁净B站 已过滤 ' + total + '\n' + Object.entries(counts)
      .filter(([, n]) => n > 0).map(([k, n]) => `${k} ${n}`).join(' · ');
  }

  // ---------- fetch 劫持 ----------
  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    const res = await origFetch.apply(this, args);
    try {
      const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '';
      if (!res.ok) return res;
      if (RE_REGION.test(url)) {
        const json = JSON.parse(await res.clone().text());
        if (processRegion(json)) return respond(json, res);
      } else if (RE_RELATED.test(url)) {
        const json = JSON.parse(await res.clone().text());
        if (processRelated(json)) return respond(json, res);
      } else if (RE_HOTPAGE.test(url)) {
        const json = JSON.parse(await res.clone().text());
        if (processList(json)) return respond(json, res);
      }
    } catch (e) { console.warn('[CleanBili·M] hook error', e); }
    return res;
  };
  function respond(json, res) {
    return new Response(JSON.stringify(json), {
      status: res.status, statusText: res.statusText, headers: res.headers,
    });
  }

  // ---------- XHR 劫持（部分移动端页面走 axios/XHR） ----------
  const XO = XMLHttpRequest.prototype.open;
  const XS = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this.__cbUrl = typeof url === 'string' ? url : (url && url.url) || '';
    return XO.call(this, method, url, ...rest);
  };
  XMLHttpRequest.prototype.send = function (...args) {
    if (this.__cbUrl && (RE_REGION.test(this.__cbUrl) || RE_RELATED.test(this.__cbUrl) || RE_HOTPAGE.test(this.__cbUrl))) {
      this.addEventListener('readystatechange', () => {
        try {
          if (this.readyState !== 4 || this.status !== 200 || this.__cbDone) return;
          this.__cbDone = true;
          const json = JSON.parse(this.responseText);
          const changed = RE_REGION.test(this.__cbUrl) ? processRegion(json)
            : RE_RELATED.test(this.__cbUrl) ? processRelated(json) : processList(json);
          if (changed) {
            Object.defineProperty(this, 'responseText', { value: JSON.stringify(json) });
            Object.defineProperty(this, 'response', { value: JSON.stringify(json) });
          }
        } catch (e) { /* ignore */ }
      });
    }
    return XS.apply(this, args);
  };

  // ---------- MutationObserver 兜底 ----------
  function observe() {
    handleSSRHot();
    const mo = new MutationObserver(() => {
      for (const [bvid, verdict] of hiddenVerdicts) {
        if (!verdict.hide) continue;
        const card = findCard(bvid);
        if (card && card.style.display !== 'none') {
          card.style.setProperty('display', 'none', 'important');
        }
      }
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', observe);
  } else {
    observe();
  }

  log('v0.1.0 loaded（mobile）. 流：SSR热榜 + region/feed/rcmd + archive/related');
  window.CleanBili = {
    test: (stat, title, tname, isOgv) => asyncVerdict({ stat, title: title || '', tname: tname || '', dimension: null, is_ogv: isOgv }),
    baseline: baselineCBI, counts, CONFIG,
    _internal: { processRegion, processRelated, processList, handleSSRHot },
  };
})();
