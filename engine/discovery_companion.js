// Calendar, a scroll-responsive cover, and the turntable.
const calendarDates=Object.keys(BOOT.calendar||{}).sort();
const bandDates = {
  '0221': ['后藤一里生日', 'hitori', 'https://bocchi.rocks/birthday/hitori.html'],
  '0421': ['喜多郁代生日', 'kita', 'https://bocchi.rocks/kessokuband/info/?article_id=60509'],
  '0529': ['伊地知虹夏生日', 'nijika', 'https://bocchi.rocks/kessokuband/info/?article_id=60699'],
  '0918': ['山田凉生日', 'ryo', 'https://bocchi.rocks/kessokuband/info/?article_id=61533'],
  '1225': ['首张专辑数字发行纪念日', 'hitori', 'https://mora.jp/package/43000100/SVWC70613B00Z_48/']
};
let calendarMonth=(activeDay||BOOT.generated_at.slice(0,7).replace('-','')).slice(0,6);
const calendarUnit = BOOT.curated ? '部入选' : '条候选';
function paintCalendar(){
 const year=Number(calendarMonth.slice(0,4)),month=Number(calendarMonth.slice(4,6)),offset=(new Date(year,month-1,1).getDay()+6)%7,days=new Date(year,month,0).getDate();
 $('calendar-month').textContent=year+' / '+String(month).padStart(2,'0');
 let html=Array.from({length:offset},()=>'<span class="calendar-blank"></span>').join('');
 for (let day = 1; day <= days; day++) {
   const key = calendarMonth + String(day).padStart(2, '0');
   const count = (BOOT.calendar || {})[key] || 0;
   const occasion = bandDates[key.slice(4)];
   const label = count + calendarUnit + (occasion ? ' · ' + occasion[0] : '');
   const classes = [key === activeDay ? 'chosen' : '', occasion ? 'band-date ' + occasion[1] : ''].join(' ');
   html += `<button data-day="${key}" ${count ? '' : 'disabled'} class="${classes}" aria-pressed="${key === activeDay}" aria-label="${year}年${month}月${day}日，${label}" title="${label}">${day}</button>`;
 }
 $('calendar-days').innerHTML=html;$('calendar-selected-date').textContent=activeDay?date(activeDay):'暂无上架';$('calendar-selected-count').textContent=((BOOT.calendar||{})[activeDay]||0)+' '+calendarUnit;
 const monthEvent = Object.entries(bandDates).find(([day]) => day.slice(0, 2) === calendarMonth.slice(4));
 $('calendar-occasion').hidden = !monthEvent;
 $('calendar-occasion').innerHTML = monthEvent
   ? `<a href="${monthEvent[1][2]}" target="_blank" rel="noopener">${Number(monthEvent[0].slice(2))} 日 · ${monthEvent[1][0]}</a>` : '';
 const buildYear = Number(BOOT.generated_at.slice(0, 4));
 const firstYear = calendarDates.length ? Number(calendarDates[0].slice(0, 4)) : buildYear;
 $('calendar-prev').disabled = calendarMonth <= Math.min(buildYear - 1, firstYear) + '01';
 $('calendar-next').disabled = calendarMonth >= (buildYear + 1) + '12';
}
function moveMonth(step){const y=Number(calendarMonth.slice(0,4)),m=Number(calendarMonth.slice(4,6)),d=new Date(y,m-1+step,1);calendarMonth=d.getFullYear()+String(d.getMonth()+1).padStart(2,'0');paintCalendar();}
$('calendar-prev').addEventListener('click',()=>moveMonth(-1));$('calendar-next').addEventListener('click',()=>moveMonth(1));
$('calendar-days').addEventListener('click',e=>{const b=e.target.closest('[data-day]');if(!b||b.disabled)return;activeDay=b.dataset.day;tab='daily';page=0;query='';$('search').value='';clearTimeout(searchTimer);paintCalendar();render();});
$('calendar-today').addEventListener('click',()=>{if(!BOOT.latest_day)return;activeDay=BOOT.latest_day;calendarMonth=activeDay.slice(0,6);tab='daily';page=0;query='';$('search').value='';clearTimeout(searchTimer);paintCalendar();render();});
paintCalendar();

