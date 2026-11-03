'use strict';
const BOOT=JSON.parse(document.getElementById('payload').textContent),$=id=>document.getElementById(id);
const PROFILE='craft_resonance_v1',SCHEMA='bili-review-v1',storageKey='bili_review_'+PROFILE;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const reasons=new Set(['craft_expression','sentiment_only','effort_only','utility_only','other']);
function validate(d){if(!d||d.schema!==SCHEMA||d.profile_id!==PROFILE||!d.reviews||Array.isArray(d.reviews))throw Error('需要制作/共鸣版本的标注文件');const result=Object.create(null);for(const [b,r] of Object.entries(d.reviews)){if(!/^BV[\da-zA-Z]{10}$/.test(b)||!r||typeof r!=='object')throw Error('标注条目不正确');for(const k of ['craft','resonance'])if(r[k]!=null&&(!Number.isInteger(r[k])||r[k]<0||r[k]>3))throw Error('评分应为0～3');if(r.reason&&!reasons.has(r.reason))throw Error('理由不正确');if(r.watched!=null&&typeof r.watched!=='boolean')throw Error('观看状态不正确');if(r.evidence!=null&&typeof r.evidence!=='string')throw Error('理由需要文字');result[b]={craft:r.craft??null,resonance:r.resonance??null,reason:r.reason??'',evidence:r.evidence??'',watched:r.watched===true};}return result;}
function status(r){if(!r||r.watched!==true)return 'unreviewed';if(!Number.isInteger(r.craft)||!Number.isInteger(r.resonance)||!reasons.has(r.reason)||!r.evidence?.trim())return 'incomplete';return r.craft>=2&&r.resonance>=2&&r.reason==='craft_expression'?'confirmed':'not_fit';}
let activeDay=BOOT.latest_day;
let reviews=Object.create(null),tab='daily',page=0,total=BOOT.streams.daily.count,currentRows=[],query='',token=0,worker,searchTimer,selected,history=[];
try{const s=localStorage.getItem(storageKey);if(s)reviews=validate(JSON.parse(s));}catch(e){$('message').textContent='本地标注未能读取；可重新导入。';}
const unpack=row=>Object.fromEntries(BOOT.fields.map((k,i)=>[k,row[i]]));
const cache=new Map(),pending=new Map();
window.BiliDiscovery={receive(key,rows){const r=pending.get(key);if(r){cache.set(key,rows);if(cache.size>12)cache.delete(cache.keys().next().value);pending.delete(key);r.resolve(rows);}}};
function chunk(file){if(cache.has(file))return Promise.resolve(cache.get(file));if(pending.has(file))return pending.get(file).promise;let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});pending.set(file,{promise,resolve,reject});const script=document.createElement('script');script.src=file;script.dataset.key=file;script.async=true;script.onerror=()=>{pending.delete(file);script.remove();reject(Error('分页面加载失败，请刷新重试'));};script.onload=()=>script.remove();document.head.appendChild(script);return promise;}
const fmt = n => {
  if (n >= 1e8) return (n / 1e8).toFixed(2) + '亿';
  if (n >= 1e4) return (n / 1e4).toFixed(n >= 1e6 ? 0 : 1) + '万';
  return String(n || 0);
};
const date=d=>d?d.slice(0,4)+'.'+d.slice(4,6)+'.'+d.slice(6,8):'日期待补';
function card(record) {
  const {bvid, dur, title, owner, view, admitted_on: admitted, first_seen: seen} = record;
  const saved = status(reviews[bvid]) === 'confirmed';
  const pic = /^(https?:\/\/|assets\/(?:selected-)?covers\/BV[0-9A-Za-z]{10}\.webp$)/.test(record.pic || '')
    ? record.pic.replace(/^http:/, 'https:') : '';
  const time = Math.floor((dur || 0) / 60) + ':' + String((dur || 0) % 60).padStart(2, '0');
  const url = 'https://www.bilibili.com/video/' + bvid;
  const cardDate = admitted ? (tab === 'daily' && !query ? '' : date(admitted)) : '发现于 ' + date(seen);
  return `<article class="card">
    <a class="cover" href="${url}" target="_blank" rel="noopener noreferrer" aria-label="${esc(title)}">
      ${pic ? `<img src="${esc(pic)}" loading="lazy" decoding="async" referrerpolicy="no-referrer" width="480" height="300" alt="">` : ''}
      ${saved ? '<span class="corner">已认可</span>' : ''}<span class="duration">${time}</span>
    </a>
    <a class="card-title" href="${url}" target="_blank" rel="noopener noreferrer">${esc(title)}</a>
    <div class="card-meta"><span class="owner">${esc(owner || '作者见原视频')}</span><span>${fmt(view)} 播放</span></div>
    <div class="card-actions"><span>${cardDate}</span><button data-review="${bvid}">${saved ? '修改标注' : admitted ? '收录笔记' : '记下感受'}</button></div>
  </article>`;
}

