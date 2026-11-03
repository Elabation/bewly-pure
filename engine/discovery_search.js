let catalogPromise;
function catalog(){
 if(!catalogPromise)catalogPromise=fetch(INDEX).then(r=>{if(!r.ok)throw Error('搜索索引加载失败');return r.json();}).then(rows=>rows.map(row=>({row,text:(row[0]+' '+row[1]+' '+row[2]).normalize('NFKC').toLowerCase()})));
 return catalogPromise;
}
onmessage=async({data})=>{
 try{
  const entries=await catalog(),q=(data.query||'').normalize('NFKC').trim().toLowerCase(),ids=data.ids?new Set(data.ids):null;
  const matches=entries.filter(x=>ids?ids.has(x.row[0]):x.text.includes(q));
  postMessage({id:data.id,total:matches.length,rows:matches.slice(data.offset||0,(data.offset||0)+24).map(x=>x.row)});
 }catch(e){postMessage({id:data.id,error:e.message});}
};
