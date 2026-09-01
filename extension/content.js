/* 洁净B站 Clean Bilibili · Edge 扩展 content.js v1.0
 *
 * 接管 bilibili.com 首页推荐流：网格铺平渲染（BewlyBewly 思路的自研实现），
 * 保留 B 站原顶栏（搜索/头像/历史/收藏全部原生可用）。
 * 判定核心与 userscript v0.3 / config/clean.config.json v2 同步（报告 §13）：
 *   同步层：直播 R1 / 短视频 R1 / 标题签名 R7
 *   异步层：竖屏 R1 / 低播放 R1 / 官方区白名单 R4 / CBI<0.5 R2 / junk 兜底 / 乞讨标 R8
 * 与 userscript 的关键差异：低质卡片**不渲染**（网格自动重排，无空洞无占位条）。
 *
 * 基础设施自建：wbi 签名（nav 取 key + 44 位置换 + MD5）→ 直接请求 rcmd，不劫持页面。
 */
(function () {
  'use strict';
  if (window.__CLEANBILI_EXT__) return;
  window.__CLEANBILI_EXT__ = true;

  // ============ CONFIG（与 config/clean.config.json v2 同步） ============
  const CONFIG = {
    scoring: { weights: { favorite: 3.0, coin: 2.0, like: 0.3 }, denominator_mode: 'view', min_view_threshold: 3000, tiers: { high: 0.107, normal: 0.064, low: 0.042 } },
    cbi: { enabled: true, min_view: 50000, threshold: 0.5,
      curve: [4.5,0.2065,4.6,0.1745,4.7,0.1376,4.8,0.1247,4.9,0.1154,5.0,0.1057,5.1,0.0919,5.2,0.083,5.3,0.0742,5.4,0.0687,5.5,0.0605,5.6,0.0577,5.7,0.0557,5.8,0.058,5.9,0.0616,6.0,0.0664,6.1,0.0706,6.2,0.0779,6.3,0.082,6.4,0.0839,6.5,0.0848,6.6,0.0861,6.7,0.0861,6.8,0.0861,6.9,0.0852,7.0,0.0849,7.1,0.0854,7.2,0.0863] },
    filters: {
      short_video_max_duration_sec: 75,
      portrait: { enabled: true, wh_ratio_min: 0.9 },
      live: true, min_views: 1000,
      block_keywords: ['第[0-9一二三四五六七八九十百]+[集话]', '挑战[^，。！？\\s]{1,12}(？|\\?|成功的可能性|能成吗)'],
      zone_whitelist: ['电影', '电视剧', '纪录片'],
      beggar_patterns: ['投币.{0,6}更新', '三连.{0,6}更新', '点赞过.{0,6}更新'],
      hide_tiers: ['junk'], hide_unproven: false,
    },
    feed: { ps: 20, batch_interval_min_ms: 400 },
    lazy: { root_margin: '1200px 0px' },
  };
  // ======================================================================

  const counts = { 短视频: 0, 竖屏: 0, 直播: 0, 看过不给: 0, 低分: 0, 低播放: 0, 签名: 0, 乞讨标: 0, 其他: 0 };
  const verdicts = new Map();
  const seenBvids = new Set();
  const cards = new Map();          // bvid -> card element
  let freshIdx = 0;
  let loading = false;
  let gridEl = null, statusEl = null, sentinelEl = null, rootEl = null;
  let mixinKey = null, mixinFetchedAt = 0;

  // ---------- wbi 签名（自建） ----------
  const MIXIN_TAB = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1];
  async function getMixinKey() {
    if (mixinKey && Date.now() - mixinFetchedAt < 6 * 3600 * 1000) return mixinKey;
    const r = await (await fetch('https://api.bilibili.com/x/web-interface/nav', { credentials: 'include' })).json();
    const wbi = r.data && r.data.wbi_img;
    if (!wbi) throw new Error('nav wbi_img missing');
    const raw = (wbi.img_url.split('/').pop() || '').split('.')[0] + (wbi.sub_url.split('/').pop() || '').split('.')[0];
    let key = '';
    for (const i of MIXIN_TAB) key += raw[i] || '';
    mixinKey = key.slice(0, 32);
    mixinFetchedAt = Date.now();
    return mixinKey;
  }
  function wbiSign(params, key) {
    const wts = Math.floor(Date.now() / 1000);
    const merged = Object.assign({}, params, { wts });
    const query = Object.keys(merged).sort().map((k) => {
      const v = String(merged[k]).replace(/[!'()*]/g, '');
      return encodeURIComponent(k) + '=' + encodeURIComponent(v);
    }).join('&');
    const w_rid = window.CleanBiliMD5(query + key);
    return query + '&w_rid=' + w_rid + '&wts=' + wts;
  }

  // ---------- 推荐流 ----------
  async function fetchRcmd() {
    freshIdx += 1;
    const params = {
      platform: 'web', ps: CONFIG.feed.ps,
      fresh_idx: freshIdx, fresh_idx_1h: freshIdx, fresh_idx_4h: freshIdx, fresh_idx_5d: freshIdx,
      web_location: 1430655,
    };
    const key = await getMixinKey();
    const url = 'https://api.bilibili.com/x/web-interface/index/top/feed/rcmd?' + wbiSign(params, key);
    const j = await (await fetch(url, { credentials: 'include' })).json();
    if (j.code !== 0) throw new Error('rcmd code=' + j.code);
    return j.data && j.data.item ? j.data.item : [];
  }

  // ---------- 判定核心（与 userscript v0.3 同步） ----------
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
    if (dim.rotate === 90 || dim.rotate === 270) { const x = w; w = h; h = x; }
    return [w, h];
  }
  function matchesAny(title, patterns) {
    for (const p of patterns) {
      try { if (new RegExp(p).test(title)) return true; } catch (e) { if (title.includes(p)) return true; }
    }
    return false;
  }
  function syncFilter(item) {
    const f = CONFIG.filters;
    const reasons = [];
    if (item.goto !== 'av') { reasons.push(item.goto === 'live' && f.live ? '直播' : '其他'); return reasons; }
    const dur = item.duration || 0;
    if (dur && dur <= f.short_video_max_duration_sec) reasons.push('短视频(' + dur + 's)');
    if (matchesAny(item.title || '', f.block_keywords)) reasons.push('签名');
    return reasons;
  }
  function asyncVerdict(data) {
    const f = CONFIG.filters;
    const reasons = [];
    const stat = data.stat || {};
    const view = stat.view || 0;
    const f7 = f7Of(stat).f7;
    let tier = tierOf(f7, view);
    let cbi = null;
    let beggar = false;

    if (f.portrait.enabled && data.dimension) {
      const wh = effWH(data.dimension);
      if (wh[0] && wh[1] && wh[0] / wh[1] < f.portrait.wh_ratio_min) reasons.push('竖屏');
    }
    if (f.min_views && view < f.min_views) reasons.push('低播放(' + view + ')');

    const tname = data.tname || '';
    const whitelisted = f.zone_whitelist.some((z) => tname.includes(z));
    if (CONFIG.cbi.enabled && view >= CONFIG.cbi.min_view && !whitelisted) {
      cbi = f7 / baselineCBI(Math.log10(view));
      if (cbi < CONFIG.cbi.threshold) { tier = 'junk'; reasons.push('看过不给(CBI ' + cbi.toFixed(2) + ')'); }
    }
    const hideTiers = f.hide_tiers.slice(0);
    if (CONFIG.cbi.enabled && view >= CONFIG.cbi.min_view) {
      if (!(cbi !== null && cbi >= CONFIG.cbi.threshold) && !whitelisted && hideTiers.includes(tier) && !reasons.some((x) => x.startsWith('看过不给'))) reasons.push('低分(' + tier + ')');
    } else if (!whitelisted && hideTiers.includes(tier) && !reasons.some((x) => x.startsWith('低播放'))) reasons.push('低分(' + tier + ')');

    const title = data.title || '';
    if (f.beggar_patterns.length && matchesAny(title, f.beggar_patterns)) { beggar = true; reasons.push('乞讨标'); }
    return { hide: reasons.some((x) => !x.startsWith('乞讨标')), tier, f7, cbi, beggar, reasons, view, tname, title };
  }
  function bump(key) { counts[key] = (counts[key] || 0) + 1; }

  // ---------- 懒判定（view API） ----------
  const lazyIO = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      lazyIO.unobserve(e.target);
      const bvid = e.target.__cbBvid;
      if (bvid && !verdicts.has(bvid)) enrichAndJudge(bvid, e.target);
    }
  }, { rootMargin: CONFIG.lazy.root_margin });

  async function enrichAndJudge(bvid, card) {
    try {
      const r = await (await fetch('https://api.bilibili.com/x/web-interface/view?bvid=' + bvid, { credentials: 'include' })).json();
      if (r.code !== 0) return;
      const v = asyncVerdict(r.data);
      verdicts.set(bvid, v);
      if (v.hide) { bump(v.reasons.find((x) => !x.startsWith('乞讨标')).split('(')[0]); removeCard(bvid); }
      else {
        const badge = card.querySelector('.cb-badge');
        if (badge) {
          badge.hidden = false;
          badge.textContent = (v.cbi !== null ? 'CBI ' + v.cbi.toFixed(2) : 'F7 ' + v.f7.toFixed(3)) + (v.beggar ? ' · 乞' : '') + (v.tname ? ' · ' + v.tname : '');
          badge.className = 'cb-badge ' + v.tier;
        }
      }
      updateStatus();
    } catch (e) { /* 静默：判定失败按保留处理 */ }
  }
  function removeCard(bvid) {
    const card = cards.get(bvid);
    if (card) { card.remove(); cards.delete(bvid); }
  }

  // ---------- 网格渲染 ----------
  function fmtNum(n) {
    n = n || 0;
    return n >= 100000000 ? (n / 100000000).toFixed(1) + '亿' : n >= 10000 ? (n / 10000).toFixed(1) + '万' : String(n);
  }
  function fmtDur(s) {
    s = s || 0;
    const m = Math.floor(s / 60), sec = s % 60;
    return m + ':' + String(sec).padStart(2, '0');
  }
  function renderCard(item) {
    const bvid = item.bvid;
    if (!bvid || seenBvids.has(bvid)) return;
    seenBvids.add(bvid);

    const reasons = syncFilter(item);
    if (reasons.length) { for (const r of reasons) bump(r.split('(')[0]); updateStatus(); return; }

    const a = document.createElement('a');
    a.className = 'cb-card';
    a.href = 'https://www.bilibili.com/video/' + bvid;
    a.target = '_blank';
    a.rel = 'noopener';
    a.__cbBvid = bvid;

    const pic = (item.pic || '').replace(/^http:/, 'https:');
    const meta = [];
    if (item.stat && item.stat.view) meta.push(fmtNum(item.stat.view) + ' 播放');
    if (item.stat && item.stat.danmaku) meta.push(fmtNum(item.stat.danmaku) + ' 弹幕');
    if (item.owner && item.owner.name) meta.push(item.owner.name);

    a.innerHTML =
      '<div class="cb-thumb"><img loading="lazy" alt="" src="' + pic + '">' +
      '<span class="cb-dur">' + fmtDur(item.duration) + '</span>' +
      '<span class="cb-badge" hidden></span></div>' +
      '<div class="cb-info"><div class="cb-title"></div><div class="cb-meta"></div></div>';
    a.querySelector('.cb-title').textContent = (item.title || '').replace(/<[^>]+>/g, '');
    a.querySelector('.cb-meta').textContent = meta.join(' · ');
    gridEl.appendChild(a);
    cards.set(bvid, a);
    lazyIO.observe(a);
  }

  async function loadMore() {
    if (loading) return;
    loading = true;
    try {
      const items = await fetchRcmd();
      for (const it of items) renderCard(it);
      updateStatus();
    } catch (e) {
      console.warn('[CleanBili] loadMore error', e);
      await new Promise((r) => setTimeout(r, 3000));   // 退避
    } finally {
      loading = false;
    }
  }

  function updateStatus() {
    if (!statusEl) return;
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    const parts = Object.entries(counts).filter(([, n]) => n > 0).map(([k, n]) => k + ' ' + n).join(' · ');
    statusEl.textContent = '洁净B站 · 网格模式 · 已过滤 ' + total + (parts ? '（' + parts + '）' : '');
  }

  // ---------- 接管首页 ----------
  function boot() {
    const header = document.querySelector('.bili-header');
    if (!header) { console.warn('[CleanBili] 未找到 .bili-header，B 站结构变化，插件不接管'); return; }
    // 拒绝接管：若用户上次点了「切回原版」
    if (sessionStorage.getItem('cleanbili_off') === '1') return;

    document.documentElement.classList.add('cleanbili-on');

    rootEl = document.createElement('div');
    rootEl.id = 'cleanbili-root';
    const bar = document.createElement('div');
    bar.className = 'cb-bar';
    statusEl = document.createElement('span');
    statusEl.className = 'cb-status';
    const offBtn = document.createElement('a');
    offBtn.className = 'cb-off';
    offBtn.textContent = '切回原版';
    offBtn.href = 'javascript:void(0)';
    offBtn.addEventListener('click', () => {
      sessionStorage.setItem('cleanbili_off', '1');
      document.documentElement.classList.remove('cleanbili-on');
      rootEl.remove();
    });
    bar.appendChild(statusEl);
    bar.appendChild(offBtn);

    gridEl = document.createElement('div');
    gridEl.className = 'cb-grid';

    sentinelEl = document.createElement('div');
    sentinelEl.className = 'cb-sentinel';

    rootEl.appendChild(bar);
    rootEl.appendChild(gridEl);
    rootEl.appendChild(sentinelEl);
    // 挂载点：.bili-feed4（含顶栏+原推荐区）之后；不要插进 header 后（会落进 feed4 内部被 CSS 波及）
    const mountAfter = document.querySelector('.bili-feed4') || header;
    mountAfter.insertAdjacentElement('afterend', rootEl);

    new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) loadMore();
    }, { rootMargin: '800px 0px' }).observe(sentinelEl);

    updateStatus();
    loadMore();
    console.log('%c[CleanBili]', 'color:#2196f3;font-weight:bold', '扩展 v1.0 已接管首页（网格模式）');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  window.CleanBili = { counts, verdicts, CONFIG, removeCard };
})();
