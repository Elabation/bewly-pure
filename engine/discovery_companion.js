// Calendar, resizable cover and a real HTMLAudioElement turntable.
const calendarDates=Object.keys(BOOT.calendar||{}).sort();
let calendarMonth=(activeDay||'20261101').slice(0,6);
function paintCalendar(){
 const year=Number(calendarMonth.slice(0,4)),month=Number(calendarMonth.slice(4,6)),offset=(new Date(year,month-1,1).getDay()+6)%7,days=new Date(year,month,0).getDate();
 $('calendar-month').textContent=year+' / '+String(month).padStart(2,'0');
 let html=Array.from({length:offset},()=>'<span class="calendar-blank"></span>').join('');
 for(let day=1;day<=days;day++){const key=calendarMonth+String(day).padStart(2,'0'),count=(BOOT.calendar||{})[key]||0;html+=`<button data-day="${key}" ${count?'':'disabled'} class="${key===activeDay?'chosen':''}" aria-label="${year}年${month}月${day}日，${count}条候选" title="${count}条候选">${day}</button>`;}
 $('calendar-days').innerHTML=html;$('calendar-selected-date').textContent=date(activeDay);$('calendar-selected-count').textContent=((BOOT.calendar||{})[activeDay]||0)+' 条候选';
 $('calendar-prev').disabled=!calendarDates.length||calendarMonth<=calendarDates[0].slice(0,6);$('calendar-next').disabled=!calendarDates.length||calendarMonth>=calendarDates[calendarDates.length-1].slice(0,6);
}
function moveMonth(step){const y=Number(calendarMonth.slice(0,4)),m=Number(calendarMonth.slice(4,6)),d=new Date(y,m-1+step,1);calendarMonth=d.getFullYear()+String(d.getMonth()+1).padStart(2,'0');paintCalendar();}
$('calendar-prev').addEventListener('click',()=>moveMonth(-1));$('calendar-next').addEventListener('click',()=>moveMonth(1));
$('calendar-days').addEventListener('click',e=>{const b=e.target.closest('[data-day]');if(!b||b.disabled)return;activeDay=b.dataset.day;tab='daily';page=0;query='';$('search').value='';paintCalendar();render();});
$('calendar-today').addEventListener('click',()=>{activeDay=BOOT.latest_day;calendarMonth=activeDay.slice(0,6);tab='daily';page=0;query='';$('search').value='';paintCalendar();render();});
paintCalendar();

const hero=$('interactive-hero'),grip=$('hero-grip');let heroStart,heroInitial;
function setHeroHeight(h){const value=Math.max(96,Math.min(440,h));hero.style.setProperty('--hero-height',value+'px');$('hero-toggle').textContent=value<=110?'展开页头 ↓':'收起页头 ↑';$('hero-toggle').setAttribute('aria-expanded',String(value>110));}
grip.addEventListener('pointerdown',e=>{heroStart=e.clientY;heroInitial=hero.getBoundingClientRect().height;hero.classList.add('dragging');grip.setPointerCapture(e.pointerId);});
grip.addEventListener('pointermove',e=>{if(heroStart==null)return;setHeroHeight(heroInitial+e.clientY-heroStart);});
function endHero(){heroStart=null;hero.classList.remove('dragging');}
grip.addEventListener('pointerup',endHero);grip.addEventListener('pointercancel',endHero);
grip.addEventListener('keydown',e=>{if(e.key==='ArrowUp'||e.key==='ArrowDown'){e.preventDefault();setHeroHeight(hero.getBoundingClientRect().height+(e.key==='ArrowUp'?-40:40));}});
$('hero-toggle').addEventListener('click',()=>setHeroHeight(hero.getBoundingClientRect().height>110?96:290));

