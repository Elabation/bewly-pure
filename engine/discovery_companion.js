// Calendar, a scroll-responsive cover, and the turntable.
const calendarDates=Object.keys(BOOT.calendar||{}).sort();
const bandDates = {
  '0221': ['后藤一里生日', 'hitori'],
  '0421': ['喜多郁代生日', 'kita'],
  '0529': ['伊地知虹夏生日', 'nijika'],
  '0918': ['山田凉生日', 'ryo'],
  '1225': ['首张专辑数字发行纪念日', 'hitori']
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
 const dates = Object.entries(bandDates).sort();
 const monthEvent = dates.find(([day]) => day.slice(0, 2) === calendarMonth.slice(4));
 const upcoming = dates.find(([day]) => day.slice(0, 2) > calendarMonth.slice(4)) || dates[0];
 const occasion = $('calendar-occasion');
 occasion.hidden = false;
 occasion.innerHTML = monthEvent
   ? `${Number(monthEvent[0].slice(2))} 日 · ${monthEvent[1][0]}`
   : `<button data-occasion-month="${upcoming[0].slice(0, 2)}">${upcoming[0].slice(0, 2)}/${upcoming[0].slice(2)} · ${upcoming[1][0]}</button>`;
 const buildYear = Number(BOOT.generated_at.slice(0, 4));
 const firstYear = calendarDates.length ? Number(calendarDates[0].slice(0, 4)) : buildYear;
 $('calendar-prev').disabled = calendarMonth <= Math.min(buildYear - 1, firstYear) + '01';
 $('calendar-next').disabled = calendarMonth >= (buildYear + 1) + '12';
}
function moveMonth(step){const y=Number(calendarMonth.slice(0,4)),m=Number(calendarMonth.slice(4,6)),d=new Date(y,m-1+step,1);calendarMonth=d.getFullYear()+String(d.getMonth()+1).padStart(2,'0');paintCalendar();}
$('calendar-prev').addEventListener('click',()=>moveMonth(-1));$('calendar-next').addEventListener('click',()=>moveMonth(1));
$('calendar-occasion').addEventListener('click', event => {
  const month = event.target.closest('[data-occasion-month]')?.dataset.occasionMonth;
  if (!month) return;
  calendarMonth = calendarMonth.slice(0, 4) + month;
  paintCalendar();
});
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

const audio = $('music-audio');
const deck = $('turntable');
const trackList = $('music-track');
const musicTracks = BOOT.music || [];
let trackIndex = 0;

const musicTime = seconds => Number.isFinite(seconds)
  ? Math.floor(seconds / 60) + ':' + String(Math.floor(seconds % 60)).padStart(2, '0')
  : '—';

function musicList() {
  const groups = new Map();
  musicTracks.forEach((track, index) => {
    const items = groups.get(track.side) || [];
    items.push(`<li><button type="button" data-track="${index}" aria-current="false"><span>${esc(track.number)}</span>${esc(track.title)}</button></li>`);
    groups.set(track.side, items);
  });
  trackList.innerHTML = Array.from(groups, ([side, items]) =>
    `<section class="track-side track-side-${esc(side.toLowerCase())}"><h4>${esc(side)} 面</h4><ul>${items.join('')}</ul></section>`
  ).join('');
  $('music-count').textContent = String(musicTracks.length).padStart(2, '0');
}

function paintTrack(track) {
  $('music-title').textContent = track.title;
  const edition = track.album === track.title ? '单曲' : track.album;
  $('music-album').textContent = edition + ' · ' + track.side + track.number;
  deck.dataset.side = track.side;
  $('deck-side').textContent = track.side + track.number;
  for (const id of ['record-art', 'sleeve-art']) {
    const image = $(id);
    image.hidden = !track.art;
    if (track.art && image.getAttribute('src') !== track.art) image.src = track.art;
  }
  for (const button of trackList.querySelectorAll('[data-track]')) {
    button.setAttribute('aria-current', String(Number(button.dataset.track) === trackIndex));
  }
}

