const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function setup(companion=false){
 const nodes={},tabs=['daily','picks','archive','editorial','saved'].map(tab=>({dataset:{tab},classList:{toggle(){}},addEventListener(){}}));
 const el=id=>nodes[id]??=( {value:'',checked:false,hidden:false,innerHTML:'',textContent:'',dataset:{},listeners:{},addEventListener(k,v){this.listeners[k]=v;},showModal(){this.open=true;},close(){this.open=false;},reportValidity(){return true;}});
 const fields=['bvid','title','owner','pic','dur','pubdate','view','coin_percentile','first_seen','motive_cues','reference_n'];
 const rows=Array.from({length:96},(_,i)=>['BV'+String(i).padStart(10,'0'),'作品 '+i,'作者','','120',null,10000,.95,'20261103',[],100]);
 rows[0][1]='</script>作品';
 el('payload').textContent=JSON.stringify({fields,chunkSize:96,pageSize:24,initial:rows.slice(0,24),total:39664,latest_day:'20261103',generated_at:'2026-11-03 12:00',streams:{daily:{count:200,chunks:['data0.js','data1.js']},archive:{count:39664,chunks:['data0.js']}},editorial:{},editorial_rows:[],collection:null,worker:'search.js'});
 let workerCount=0,stored;
 const window={scrollY:0,innerHeight:720,listeners:{},scrollTo(x,y){this.scrollY=y;},addEventListener(k,v,options){this.listeners[k]={v,options};}};
 const context=vm.createContext({console,Set,Map,Array,Object,String,Number,JSON,Math,Blob,URL,setTimeout,clearTimeout,
  location:{protocol:'https:'},window,localStorage:{getItem(){return null;},setItem(k,v){stored=v;}},
  Worker:class{constructor(){workerCount++;}},
  document:{documentElement:{scrollHeight:2000},getElementById:el,querySelectorAll(){return tabs;},head:{appendChild(script){context.window.BiliDiscovery.receive(script.dataset.key,rows);script.onload();}},createElement(){return {dataset:{},remove(){},click(){}};}}});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'discovery_ui.js'),'utf8'),context);
 if(companion){
  context.Date=Date;
  vm.runInContext("BOOT.calendar={20261101:1,20261103:200};BOOT.streams['day:20261101']={count:1,chunks:['older.js']};BOOT.music=[{title:'青春コンプレックス',album:'結束バンド',side:'A',number:'01',src:'assets/music/tracks/a01.mp3'}];",context);
  for(const id of ['interactive-hero','turntable']){const node=el(id);node.classes=new Set();node.classList={add:(...keys)=>keys.forEach(k=>node.classes.add(k)),remove:(...keys)=>keys.forEach(k=>node.classes.delete(k))};}
  el('music-track').querySelectorAll=()=>[];
  for(const id of ['interactive-hero','turntable'])el(id).style={setProperty(k,v){this[k]=v;}};
  el('music-play').setAttribute=function(k,v){this[k]=v;};
  const audio=el('music-audio');audio.paused=true;audio.pause=()=>{audio.paused=true;audio.listeners.pause?.();};audio.play=()=>{audio.paused=false;audio.listeners.play?.();return Promise.resolve();};
  vm.runInContext(fs.readFileSync(path.join(__dirname,'discovery_companion.js'),'utf8'),context);
 }
 return {context,el,run:s=>vm.runInContext(s,context),workers:()=>workerCount,stored:()=>stored};
}
test('large catalog starts with 24 records and no search worker',()=>{const h=setup();assert.equal(h.run('currentRows.length'),24);assert.equal(h.workers(),0);assert.equal((h.el('grid').innerHTML.match(/class="card"/g)||[]).length,24);assert.doesNotMatch(h.el('grid').innerHTML,/featured/);});
test('pagination replaces records and returns to the very top',async()=>{const h=setup();h.run('window.scrollY=920');h.el('next').listeners.click();await new Promise(setImmediate);assert.equal(h.run('currentRows.length'),24);assert.equal(h.run('currentRows[0].bvid'),'BV0000000024');assert.equal((h.el('grid').innerHTML.match(/class="card"/g)||[]).length,24);assert.equal(h.run('window.scrollY'),0);});
test('unsafe titles are escaped',()=>{const h=setup();assert.match(h.el('grid').innerHTML,/&lt;\/script&gt;/);assert.doesNotMatch(h.el('grid').innerHTML,/<script>/);});
test('review dialog is not duplicated into every card',()=>{const h=setup();assert.doesNotMatch(h.el('grid').innerHTML,/<select|<textarea/);h.run("openReview('BV0000000004')");assert.equal(h.el('review-dialog').open,true);});
test('same craft/resonance standard survives new interface',()=>{const h=setup();assert.equal(h.run("status({watched:true,craft:3,resonance:3,reason:'effort_only',evidence:'辛苦'})"),'not_fit');assert.equal(h.run("status({watched:true,craft:3,resonance:2,reason:'craft_expression',evidence:'具体镜头'})"),'confirmed');});
test('search kernel runs independently and bounds results to one page',async()=>{let result;const rows=Array.from({length:40000},(_,i)=>['BV'+i,'音乐'+i,'作者']);const context=vm.createContext({Set,fetch:async()=>({ok:true,json:async()=>rows}),postMessage:r=>result=r});vm.runInContext("const INDEX='index.json';"+fs.readFileSync(path.join(__dirname,'discovery_search.js'),'utf8'),context);await context.onmessage({data:{id:1,query:'音乐',offset:24}});assert.equal(result.total,40000);assert.equal(result.rows.length,24);assert.equal(result.rows[0][1],'音乐24');});