const emptySearch = `<div class="empty search-empty">
  <svg viewBox="0 0 116 82" aria-hidden="true">
    <ellipse cx="56" cy="73" rx="48" ry="6" fill="#21192060"/>
    <path d="M14 26 38 11 104 22 85 36Z" fill="#cbaa85" stroke="#604737" stroke-linejoin="round"/>
    <path d="M85 36 104 22 101 59 82 73Z" fill="#927256" stroke="#604737" stroke-linejoin="round"/>
    <path d="M14 26 85 36 82 73 17 62Z" fill="#b9906b" stroke="#604737" stroke-linejoin="round"/>
    <path d="M52 15 63 17 43 30 32 29Z" fill="#ead2aa" opacity=".75"/>
    <path d="M42 18 93 27" stroke="#73543d" stroke-width=".8"/>
    <path d="M91 41 97 37" stroke="#3b2926" stroke-width="3" stroke-linecap="round"/>
    <text x="50" y="53" text-anchor="middle" transform="rotate(9 50 53)" fill="#4b312a" font-size="9" font-weight="600">完熟マンゴー</text>
  </svg>
  <p role="status">没找到匹配的作品</p>
  <button type="button" data-clear-search>清空搜索</button>
</div>`;

function show(rows, n) {
  currentRows = rows;
  total = n;
  $('grid').innerHTML = rows.map(card).join('') ||
    (BOOT.curated && query ? emptySearch : '<div class="empty">暂无作品。</div>');
  $('count').textContent = n.toLocaleString() + (BOOT.curated ? ' 部' : ' 条');
  $('page-label').textContent = (page + 1) + ' / ' + Math.max(1, Math.ceil(n / 24));
  $('prev').disabled = page === 0;
  $('next').disabled = (page + 1) * 24 >= n;
  const titles = {
    daily: BOOT.curated ? '本期入选' : '当期目录',
    archive: BOOT.curated ? '全部入选' : '全部探索',
    saved: '我的认可'
  };
  $('section-title').textContent = query ? '搜索结果' : titles[tab];
  $('section-sub').textContent = query ? '「' + query + '」' : tab === 'daily' && activeDay ? date(activeDay) : '';
  document.querySelectorAll('[data-tab]').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
}
let searchResolvers=new Map();
function workerSearch(args){if(location.protocol==='file:')return Promise.reject(Error('全库搜索请使用网页地址，或运行 run_review.ps1。'));if(!worker){worker=new Worker(BOOT.worker);worker.onmessage=({data})=>{const p=searchResolvers.get(data.id);if(!p)return;searchResolvers.delete(data.id);data.error?p.reject(Error(data.error)):p.resolve(data);};worker.onerror=()=>{for(const p of searchResolvers.values())p.reject(Error('搜索加载失败，请刷新重试'));searchResolvers.clear();worker.terminate();worker=null;};}const id=++workerSearch.id;return new Promise((resolve,reject)=>{searchResolvers.set(id,{resolve,reject});worker.postMessage({...args,id});});}workerSearch.id=0;
async function render(){const my=++token;$('message').textContent='';try{if(query||tab==='saved'){const ids=tab==='saved'&&!query?Object.keys(reviews).filter(b=>status(reviews[b])==='confirmed'):null;if(ids?.length===0){show([],0);return;}$('message').textContent='正在后台查找，不影响页面浏览…';const result=await workerSearch({query,ids,offset:page*24});if(my!==token)return;$('message').textContent='';show(result.rows.map(unpack),result.total);return;}const stream=BOOT.streams[tab==='daily'&&activeDay!==BOOT.latest_day?'day:'+activeDay:tab];if(!stream||stream.count===0){show([],0);return;}const absolute=page*24,index=Math.floor(absolute/BOOT.chunkSize),offset=absolute%BOOT.chunkSize;const values=await chunk(stream.chunks[index]);if(my!==token)return;show(values.slice(offset,offset+24).map(unpack),stream.count);}catch(e){if(my===token)$('message').textContent=e.message;}}
function persist(){try{localStorage.setItem(storageKey,JSON.stringify(documentForExport()));}catch(e){$('message').textContent='浏览器保存失败，请导出标注备份。';}}
function documentForExport(){return {schema:SCHEMA,profile_id:PROFILE,catalog_id:BOOT.catalog_id,experiment_id:BOOT.experiment_id,reviews};}
function remember(){history.push(JSON.stringify(reviews));if(history.length>30)history.shift();}
function openReview(b){selected=currentRows.find(r=>r.bvid===b);if(!selected)return;const r=reviews[b]||{};$('review-title').textContent=selected.title;$('review-note').textContent=selected.review_note?(selected.review_basis+' · '+selected.review_note):'制作与共鸣各至少2分，并认可表达本身，才加入“我的认可”。';for(const k of ['craft','resonance','reason','evidence'])$(k).value=r[k]??'';$('watched').checked=r.watched===true;$('review-dialog').showModal();}
$('grid').addEventListener('click', event => {
  const review = event.target.closest('[data-review]');
  if (review) openReview(review.dataset.review);
  if (event.target.closest('[data-clear-search]')) {
    clearTimeout(searchTimer);
    query = $('search').value = '';
    page = 0;
    $('search').focus();
    render();
  }
});
$('review-form').addEventListener('submit',e=>{e.preventDefault();if(!$('review-form').reportValidity())return;remember();reviews[selected.bvid]={craft:Number($('craft').value),resonance:Number($('resonance').value),reason:$('reason').value,evidence:$('evidence').value,watched:$('watched').checked};persist();$('review-dialog').close();show(currentRows,total);});
$('close-review').addEventListener('click',()=>$('review-dialog').close());$('clear-review').addEventListener('click',()=>{remember();delete reviews[selected.bvid];persist();$('review-dialog').close();if(tab==='saved')render();else show(currentRows,total);});
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>{tab=b.dataset.tab;if(tab==='daily'&&BOOT.latest_day){activeDay=BOOT.latest_day;calendarMonth=activeDay.slice(0,6);paintCalendar();}page=0;query='';$('search').value='';clearTimeout(searchTimer);render();}));
$('search').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{query=$('search').value.trim();page=0;render();},250);});
function changePage(step) {
  const next = page + step;
  if (next < 0 || next * 24 >= total) return;
  page = next;
  render().then(() => window.scrollTo(0, 0));
}
$('prev').addEventListener('click', () => changePage(-1));
$('next').addEventListener('click', () => changePage(1));
$('export').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(documentForExport(),null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='制作与共鸣标注.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('import').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{const clean=validate(JSON.parse(await file.text()));remember();Object.assign(reviews,clean);persist();await render();$('message').textContent='已导入 '+Object.keys(clean).length+' 条标注。';}catch(error){$('message').textContent='导入失败：'+error.message;}e.target.value='';});
$('undo').addEventListener('click',()=>{if(!history.length){$('message').textContent='暂无可撤销的判断。';return;}reviews=Object.assign(Object.create(null),JSON.parse(history.pop()));persist();render();});
$('updated').textContent = '更新 ' + BOOT.generated_at.slice(0, 16);
$('collection-note').textContent = BOOT.collection
  ? '最近采集完成于 ' + date(BOOT.collection.finished_at.slice(0, 8)) + '，新发现热门 ' + BOOT.collection.new_videos + ' 条。'
  : '本期使用已有采集数据。';
if (!BOOT.curated) {
  $('search').setAttribute?.('aria-label', '搜索样本目录');
}
show(BOOT.initial.map(unpack),BOOT.streams.daily.count);

