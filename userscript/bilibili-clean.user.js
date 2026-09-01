// ==UserScript==
// @name         洁净B站 Clean Bilibili
// @namespace    dsh-bilibili-clean
// @version      0.2.0
// @description  按《看过，却不给》v3 报告 §13 落地：CBI 感谢指数相对基线判定「看过不给」（R2）+ 加权感谢率 F7（R3）+ 竖屏/直播/短视频硬偏好（R1）+ 经检验标题签名（R7）+ 乞讨打标（R8）+ 官方区白名单（R4）。拒绝 log 分母（R5）、拒绝文体歧视（R6）。参数与 config/clean.config.json 同步。
// @author       CleanBili
// @match        https://www.bilibili.com/
// @match        https://www.bilibili.com/index.html*
// @match        https://www.bilibili.com/?*
// @run-at       document-start
// @grant        none
// ==/UserScript==

/* 洁净B站 —— v0.2（过滤器 v2：CBI 相对基线版）
 *
 * 判定顺序（对应报告 §13）：
 *   同步层（响应即删，不渲染）：直播 R1 / 短视频 R1 / 命中标题签名 R7
 *   异步层（view API 补全后判定）：
 *     1. 竖屏           R1  hide
 *     2. 播放 < 1000    R1  hide（低播放硬过滤）
 *     3. 官方区白名单    R4  跳过 CBI 判定（电影/电视剧/纪录片感谢率天然垫底，§7）
 *     4. CBI 判定       R2  播放 ≥ 5万 且 CBI < 0.5 → tier=junk，hide（看过不给）
 *     5. 全局 tier 兜底      播放 3千~5万之间用 v1 全局阈值（CBI 曲线在低播放段噪声大）
 *     6. 乞讨打标        R8  命中「投币X更新」等文本 → badge 标记，不惩罚
 *   拒绝 log 分母 R5（分母锁定 view）；拒绝标题文体歧视 R6（emoji/感叹/排版不参与判定）。
 *
 * CBI = F7 ÷ 同播放段基线中位数。F7 = (3×收藏 + 2×投币 + 0.3×点赞) / 播放。
 * 基线 = 滑动窗口分位数回归 P50 曲线（6,734 条样本拟合，2026-09-01，data/analysis/cbi_baseline.json）。
 */
