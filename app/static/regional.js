const regionalData=new Map();let regionalSequence=0,trafficVisit=null;
function syncTrafficVisit(kind){
 if(kind!=='traffic'){trafficVisit=null;return;}
 const key=JSON.stringify([id,channel.latitude,channel.longitude,channel.traffic_radius_km]);
 if(!trafficVisit||trafficVisit.key!==key||trafficVisit.switchAt!==lastSwitch)trafficVisit={key,switchAt:lastSwitch,readyAt:null,data:null,pageSeconds:Math.max(5,channel.seconds||20),drawnPage:-1};
}
function trafficPageCount(data){return Math.max(1,Math.ceil((data?.items?.length||0)/3));}
function trafficPageSeconds(fallback){
 if(!trafficVisit?.data)return Infinity;
 return Math.max(0,(trafficVisit.readyAt-lastSwitch)/1000)+(trafficVisit.data.items.length?trafficPageCount(trafficVisit.data)*trafficVisit.pageSeconds:10);
}
function trafficCurrentPage(){return trafficVisit?.data?Math.min(trafficPageCount(trafficVisit.data)-1,Math.max(0,Math.floor((Date.now()-trafficVisit.readyAt)/1000/trafficVisit.pageSeconds))):0;}
function tickTraffic(){if(trafficVisit&&!trafficVisit.data&&Date.now()-trafficVisit.switchAt>25000)renderRegional('traffic',{items:[],status:'error',radius_km:channel.traffic_radius_km,source:'Verkehrsquelle',message:'Verkehrsquelle derzeit nicht verfügbar. Keine Entwarnung ableitbar.'});if(trafficVisit?.data&&$('content').dataset.page==='traffic'&&trafficVisit.drawnPage!==trafficCurrentPage())renderRegional('traffic',trafficVisit.data);}
function countryGraphic(data){
 const shape=data.map,points=data.places;if(!shape)return '<div class="notice">Keine passende Landesgrenze gefunden.</div>';
 const merc=lat=>Math.log(Math.tan(Math.PI/4+Math.max(-85,Math.min(85,lat))*Math.PI/360));
 const rings=shape.geometry.coordinates,all=rings.flat(),xs=all.map(p=>p[0]*Math.PI/180),ys=all.map(p=>merc(p[1]));
 const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys),scale=Math.min(840/Math.max(.000001,maxX-minX),360/Math.max(.000001,maxY-minY));
 const project=(lon,lat)=>[500+(lon*Math.PI/180-(minX+maxX)/2)*scale,207-(merc(lat)-(minY+maxY)/2)*scale];
 const path=rings.map(r=>r.map((p,i)=>{const [x,y]=project(...p);return `${i?'L':'M'}${x.toFixed(1)} ${y.toFixed(1)}`;}).join('')+'Z').join('');
 const occupied=[];
 const marks=points.map(p=>{
  const [ax,ay]=project(p.longitude,p.latitude),width=160,height=65;
  const candidates=[];
  for(let dy=-230;dy<=230;dy+=23)for(let dx=-300;dx<=300;dx+=25)candidates.push([dx,dy]);
  const distance=([dx,dy])=>{const x=Math.max(8,Math.min(832,ax+dx)),y=Math.max(8,Math.min(343,ay+dy));const ex=Math.max(x,Math.min(x+width,ax))-ax,ey=Math.max(y,Math.min(y+height,ay))-ay;return ex*ex+ey*ey+.02*((x+width/2-ax)**2+(y+height/2-ay)**2);};
  candidates.sort((a,b)=>distance(a)-distance(b));
  let chosen=null;
  for(const [dx,dy] of candidates){const x=Math.max(8,Math.min(832,ax+dx)),y=Math.max(8,Math.min(343,ay+dy));if(!occupied.some(b=>x<b.x+width+8&&x+width+8>b.x&&y<b.y+height+6&&y+height+6>b.y)){chosen={x,y};break;}}
  if(!chosen){for(let y=8;y<344&&!chosen;y+=71)for(let x=8;x<833;x+=168)if(!occupied.some(b=>x<b.x+width+8&&x+width+8>b.x&&y<b.y+height+6&&y+height+6>b.y)){chosen={x,y};break;}}
  chosen=chosen||{x:8,y:8};occupied.push(chosen);const {x,y}=chosen;
  const name=String(p.name),label=name.length>22?name.slice(0,21)+'…':name;
  return `<g class="country-weather-mark"><title>${escapeText(name)}: ${num(p.current.temperature_2m,' °C')}</title><path class="country-leader" d="M${ax.toFixed(1)} ${ay.toFixed(1)}L${Math.max(x,Math.min(x+width,ax))} ${Math.max(y,Math.min(y+height,ay))}"/><circle cx="${ax}" cy="${ay}" r="4"/><rect x="${x}" y="${y}" width="${width}" height="${height}" rx="9"/><text class="country-city-name" x="${x+10}" y="${y+21}">${escapeText(label)}</text><text class="country-temperature" x="${x+10}" y="${y+54}">${num(p.current.temperature_2m,'°')}</text><foreignObject x="${x+110}" y="${y+23}" width="44" height="38"><div xmlns="http://www.w3.org/1999/xhtml" class="country-map-icon">${weatherArt(p.current.weather_code,p.current.is_day===0)}</div></foreignObject></g>`;
 }).join('');
 return `<svg class="country-map" viewBox="0 0 1000 420" role="img" aria-label="${escapeText(shape.name)}: Wetterkarte mit Ortsnamen und Temperaturen"><defs><linearGradient id="country-fill" x2="1" y2="1"><stop stop-color="var(--accent)" stop-opacity=".65"/><stop offset="1" stop-color="#153a55"/></linearGradient></defs><path d="${path}" fill="url(#country-fill)" stroke="var(--accent)" stroke-width="2" fill-rule="evenodd"/>${marks}</svg>`;
}

