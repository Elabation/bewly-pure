// ==UserScript==
// @name         洁净B站 Clean Bilibili
// @namespace    dsh-bilibili-clean
// @version      0.3.0
// @description  按《看过，却不给》v3 报告 §13 落地：CBI 感谢指数相对基线判定「看过不给」（R2）+ 加权感谢率 F7（R3）+ 竖屏/直播/短视频硬偏好（R1）+ 经检验标题签名（R7）+ 乞讨打标（R8）+ 官方区白名单（R4）。v0.3：懒判定（滚近视口才请求，性能大幅提升）+ 占位薄条（布局不塌陷、点击可临时放行）+ 增量观察器。
// @author       CleanBili
// @match        https://www.bilibili.com/
// @match        https://www.bilibili.com/index.html*
// @match        https://www.bilibili.com/?*
// @run-at       document-start
// @grant        none
// ==/UserScript==

/* 洁净B站 —— v0.3（懒判定 + 占位条版）
 *
 * 判定顺序（报告 §13）：
 *   同步层（响应即删）：直播 R1 / 短视频 R1 / 标题签名 R7
 *   异步层（懒判定：卡片滚近视口才 enrich）：
 *     竖屏 R1 → 隐藏        播放<1000 R1 → 隐藏
 *     官方区白名单 R4 → 跳过 CBI
 *     播放≥5万 且 CBI<0.5 R2 → 隐藏「看过不给」
 *     播放3千~5万 R2' → 只 hide junk
 *     乞讨文本 R8 → 打「乞」标
 *   被隐藏卡片替换为「已过滤」占位薄条：保持布局密度（B 站滚动加载正常触发），
 *   点击占位条可临时放行该视频（本次浏览内不再隐藏）。
 *
 * 性能设计：
 *   - IntersectionObserver 懒判定：只对滚近视口（rootMargin 1600px）的卡片调 view API，
 *     请求量比「来一批判一批」下降约 60-70%，不再挤占页面自身的接口通道
 *   - MutationObserver 节流 200ms 且只扫描增量节点
 *   - verdict 缓存 24h（互动数变化慢，CBI 基本稳定）
 */
