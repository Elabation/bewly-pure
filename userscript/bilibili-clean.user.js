// ==UserScript==
// @name         洁净B站 Clean Bilibili
// @namespace    dsh-bilibili-clean
// @version      0.1.0
// @description  过滤B站首页推荐：短视频/竖屏/直播/低评分视频。评分公式与阈值在 CONFIG 内手调（与 config/clean.config.json 保持同步）。
// @author       CleanBili
// @match        https://www.bilibili.com/
// @match        https://www.bilibili.com/index.html*
// @match        https://www.bilibili.com/?*
// @run-at       document-start
// @grant        none
// ==/UserScript==

/* 洁净B站 —— 原型 v0.1
 * 工作方式（两层过滤）：
 *   ① 同步层：劫持首页推荐接口响应，直接删掉 直播/短视频/命中关键词 的卡片（根本不渲染）
 *   ② 异步层：对留下的视频调 view API 拿 收藏/投币/宽高，算评分 → 低分/竖屏/低播放的卡片渲染后隐藏
 * 兜底：MutationObserver 处理晚渲染的卡片；所有过滤永不阻断页面本身。
 */
(function () {
  'use strict';

  // ============ CONFIG：手动同步自 config/clean.config.json ============
  const CONFIG = {
    scoring: {
      weights: { favorite: 3.0, coin: 2.0, like: 0.3 },
      denominator_mode: 'view',            // view | sqrt_view | log10_view
      min_view_threshold: 3000,            // 低于此播放量 → unproven
      tiers: { high: 0.107, normal: 0.064, low: 0.042 },  // 首轮校准值 2026-09-01，随 clean.config.json 同步
      below_min_view_tier: 'unproven',
    },
    filters: {
      short_video_max_duration_sec: 75,
      portrait: { enabled: true, wh_ratio_min: 0.9 },
      live: true,
      min_views: 1000,
      block_keywords: [],                  // 标题命中即过滤
      hide_tiers: ['low', 'junk'],
      hide_unproven: false,
    },
    enrich: { enabled: true, concurrency: 4, cache_minutes: 30 },
    ui: { show_counter: true, show_badge: true },
  };
  // =====================================================================

  const FEED_RE = /\/x\/web-interface\/(wbi\/)?index\/top\/feed\/rcmd/;
  const counts = { 短视频: 0, 竖屏: 0, 直播: 0, 低分: 0, 低播放: 0, 关键词: 0, 其他: 0 };
  const hiddenVerdicts = new Map();   // bvid -> { hide, tier, ratio, reasons[] }
  const verdictCache = new Map();     // bvid -> { t, verdict } 内存缓存
  const enrichQueue = [];
  let enrichActive = 0;

  const log = (...a) => console.log('%c[CleanBili]', 'color:#2196f3;font-weight:bold', ...a);

  // ---------- 评分（与 engine/scoring.py 同逻辑） ----------
  function scoreOf(stat) {
    const w = CONFIG.scoring.weights;
    const view = stat.view || 0;
    const raw = (stat.favorite || 0) * w.favorite + (stat.coin || 0) * w.coin + (stat.like || 0) * w.like;
    let denom = Math.max(view, 1);
    if (CONFIG.scoring.denominator_mode === 'sqrt_view') denom = Math.sqrt(Math.max(view, 1));
    else if (CONFIG.scoring.denominator_mode === 'log10_view') denom = Math.log10(Math.max(view, 10));
    return { ratio: view > 0 ? raw / denom : 0, view, raw };
  }
  function tierOf(ratio, view) {
    const sc = CONFIG.scoring;
    if (view < sc.min_view_threshold) return sc.below_min_view_tier;
    const t = sc.tiers;
    return ratio >= t.high ? 'high' : ratio >= t.normal ? 'normal' : ratio >= t.low ? 'low' : 'junk';
  }
  function effWH(dim) {
    let w = dim.width || 0, h = dim.height || 0;
    if (dim.rotate === 90 || dim.rotate === 270) [w, h] = [h, w];
    return [w, h];
  }

  // ---------- 过滤判定 ----------
  function syncReasons(item) {
    const r = [];
    const f = CONFIG.filters;
    if (item.goto !== 'av') {
      if (item.goto === 'live' && f.live) r.push('直播');
      else r.push('其他');
      return r;
    }
    const dur = item.duration || 0;
    if (dur && dur <= f.short_video_max_duration_sec) r.push(`短视频(${dur}s)`);
    const title = item.title || '';
    for (const kw of f.block_keywords) if (kw && title.includes(kw)) { r.push('关键词'); break; }
    return r;
  }

  function asyncVerdict(data) {
    const f = CONFIG.filters;
    const reasons = [];
    const stat = data.stat || {};
    const view = stat.view || 0;
    if (f.portrait.enabled && data.dimension) {
      const [w, h] = effWH(data.dimension);
      if (w && h && w / h < f.portrait.wh_ratio_min) reasons.push('竖屏');
    }
    if (f.min_views && view < f.min_views) reasons.push(`低播放(${view})`);
    const { ratio } = scoreOf(stat);
    const tier = tierOf(ratio, view);
    const hideTiers = [...f.hide_tiers, ...(f.hide_unproven ? ['unproven'] : [])];
    if (hideTiers.includes(tier)) reasons.push(`低分(${tier})`);
    return { hide: reasons.length > 0, tier, ratio, reasons, view };
  }

  // ---------- 异步补全（并发限制 + localStorage 缓存） ----------
  function enrich(bvid) {
    return new Promise((resolve) => {
      const ck = 'cleanbili_' + bvid;
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
          const verdict = j && j.code === 0 ? asyncVerdict(j.data) : { hide: false, tier: 'unknown', ratio: 0, reasons: [] };
          try { localStorage.setItem(ck, JSON.stringify({ t: Date.now(), verdict })); } catch (e) { /* ignore */ }
          resolve(verdict);
        })
        .catch(() => resolve({ hide: false, tier: 'unknown', ratio: 0, reasons: [] }))
        .finally(() => { enrichActive--; pump(); });
    }
  }

  // ---------- DOM 处理 ----------
  function findCard(bvid) {
    const a = document.querySelector(`a[href*="/video/${bvid}"], a[href*="bvid=${bvid}"]`);
    if (!a) return null;
    return a.closest('.bili-video-card, .feed-card, .bili-feed-card') || a.parentElement;
  }
  function applyVerdict(bvid, verdict) {
    hiddenVerdicts.set(bvid, verdict);
    const card = findCard(bvid);
    if (verdict.hide && card) {
      card.style.setProperty('display', 'none', 'important');
      card.dataset.cleanbili = 'hidden';
    }
    if (CONFIG.ui.show_badge && card && !card.querySelector('.cleanbili-badge')) {
      const badge = document.createElement('div');
      badge.className = 'cleanbili-badge';
      badge.textContent = `${verdict.ratio.toFixed(3)} · ${verdict.tier}`;
      const color = { high: '#1b9e77', normal: '#666', low: '#d95f02', junk: '#e41a1c', unproven: '#999' }[verdict.tier] || '#999';
      badge.style.cssText = `position:absolute;top:4px;right:4px;z-index:9;background:#000a;color:#fff;` +
        `font-size:11px;line-height:1;padding:3px 6px;border-radius:3px;border:1px solid ${color}`;
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
      chip.style.cssText = 'position:fixed;left:8px;bottom:8px;z-index:99999;background:#1f2937e6;color:#e5e7eb;' +
        'font:12px/1.5 system-ui;padding:6px 10px;border-radius:6px;pointer-events:none;white-space:pre-line;';
      document.body.appendChild(chip);
    }
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    if (!total) { chip.style.display = 'none'; return; }
    chip.style.display = 'block';
    chip.textContent = '洁净B站 已过滤 ' + total + '\n' + Object.entries(counts)
      .filter(([, n]) => n > 0).map(([k, n]) => `${k} ${n}`).join(' · ');
  }

  // ---------- 推荐流响应处理 ----------
  function processFeed(json) {
    const data = json && json.data;
    if (!data || !Array.isArray(data.item)) return false;
    const kept = [];
    for (const item of data.item) {
      const reasons = syncReasons(item);
      if (reasons.length) {
        for (const r of reasons) counts[r.includes('短视频') ? '短视频' : r] = (counts[r.includes('短视频') ? '短视频' : r] || 0) + 1;
        log('sync-filtered', item.goto, (item.title || '').slice(0, 24), reasons.join(','));
        continue;
      }
      kept.push(item);
    }
    data.item = kept;
    if (CONFIG.enrich.enabled) {
      for (const item of kept) {
        const bvid = item.bvid;
        if (!bvid || hiddenVerdicts.has(bvid)) continue;
        enrich(bvid).then((verdict) => {
          if (verdict.hide) for (const r of verdict.reasons) {
            const key = r.startsWith('短视频') ? '短视频' : r.startsWith('低播放') ? '低播放' : r.startsWith('低分') ? '低分' : r;
            counts[key] = (counts[key] || 0) + 1;
          }
          applyVerdict(bvid, verdict);
        });
      }
    }
    updateCounter();
    return true;
  }

  // ---------- fetch 劫持 ----------
  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    const res = await origFetch.apply(this, args);
    try {
      const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '';
      if (FEED_RE.test(url) && res.ok) {
        const json = JSON.parse(await res.clone().text());
        if (processFeed(json)) {
          return new Response(JSON.stringify(json), {
            status: res.status, statusText: res.statusText, headers: res.headers,
          });
        }
      }
    } catch (e) { console.warn('[CleanBili] hook error', e); }
    return res;
  };

  // ---------- MutationObserver 兜底：晚渲染的卡片 ----------
  function observe() {
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

  log('v0.1 loaded. CONFIG=', CONFIG);
})();