const audio=$('music-audio'),officialTracks=BOOT.music||[];let musicTracks=[...officialTracks],trackIndex=0,localUrls=[],fallbackTried=false;
const musicTime=n=>Number.isFinite(n)?Math.floor(n/60)+':'+String(Math.floor(n%60)).padStart(2,'0'):'—';
function musicList(){$('music-track').innerHTML=musicTracks.map((t,i)=>`<option value="${i}">${esc(t.title)}</option>`).join('');$('music-track').value=String(trackIndex);}
function loadTrack(index,play=false){if(!musicTracks.length){$('music-message').textContent='可以选择本地音频播放。';return;}audio.pause();fallbackTried=false;trackIndex=(index+musicTracks.length)%musicTracks.length;const track=musicTracks[trackIndex];audio.src=track.src;$('music-track').value=String(trackIndex);$('music-kind').textContent=track.kind||'本地音频';$('music-source').hidden=!track.url;$('music-source').href=track.url||'https://open.spotify.com/album/5ZGzGGNAB6U7QlKpdaMu0d';$('music-message').textContent='';$('music-seek').value='0';$('music-elapsed').textContent='0:00';$('music-duration').textContent='—';if(play)startMusic();}
function startMusic(){audio.play().catch(()=>{$('music-message').textContent='试听暂时无法连接，可选择本地音频或打开完整曲目。';});}
function transportState(playing){$('turntable').classList.toggle('playing',playing);$('music-play').textContent=playing?'Ⅱ':'▶';$('music-play').setAttribute('aria-label',playing?'暂停':'播放');}
audio.addEventListener('play',()=>{$('music-play').textContent='Ⅱ';$('music-play').setAttribute('aria-label','暂停');$('music-message').textContent='正在连接试听…';});
audio.addEventListener('playing',()=>{transportState(true);$('music-message').textContent='';});
audio.addEventListener('waiting',()=>{$('turntable').classList.remove('playing');$('music-message').textContent='正在缓冲…';});
audio.addEventListener('pause',()=>transportState(false));audio.addEventListener('error',()=>{transportState(false);const backup=musicTracks[trackIndex]?.fallbackSrc;if(backup&&!fallbackTried){fallbackTried=true;audio.src=backup;startMusic();return;}$('music-message').textContent='音频加载失败，可切换曲目或选择本地音频。';});
audio.addEventListener('loadedmetadata',()=>{$('music-duration').textContent=musicTime(audio.duration);});
audio.addEventListener('timeupdate',()=>{$('music-elapsed').textContent=musicTime(audio.currentTime);$('music-seek').value=Number.isFinite(audio.duration)&&audio.duration>0?String(audio.currentTime/audio.duration*1000):'0';});
audio.addEventListener('ended',()=>loadTrack(trackIndex+1,true));audio.volume=.25;
$('music-play').addEventListener('click',()=>{if(!audio.src)loadTrack(trackIndex,false);if(audio.paused)startMusic();else audio.pause();});
$('music-prev').addEventListener('click',()=>loadTrack(trackIndex-1,!audio.paused));$('music-next').addEventListener('click',()=>loadTrack(trackIndex+1,!audio.paused));
$('music-track').addEventListener('change',()=>loadTrack(Number($('music-track').value),!audio.paused));
$('music-seek').addEventListener('input',()=>{if(Number.isFinite(audio.duration)&&audio.duration>0)audio.currentTime=Number($('music-seek').value)/1000*audio.duration;});
$('music-volume').addEventListener('input',()=>{audio.volume=Number($('music-volume').value);});
$('music-local').addEventListener('change',e=>{const files=Array.from(e.target.files||[]);if(!files.length)return;audio.pause();for(const url of localUrls)URL.revokeObjectURL(url);localUrls=[];musicTracks=files.map(file=>{const src=URL.createObjectURL(file);localUrls.push(src);return {title:file.name.replace(/\.[^.]+$/,''),src,kind:'本地音频'};});trackIndex=0;musicList();loadTrack(0,false);});
$('music-official').addEventListener('click',()=>{audio.pause();musicTracks=[...officialTracks];trackIndex=0;musicList();loadTrack(0,false);for(const url of localUrls)URL.revokeObjectURL(url);localUrls=[];});
musicList();
if(officialTracks[0])$('music-source').href=officialTracks[0].url;