function renderRegional(kind,data){
 const content=$('content');if(content.dataset.page!==kind)return;
 if(kind==='country'){
  content.innerHTML=`<div class="country-layout country-tv"><div class="country-panel">${countryGraphic(data)}<span>${escapeText(data.country?new Intl.DisplayNames(['de'],{type:'region'}).of(data.country):(data.map?.name||''))} · ${data.stale?'MODELLWERTE VERALTET':'Aktuelles Modellwetter'}</span></div></div>`;
 }else if(kind==='traffic'){
  syncTrafficVisit('traffic');
  if(!trafficVisit.data&&data.status!=='loading'){trafficVisit.data={...data,items:[...data.items]};trafficVisit.readyAt=Date.now();}
  if(trafficVisit.data)data=trafficVisit.data;
  const trafficPage=trafficCurrentPage(),start=trafficPage*3;trafficVisit.drawnPage=trafficPage;
  const status={loading:'Meldungen werden geladen …',partial:'QUELLE UNVOLLSTÄNDIG',stale:'QUELLE VERALTET',error:'Quelle nicht erreichbar',unsupported:'Keine Datenquelle verbunden',ok:'Gemeldete Ereignisse'}[data.status]||data.status;
  content.innerHTML=`<div class="regional-head"><strong>${escapeText(status)}</strong><span>${data.items.length?`Seite ${trafficPage+1}/${trafficPageCount(data)} · ${start+1}–${Math.min(start+3,data.items.length)} / ${data.items.length} · `:''}${data.radius_km} km Luftlinienradius · ${escapeText(data.source)}</span></div><div class="traffic-list">${data.items.slice(start,start+3).map(x=>`<article><div class="road-sign">${escapeText(x.road||'!')}</div><div><strong>${escapeText(x.title)}</strong><p>${escapeText(x.description)}</p></div><b>${num(x.distance_km,' km')}</b></article>`).join('')||`<div class="notice">${data.status==='loading'?'Verkehrsquelle wird zum ersten Mal eingelesen.':data.status==='ok'?'Keine Verkehrsmeldungen':'Keine verwendbaren aktuellen Verkehrsmeldungen.'}</div>`}</div><p class="regional-note">${escapeText(data.message)}</p>`;
 }else{
  const cameraStart=data.items.length?Math.floor(Date.now()/20000)%Math.ceil(data.items.length/4)*4:0;
  content.innerHTML=`<div class="regional-head"><strong>Wetter- und Stadtkameras</strong><span>Bis 100 km · ${data.status==='loading'?'Quellenprüfung läuft':data.status==='ok'?'Verzeichnis täglich geprüft':'Verzeichnis teilweise / veraltet'}</span></div><div class="webcam-grid">${data.items.slice(cameraStart,cameraStart+4).map(x=>`<a href="${escapeText(x.url)}" target="_blank" rel="noopener noreferrer"><svg viewBox="0 0 64 48" aria-hidden="true"><rect x="3" y="9" width="42" height="30" rx="6"/><path d="m45 18 15-8v28l-15-8Z"/><circle cx="24" cy="24" r="9"/></svg><div><strong>${escapeText(x.name)}</strong><small>${num(x.distance_km,' km')} · ${escapeText(x.source)}</small><span>${x.page_reachable===false?'Anbieterseite zuletzt nicht erreichbar':x.page_reachable===true?'Anbieterseite erreichbar':'Noch nicht geprüft'} · Quelle öffnen ↗</span></div></a>`).join('')||'<div class="notice">Noch keine Kameraseiten im Umkreis gefunden. Die tägliche Suche läuft unabhängig von der Vorschau.</div>'}</div><p class="regional-note">${escapeText(data.message)}</p>`;
 }
}
async function showRegional(kind){
 const key=JSON.stringify([id,kind,channel.latitude,channel.longitude,channel.country_code,channel.overview_places,channel.traffic_radius_km]);const seq=++regionalSequence;
 const old=regionalData.get(key);if(old&&(kind!=='traffic'||Date.now()-old.stamp<15000))renderRegional(kind,old.data);else if(kind!=='traffic'||!trafficVisit?.data)$('content').innerHTML='<div class="notice">Regionale Daten werden geladen …</div>';
 if(old&&Date.now()-old.stamp<15000)return;
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),25000);
 try{const r=await fetch(`/api/${kind==='country'?'country':kind==='traffic'?'traffic':'webcams'}/${id}`,{cache:'no-store',signal:controller.signal});const data=await r.json();if(!r.ok)throw Error(data.detail||'Datenquelle nicht erreichbar');regionalData.set(key,{stamp:Date.now(),data});if(seq===regionalSequence)renderRegional(kind,data);}
 catch(e){if(seq===regionalSequence&&$('content').dataset.page===kind){if(kind==='traffic')renderRegional('traffic',{items:[],status:'error',radius_km:channel.traffic_radius_km,source:'Verkehrsquelle',message:'Verkehrsquelle derzeit nicht verfügbar. Keine Entwarnung ableitbar.'});else $('content').innerHTML=`<div class="notice">${escapeText(e.message)}</div>`;}}finally{clearTimeout(timeout);}
}
setInterval(()=>{const kind=$('content')?.dataset.page;if(['country','traffic'].includes(kind))showRegional(kind);},20000);
let placePhotoKey='',placePhotoInfo=null,placePhotoChecked=0;
async function syncPlacePhoto(){
 const themes=new Set(['metro-red','ocean-blue','forest-green','city-photo']);const screen=document.querySelector('.tv');
 if(!themes.has(activeTheme())){screen.classList.remove('place-photo-active');if(placePhotoKey)$('source').textContent='Wetterdaten: Open-Meteo · Modellwerte und Prognosen';placePhotoKey='';return;}
 const key=JSON.stringify([id,channel.latitude,channel.longitude,sceneState.period,sceneState.weather]);
 if(key===placePhotoKey&&Date.now()-placePhotoChecked<30000)return;if(key!==placePhotoKey)screen.classList.remove('place-photo-active');placePhotoKey=key;placePhotoChecked=Date.now();
 try{const r=await fetch(`/api/place-photo/${id}?period=${['dawn','day','dusk','night'].includes(sceneState.period)?sceneState.period:'any'}&weather=${sceneState.weather}`);if(!r.ok)throw Error();const p=await r.json();if(key!==placePhotoKey)return;placePhotoInfo=p;
  if(p.available){screen.style.setProperty('--scene-photo',`url('${p.image}')`);screen.classList.add('place-photo-active');$('source').textContent=`Wetter: Open-Meteo · Archivfoto: ${p.artist||p.title} · ${p.license}`;$('source').title=p.message+' '+p.source_url;}else{screen.classList.remove('place-photo-active');$('source').textContent='Wetterdaten: Open-Meteo · Modellwerte und Prognosen';}
 }catch(_){}
}