function paintTransport(active) {
  $('music-play').textContent = active ? 'Ⅱ' : '▶';
  $('music-play').setAttribute('aria-label', active ? '暂停' : '播放');
}

function parkArm() {
  deck.classList.remove('playing', 'arm-down', 'arm-cued');
  paintTransport(false);
}

function paintProgress() {
  const duration = audio.duration;
  const fraction = Number.isFinite(duration) && duration > 0
    ? Math.min(1, audio.currentTime / duration) : 0;
  $('music-elapsed').textContent = musicTime(audio.currentTime);
  $('music-seek').value = String(fraction * 1000);
  deck.style.setProperty('--arm-angle', (18 + fraction * 10) + 'deg');
}

function startMusic() {
  audio.play().catch(error => {
    if (error.name === 'AbortError') return;
    parkArm();
    $('music-message').textContent = '音频未能播放，请再试一次。';
  });
}

function loadTrack(index, play = false) {
  if (!musicTracks.length) return;
  audio.pause();
  parkArm();
  trackIndex = (index + musicTracks.length) % musicTracks.length;
  const track = musicTracks[trackIndex];
  audio.src = track.src;
  paintTrack(track);
  $('music-message').textContent = '';
  $('music-seek').value = '0';
  $('music-seek').disabled = true;
  $('music-elapsed').textContent = '0:00';
  $('music-duration').textContent = '—';
  deck.style.setProperty('--arm-angle', '18deg');
  if (play) startMusic();
}

audio.addEventListener('play', () => {
  paintTransport(true);
  deck.classList.add('arm-cued');
});
audio.addEventListener('playing', () => {
  deck.classList.add('playing', 'arm-cued', 'arm-down');
  $('music-message').textContent = '';
});
audio.addEventListener('waiting', () => {
  if (audio.paused) return;
  deck.classList.remove('playing');
  $('music-message').textContent = '正在缓冲…';
});
audio.addEventListener('pause', () => {
  if (!audio.paused) return;
  parkArm();
  $('music-message').textContent = '';
});
audio.addEventListener('error', () => {
  parkArm();
  $('music-message').textContent = '音频加载失败，请重试或换一首。';
});
audio.addEventListener('loadedmetadata', () => {
  $('music-duration').textContent = musicTime(audio.duration);
  $('music-seek').disabled = !Number.isFinite(audio.duration);
  paintProgress();
});
audio.addEventListener('timeupdate', paintProgress);
audio.addEventListener('ended', () => loadTrack(trackIndex + 1, true));
audio.volume = .25;

$('music-play').addEventListener('click', () => {
  if (!musicTracks.length) return;
  if (!audio.paused) {
    audio.pause();
  } else if (!audio.src || audio.error) {
    loadTrack(trackIndex, true);
  } else {
    startMusic();
  }
});
$('music-prev').addEventListener('click', () => loadTrack(trackIndex - 1, !audio.paused));
$('music-next').addEventListener('click', () => loadTrack(trackIndex + 1, !audio.paused));
trackList.addEventListener('click', event => {
  const button = event.target.closest('[data-track]');
  if (!button) return;
  const index = Number(button.dataset.track);
  if (index !== trackIndex || !audio.src || audio.error) loadTrack(index, true);
  else if (audio.paused) startMusic();
});
$('music-seek').addEventListener('input', () => {
  if (Number.isFinite(audio.duration) && audio.duration > 0) {
    audio.currentTime = Number($('music-seek').value) / 1000 * audio.duration;
    paintProgress();
  }
});
$('music-volume').addEventListener('input', () => { audio.volume = Number($('music-volume').value); });
musicList();
if (musicTracks.length) {
  paintTrack(musicTracks[0]);
  $('music-seek').disabled = true;
} else {
  $('music-queue').hidden = true;
  for (const id of ['music-prev', 'music-play', 'music-next', 'music-seek', 'music-volume']) $(id).disabled = true;
  $('music-message').textContent = '暂无曲目';
}