const hero = $('interactive-hero');
const expandThreshold = 44;
let wheelPull = 0;
function resetHero() {
  if (!wheelPull) return;
  wheelPull = 0;
  hero.style.setProperty('--pull', '0');
}
window.addEventListener('wheel', event => {
  if (event.ctrlKey || event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
  if (event.deltaY > 0) {
    resetHero();
    return;
  }
  if (event.deltaY >= 0 || window.scrollY > 1 || wheelPull >= expandThreshold) return;
  const units = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1;
  wheelPull = Math.min(expandThreshold, wheelPull - event.deltaY * units);
  const stretch = wheelPull === expandThreshold ? 1 : .48 * wheelPull / expandThreshold;
  hero.style.setProperty('--pull', String(stretch));
}, {passive: true});
window.addEventListener('scroll', () => {
  if (window.scrollY > 1) resetHero();
}, {passive: true});
$('jump-end').addEventListener('click', () => {
  resetHero();
  window.scrollTo(0, document.documentElement.scrollHeight);
});

const audio=$('music-audio'),officialTracks=BOOT.music||[];let musicTracks=[...officialTracks],trackIndex=0,localUrls=[],fallbackTried=false;
const musicTime=n=>Number.isFinite(n)?Math.floor(n/60)+':'+String(Math.floor(n%60)).padStart(2,'0'):'—';
function musicList() {
  $('music-track').innerHTML = musicTracks.map((track, index) =>
    `<option value="${index}">${esc(track.title)}</option>`).join('');
  $('music-track').value = String(trackIndex);
}

function paintTrack(track) {
  if (!track) return;
  $('music-title').textContent = track.title;
  $('music-album').textContent = track.album ? track.album + ' · ' + track.number : '本地音频';
  $('music-kind').textContent = track.fullVideo ? '完整曲目' : track.kind || '本地音频';
  $('music-play').textContent = '▶';
  $('music-play').setAttribute('aria-label', track.fullVideo ? '播放完整曲目' : '播放');
  $('music-play').title = track.fullVideo ? '播放完整曲目' : '播放';
  $('music-preview').hidden = !track.fullVideo;
  $('music-preview').textContent = '试听';
  $('music-official').hidden = Boolean(track.url);
  for (const id of ['record-art', 'sleeve-art']) {
    const art = $(id);
    art.hidden = !track.art;
    if (track.art) art.src = track.art;
  }
  $('music-download').hidden = !track.download;
  if (track.download) $('music-download').href = track.download;
}

function loadTrack(index, play = false) {
  if (!musicTracks.length) {
    $('music-message').textContent = '可以选择本地音频播放。';
    return;
  }
  audio.pause();
  fallbackTried = false;
  trackIndex = (index + musicTracks.length) % musicTracks.length;
  const track = musicTracks[trackIndex];
  audio.src = track.src;
  $('music-track').value = String(trackIndex);
  paintTrack(track);
  $('music-message').textContent = '';
  $('music-seek').value = '0';
  $('music-elapsed').textContent = '0:00';
  $('music-duration').textContent = '—';
  $('turntable').style.setProperty('--arm-angle', '26deg');
  if (play) startMusic();
}
function startMusic(){audio.play().catch(()=>{$('music-message').textContent='试听暂时无法连接，可选择本地音频或打开完整曲目。';});}
function paintTransport(playing) {
  if (musicTracks[trackIndex]?.fullVideo) {
    $('music-preview').textContent = playing ? '暂停试听' : '试听';
    return;
  }
  $('music-play').textContent = playing ? 'Ⅱ' : '▶';
  $('music-play').setAttribute('aria-label', playing ? '暂停' : '播放');
}
function transportState(playing) {
  $('turntable').classList.toggle('playing', playing);
  paintTransport(playing);
}
audio.addEventListener('play',()=>{paintTransport(true);$('music-message').textContent='正在连接音源…';});
audio.addEventListener('playing',()=>{transportState(true);$('music-message').textContent='';});
audio.addEventListener('waiting',()=>{$('turntable').classList.remove('playing');$('music-message').textContent='正在缓冲…';});
audio.addEventListener('pause',()=>transportState(false));audio.addEventListener('error',()=>{transportState(false);const backup=musicTracks[trackIndex]?.fallbackSrc;if(backup&&!fallbackTried){fallbackTried=true;audio.src=backup;startMusic();return;}$('music-message').textContent='音频加载失败，可切换曲目或选择本地音频。';});
audio.addEventListener('loadedmetadata',()=>{$('music-duration').textContent=musicTime(audio.duration);});
audio.addEventListener('timeupdate', () => {
  const fraction = audio.duration > 0 ? Math.min(1, audio.currentTime / audio.duration) : 0;
  $('music-elapsed').textContent = musicTime(audio.currentTime);
  $('music-seek').value = String(fraction * 1000);
  $('turntable').style.setProperty('--arm-angle', (26 + fraction * 10) + 'deg');
});
audio.addEventListener('ended',()=>loadTrack(trackIndex+1,true));audio.volume=.25;
function toggleAudio() {
  if (!audio.src) loadTrack(trackIndex, false);
  if (audio.paused) startMusic();
  else audio.pause();
}

const fullPlayer = $('full-player');
function openFullTrack(track) {
  audio.pause();
  const frame = document.createElement('iframe');
  frame.title = track.title + ' · 完整曲目';
  frame.referrerPolicy = 'strict-origin-when-cross-origin';
  frame.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
  frame.src = 'https://www.youtube-nocookie.com/embed/' + track.fullVideo + '?autoplay=1&playsinline=1';
  $('full-track-title').textContent = track.title;
  $('full-track-link').href = 'https://www.youtube.com/watch?v=' + track.fullVideo;
  $('full-player-frame').replaceChildren(frame);
  fullPlayer.showModal();
}
$('close-full-player').addEventListener('click', () => fullPlayer.close());
fullPlayer.addEventListener('close', () => $('full-player-frame').replaceChildren());
$('music-play').addEventListener('click', () => {
  const track = musicTracks[trackIndex];
  if (track?.fullVideo) openFullTrack(track);
  else toggleAudio();
});
$('music-preview').addEventListener('click', toggleAudio);
$('music-prev').addEventListener('click',()=>loadTrack(trackIndex-1,!audio.paused));$('music-next').addEventListener('click',()=>loadTrack(trackIndex+1,!audio.paused));
$('music-track').addEventListener('change',()=>loadTrack(Number($('music-track').value),!audio.paused));
$('music-seek').addEventListener('input',()=>{if(Number.isFinite(audio.duration)&&audio.duration>0)audio.currentTime=Number($('music-seek').value)/1000*audio.duration;});
$('music-volume').addEventListener('input',()=>{audio.volume=Number($('music-volume').value);});
$('music-local').addEventListener('change',e=>{const files=Array.from(e.target.files||[]);if(!files.length)return;audio.pause();for(const url of localUrls)URL.revokeObjectURL(url);localUrls=[];musicTracks=files.map(file=>{const src=URL.createObjectURL(file);localUrls.push(src);return {title:file.name.replace(/\.[^.]+$/,''),src,kind:'本地音频'};});trackIndex=0;musicList();loadTrack(0,false);});
$('music-official').addEventListener('click',()=>{audio.pause();musicTracks=[...officialTracks];trackIndex=0;musicList();loadTrack(0,false);for(const url of localUrls)URL.revokeObjectURL(url);localUrls=[];});
musicList();
paintTrack(officialTracks[0]);