test('calendar selection loads the older stream and resets to latest',async()=>{const h=setup(true);h.el('calendar-days').listeners.click({target:{closest:()=>({dataset:{day:'20261101'}})}});await new Promise(setImmediate);assert.equal(h.run('activeDay'),'20261101');assert.equal(h.run('total'),1);h.el('calendar-today').listeners.click();await new Promise(setImmediate);assert.equal(h.run('activeDay'),'20261103');assert.equal(h.run('total'),200);});

test('vinyl follows playback and the arm tracks the groove even through buffering',()=>{
 const h=setup(true),audio=h.el('music-audio'),deck=h.el('turntable');
 h.el('music-play').listeners.click();
 assert.equal(audio.src,'assets/music/tracks/a01.mp3');
 assert.equal(deck.classes.has('arm-cued'),true);
 assert.equal(deck.classes.has('playing'),false);
 audio.listeners.playing();
 assert.equal(deck.classes.has('playing'),true);
 assert.equal(deck.classes.has('arm-down'),true);
 audio.duration=200;audio.currentTime=100;audio.listeners.timeupdate();
 assert.equal(deck.style['--arm-angle'],'23deg');
 audio.listeners.waiting();
 assert.equal(deck.classes.has('playing'),false);
 assert.equal(deck.classes.has('arm-down'),true);
 audio.listeners.playing();
 h.el('music-play').listeners.click();
 assert.equal(audio.paused,true);
 assert.equal(deck.classes.size,0);
});

test('small top-edge wheel gestures expand the header, down resets and the wheel stays passive',()=>{
 const h=setup(true),wheel=h.context.window.listeners.wheel,style=h.el('interactive-hero').style;
 assert.equal(wheel.options.passive,true);
 wheel.v({deltaY:-16,deltaX:0,deltaMode:0});
 assert.ok(Number(style['--pull'])>0 && Number(style['--pull'])<0.5);
 wheel.v({deltaY:-30,deltaX:0,deltaMode:0});
 assert.equal(style['--pull'],'1');
 wheel.v({deltaY:12,deltaX:0,deltaMode:0});
 assert.equal(style['--pull'],'0');
 h.el('jump-end').listeners.click();
 assert.equal(h.run('window.scrollY'),2000);
 wheel.v({deltaY:-80,deltaX:0,deltaMode:0});
 assert.equal(style['--pull'],'0');
});