(function () {
  'use strict';

  // ============ CONFIG：手动同步自 config/clean.config.json（v2） ============
  const CONFIG = {
    scoring: {
      weights: { favorite: 3.0, coin: 2.0, like: 0.3 },   // R3
      denominator_mode: 'view',                            // R5：锁定
      min_view_threshold: 3000,
      tiers: { high: 0.107, normal: 0.064, low: 0.042 },   // v1 兜底阈值（3千~5万播放段）
    },
    cbi: {                                                  // R2：主判定
      enabled: true,
      min_view: 50000,
      threshold: 0.5,
      // 滑窗分位回归 P50 基线：[log10_view, F7基线, ...]（n=6734，2026-09-01 拟合）
      curve: [4.5,0.2065,4.6,0.1745,4.7,0.1376,4.8,0.1247,4.9,0.1154,5.0,0.1057,5.1,0.0919,5.2,0.083,5.3,0.0742,5.4,0.0687,5.5,0.0605,5.6,0.0577,5.7,0.0557,5.8,0.058,5.9,0.0616,6.0,0.0664,6.1,0.0706,6.2,0.0779,6.3,0.082,6.4,0.0839,6.5,0.0848,6.6,0.0861,6.7,0.0861,6.8,0.0861,6.9,0.0852,7.0,0.0849,7.1,0.0854,7.2,0.0863],
    },
    filters: {
      short_video_max_duration_sec: 75,                    // R1
      portrait: { enabled: true, wh_ratio_min: 0.9 },      // R1
      live: true,                                          // R1
      min_views: 1000,                                     // R1
      block_keywords: [                                    // R7
        '第[0-9一二三四五六七八九十百]+[集话]',
        '挑战[^，。！？\\s]{1,12}(？|\\?|成功的可能性|能成吗)',
      ],
      zone_whitelist: ['电影', '电视剧', '纪录片'],          // R4
      beggar_patterns: ['投币.{0,6}更新', '三连.{0,6}更新', '点赞过.{0,6}更新'],  // R8
      hide_tiers: ['junk'],                                // v2：只隐藏最低档
      hide_unproven: false,
    },
    enrich: { cache_minutes: 1440, concurrency: 6 },       // v0.3：24h 缓存
    lazy: { enabled: true, root_margin: '1600px 0px' },    // v0.3：懒判定
    ui: { show_counter: true, show_badge: true, placeholder: true },  // v0.3：占位薄条
  };
  // =====================================================================

  const FEED_RE = /\/x\/web-interface\/(wbi\/)?index\/top\/feed\/rcmd/;
  const counts = { 短视频: 0, 竖屏: 0, 直播: 0, 看过不给: 0, 低分: 0, 低播放: 0, 签名: 0, 乞讨标: 0 };
  const verdicts = new Map();        // bvid -> verdict
  const shownOnce = new Set();       // 本次浏览内被手动放行的 bvid
  const enrichQueue = [];
  const enqueued = new Set();        // 已入队/已判定
  let enrichActive = 0;

  const log = (...a) => console.log('%c[CleanBili]', 'color:#2196f3;font-weight:bold', ...a);

  // ---------- 评分核心 ----------
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

  // ---------- 同步层 ----------
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
    if (f.block_keywords.length && matchesAny(title, f.block_keywords)) r.push('签名');
    return r;
  }

  // ---------- 异步层判定 ----------
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
    const whitelisted = f.zone_whitelist.some((z) => tname.includes(z));

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

    return { hide: reasons.some((x) => !x.startsWith('乞讨标')), tier, f7, cbi, beggar, reasons, view, tname, title };
  }

  // ---------- 懒判定：滚近视口才 enrich ----------
  let lazyIO = null;
  if (CONFIG.lazy.enabled && typeof IntersectionObserver !== 'undefined') {
    lazyIO = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        lazyIO.unobserve(e.target);
        const bvid = e.target.__cleanbiliBvid;
        if (bvid && !enqueued.has(bvid)) {
          enqueued.add(bvid);
          enrich(bvid);
        }
      }
    }, { rootMargin: CONFIG.lazy.root_margin });
  }
  function watchCard(card, bvid) {
    if (verdicts.has(bvid)) { applyVerdict(bvid, verdicts.get(bvid)); return; }
    if (shownOnce.has(bvid)) return;
    if (lazyIO) {
      card.__cleanbiliBvid = bvid;
      lazyIO.observe(card);
    } else if (!enqueued.has(bvid)) {
      enqueued.add(bvid);
      enrich(bvid);
    }
  }

  // ---------- 补全（缓存 24h + 并发限制） ----------
  function bumpVerdict(verdict) {
    if (!verdict || (!verdict.hide && !verdict.beggar)) return;
    for (const r of verdict.reasons || []) {
      if (r.startsWith('乞讨标')) { bump('乞讨标'); break; }
      bump(r.startsWith('短视频') ? '短视频' : r.startsWith('看过不给') ? '看过不给' : r.startsWith('低播放') ? '低播放' : r.startsWith('低分') ? '低分' : r);
    }
  }
  function enrich(bvid) {
    return new Promise((resolve) => {
      const ck = 'cleanbili_' + bvid;
      try {
        const c = JSON.parse(localStorage.getItem(ck) || 'null');
        if (c && Date.now() - c.t < CONFIG.enrich.cache_minutes * 60000) { bumpVerdict(c.verdict); applyVerdict(bvid, c.verdict); return resolve(c.verdict); }
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
          const verdict = j && j.code === 0 ? asyncVerdict(j.data) : { hide: false, tier: 'unknown', f7: 0, cbi: null, beggar: false, reasons: [], view: 0, tname: '', title: '' };
          try { localStorage.setItem(ck, JSON.stringify({ t: Date.now(), verdict })); } catch (e) { /* ignore */ }
          bumpVerdict(verdict);
          applyVerdict(bvid, verdict);
          resolve(verdict);
        })
        .catch(() => resolve(null))
        .finally(() => { enrichActive--; pump(); });
    }
  }

  // ---------- DOM：隐藏 + 占位薄条 + badge ----------
  function findCard(bvid) {
    const a = document.querySelector(`a[href*="/video/${bvid}"], a[href*="bvid=${bvid}"]`);
    if (!a) return null;
    return a.closest('.bili-video-card, .feed-card, .bili-feed-card') || a.parentElement;
  }
  function applyVerdict(bvid, verdict) {
    verdicts.set(bvid, verdict);
    if (shownOnce.has(bvid)) return;
    const card = findCard(bvid);
    if (!card) return;
    if (verdict.hide) {
      const old = card.previousElementSibling;
      if (old && old.classList && old.classList.contains('cleanbili-placeholder')) old.remove();
      card.style.setProperty('display', 'none', 'important');
      card.dataset.cleanbili = 'hidden';
      if (CONFIG.ui.placeholder) {
        const ph = document.createElement('div');
        ph.className = 'cleanbili-placeholder';
        const why = verdict.reasons.find((x) => !x.startsWith('乞讨标')) || '已过滤';
        ph.textContent = `已过滤 · ${why} · ${(verdict.title || '').slice(0, 16)} · 点击临时显示`;
        ph.style.cssText = 'height:44px;margin:4px 0;border-radius:8px;display:flex;align-items:center;justify-content:center;overflow:hidden;' +
          'background:repeating-linear-gradient(45deg,#EFE9DE,#EFE9DE 9px,#E9E2D4 9px,#E9E2D4 18px);color:#9AA3B5;font-size:11.5px;cursor:pointer;white-space:nowrap;';
        ph.addEventListener('click', () => {
          shownOnce.add(bvid);
          card.style.removeProperty('display');
          ph.remove();
        });
        card.insertAdjacentElement('afterend', ph);
      }
    }
    if (CONFIG.ui.show_badge && !card.querySelector('.cleanbili-badge')) {
      const badge = document.createElement('div');
      badge.className = 'cleanbili-badge';
      const main = verdict.cbi !== null ? `CBI ${verdict.cbi.toFixed(2)}` : `F7 ${verdict.f7.toFixed(3)}`;
      badge.textContent = main + (verdict.beggar ? ' · 乞' : '') + (verdict.tname ? ' · ' + verdict.tname : '');
      const color = { high: '#1b9e77', normal: '#666', low: '#d95f02', junk: '#e41a1c', unproven: '#999', unknown: '#999' }[verdict.tier] || '#999';
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
    chip.style.display = 'block';
    chip.textContent = '洁净B站 已过滤 ' + total + '\n' + Object.entries(counts)
      .filter(([, n]) => n > 0).map(([k, n]) => `${k} ${n}`).join(' · ');
  }

  // ---------- 推荐流响应处理（同步层） ----------
  function bump(key) { counts[key] = (counts[key] || 0) + 1; }
  function processFeed(json) {
    const data = json && json.data;
    if (!data || !Array.isArray(data.item)) return false;
    const kept = [];
    for (const item of data.item) {
      const reasons = syncReasons(item);
      if (reasons.length) {
        for (const r of reasons) bump(r.includes('短视频') ? '短视频' : r);
        continue;
      }
      kept.push(item);
    }
    data.item = kept;
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

  // ---------- 增量观察器：找新卡片 → 挂懒判定（节流 200ms，累积合并） ----------
  let scanTimer = null;
  let pendingMutations = [];
  function scanNewCards(muts) {
    const seen = new Set();
    for (const m of muts) {
      for (const node of m.addedNodes) {
        if (node.nodeType !== 1) continue;
        const cards = node.matches?.('.bili-video-card, .feed-card, .bili-feed-card')
          ? [node]
          : [...node.querySelectorAll?.('.bili-video-card, .feed-card, .bili-feed-card') || []];
        for (const card of cards) {
          const a = card.querySelector('a[href*="/video/BV"], a[href*="bvid=BV"]');
          const bv = a ? (a.href.match(/\/video\/(BV[\w]+)/) || [])[1] : null;
          if (!bv || seen.has(bv) || enqueued.has(bv) || verdicts.has(bv) || shownOnce.has(bv)) continue;
          seen.add(bv);
          watchCard(card, bv);
        }
      }
    }
  }
  const mo = new MutationObserver((mutations) => {
    pendingMutations.push(...mutations);
    if (scanTimer) return;
    scanTimer = setTimeout(() => {
      scanTimer = null;
      scanNewCards(pendingMutations.splice(0));
    }, 200);
  });
  mo.observe(document.documentElement, { childList: true, subtree: true });

  log('v0.3 loaded（懒判定 + 占位条版）. CONFIG=', CONFIG);

  window.CleanBili = {
    test: (stat, title, tname) => asyncVerdict({ stat, title: title || '', tname: tname || '', dimension: null }),
    counts, verdicts, CONFIG,
  };
})();