(function () {
  'use strict';

  // ============ CONFIG：手动同步自 config/clean.config.json（v2） ============
  const CONFIG = {
    scoring: {
      weights: { favorite: 3.0, coin: 2.0, like: 0.3 },   // R3
      denominator_mode: 'view',                            // R5：锁定，log/√ 已废弃
      min_view_threshold: 3000,                            // 低于此 → unproven（比率不可信）
      tiers: { high: 0.107, normal: 0.064, low: 0.042 },   // v1 兜底阈值（3千~5万播放段）
    },
    cbi: {                                                  // R2：主判定
      enabled: true,
      min_view: 50000,                                     // 播放≥5万才做 CBI 判定
      threshold: 0.5,                                      // CBI < 0.5 → 「看过不给」
      // 滑窗分位回归 P50 基线：[log10_view, F7基线, ...]（n=6734，2026-09-01 拟合）
      curve: [4.5,0.2065,4.6,0.1745,4.7,0.1376,4.8,0.1247,4.9,0.1154,5.0,0.1057,5.1,0.0919,5.2,0.083,5.3,0.0742,5.4,0.0687,5.5,0.0605,5.6,0.0577,5.7,0.0557,5.8,0.058,5.9,0.0616,6.0,0.0664,6.1,0.0706,6.2,0.0779,6.3,0.082,6.4,0.0839,6.5,0.0848,6.6,0.0861,6.7,0.0861,6.8,0.0861,6.9,0.0852,7.0,0.0849,7.1,0.0854,7.2,0.0863],
    },
    filters: {
      short_video_max_duration_sec: 75,                    // R1
      portrait: { enabled: true, wh_ratio_min: 0.9 },      // R1
      live: true,                                          // R1
      min_views: 1000,                                     // R1 硬过滤
      block_keywords: [                                    // R7：仅经过检验的签名（§14 p<0.01）
        '第[0-9一二三四五六七八九十百]+[集话]',
        '挑战[^，。！？\\s]{1,12}(？|\\?|成功的可能性|能成吗)',
      ],
      zone_whitelist: ['电影', '电视剧', '纪录片'],          // R4：官方区跳过 CBI（§7 指纹）
      beggar_patterns: ['投币.{0,6}更新', '三连.{0,6}更新', '点赞过.{0,6}更新'],  // R8 观察项
      hide_tiers: ['junk'],                                // v2：只隐藏最低档；low 打标不隐藏（R2：不冤枉规模稀释）
      hide_unproven: false,
    },
    enrich: { enabled: true, concurrency: 4, cache_minutes: 30 },
    ui: { show_counter: true, show_badge: true },
  };
  // =====================================================================

  const FEED_RE = /\/x\/web-interface\/(wbi\/)?index\/top\/feed\/rcmd/;
  const counts = { 短视频: 0, 竖屏: 0, 直播: 0, 看过不给: 0, 低分: 0, 低播放: 0, 签名: 0, 乞讨标: 0 };
  const hiddenVerdicts = new Map();
  const verdictCache = new Map();
  const enrichQueue = [];
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

  // ---------- 同步层判定（响应即删） ----------
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

  // ---------- 异步层判定（view API 补全后） ----------
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

    // R2：CBI 主判定（播放≥5万，官方区豁免）
    if (CONFIG.cbi.enabled && view >= CONFIG.cbi.min_view && !whitelisted) {
      cbi = f7 / baselineCBI(Math.log10(view));
      if (cbi < CONFIG.cbi.threshold) {
        tier = 'junk';
        reasons.push(`看过不给(CBI ${cbi.toFixed(2)})`);
      }
    }
    // 全局 tier 兜底（3千~5万段）
    const hideTiers = [...f.hide_tiers, ...(f.hide_unproven ? ['unproven'] : [])];
    if (CONFIG.cbi.enabled && view >= CONFIG.cbi.min_view) {
      // CBI 段已判定；只有非白名单且 CBI 健康才不应用全局 low/junk
      if (!(cbi !== null && cbi >= CONFIG.cbi.threshold) && !whitelisted && hideTiers.includes(tier) && !reasons.some((x) => x.startsWith('看过不给'))) {
        reasons.push(`低分(${tier})`);
      }
    } else if (!whitelisted && hideTiers.includes(tier) && !reasons.some((x) => x.startsWith('低播放'))) {
      reasons.push(`低分(${tier})`);
    }
    // R8：乞讨打标（不惩罚）
    const title = data.title || '';
    if (f.beggar_patterns.length && matchesAny(title, f.beggar_patterns)) { beggar = true; reasons.push('乞讨标'); }

    return { hide: reasons.some((x) => !x.startsWith('乞讨标')), tier, f7, cbi, beggar, reasons, view, tname };
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
          const verdict = j && j.code === 0 ? asyncVerdict(j.data) : { hide: false, tier: 'unknown', f7: 0, cbi: null, beggar: false, reasons: [], view: 0, tname: '' };
          try { localStorage.setItem(ck, JSON.stringify({ t: Date.now(), verdict })); } catch (e) { /* ignore */ }
          resolve(verdict);
        })
        .catch(() => resolve({ hide: false, tier: 'unknown', f7: 0, cbi: null, beggar: false, reasons: [], view: 0, tname: '' }))
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
          if (verdict.hide || verdict.beggar) {
            for (const r of verdict.reasons) {
              const key = r.startsWith('短视频') ? '短视频' : r.startsWith('看过不给') ? '看过不给'
                : r.startsWith('低播放') ? '低播放' : r.startsWith('低分') ? '低分' : r.startsWith('乞讨标') ? '乞讨标' : r;
              if (r.startsWith('乞讨标')) { counts['乞讨标']++; break; }   // 乞讨只打标不计数隐藏
              counts[key] = (counts[key] || 0) + 1;
            }
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

  log('v0.2 loaded（CBI 相对基线版）. CONFIG=', CONFIG);

  // 暴露调试接口：控制台 CleanBili.test(stat, title, tname) 手动试算
  window.CleanBili = {
    test: (stat, title, tname) => asyncVerdict({ stat, title: title || '', tname: tname || '', dimension: null }),
    baseline: baselineCBI, counts, CONFIG,
  };
})();
