// Real radar imagery and a local geographic basemap share Web-Mercator coordinates.
let radarMapData=null,radarMapPromise=null,radarState=null;
const RADAR_W=800,RADAR_H=300;
function radarProject(lon,lat,centerLon,centerLat,zoom){
 const merc=v=>Math.log(Math.tan(Math.PI/4+Math.max(-85.051129,Math.min(85.051129,v))*Math.PI/360));
 const scale=RADAR_W*2**zoom;
 return [RADAR_W/2+(lon-centerLon)/360*scale,RADAR_H/2-(merc(lat)-merc(centerLat))/(2*Math.PI)*scale];
}
async function radarGeography(){
 if(!radarMapPromise)radarMapPromise=fetch('/api/radar/geography?v=2').then(r=>{if(!r.ok)throw Error('Karte nicht verfügbar');return r.json();}).then(d=>(radarMapData=d)).catch(e=>{radarMapPromise=null;throw e;});
 return radarMapPromise;
}
function radarGeometry(latitude,zoom,radius){
 const effective=radius?Math.max(1,Math.log2(Math.cos(latitude*Math.PI/180)*40075/(2*radius))):zoom;
 const source=Math.max(1,Math.min(7,Math.floor(effective)));
 return {effective,source,size:RADAR_W*2**(effective-source)};
}
function radarScaleLabel(latitude,zoom){const km=Math.cos(latitude*Math.PI/180)*40075/(RADAR_W*2**zoom)*100;return km<1?Math.round(km*1000)+' m':Math.round(km)+' km';}
function radarMapStyle(){const requested=new URLSearchParams(location.search).get('map');return !broadcastRender&&['streets','streets-dark','satellite','satellite-night','overview'].includes(requested)?requested:(channel.radar_map_style||'streets');}
function radarRequestedGoogle(){return radarMapStyle().startsWith('google-');}
function radarBaseStyle(){const style=radarMapStyle();return style.startsWith('google-')?(style==='google-satellite'||style==='google-hybrid'?'satellite':'streets'):style;}
function radarMapCredit(){return radarBaseStyle().startsWith('satellite')?'Bild: Esri, Vantor, Earthstar Geographics, GIS User Community · Archivbild'+(radarMapStyle()==='satellite-night'?' · Nachtoptik (Filter)':''):'© OpenStreetMap-Mitwirkende';}
function radarStreetTiles(meta,zoom){
 const style=radarBaseStyle();if(style==='overview')return '';const provider=style.startsWith('satellite')?'satellite':'streets';
 const scale=RADAR_W*2**zoom,z=Math.max(0,Math.min(18,Math.floor(Math.log2(scale/256)))),n=2**z,size=scale/n;
 const lat=Math.max(-85.051129,Math.min(85.051129,meta.latitude))*Math.PI/180;
 const cx=(meta.longitude+180)/360*n,cy=(1-Math.log(Math.tan(Math.PI/4+lat/2))/Math.PI)/2*n,tiles=[];
 for(let y=Math.floor(cy-RADAR_H/2/size);y<=Math.floor(cy+RADAR_H/2/size);y++)for(let x=Math.floor(cx-RADAR_W/2/size);x<=Math.floor(cx+RADAR_W/2/size);x++){
  if(y<0||y>=n)continue;
  tiles.push(`<image class="radar-street-tile" x="${RADAR_W/2+(x-cx)*size}" y="${RADAR_H/2+(y-cy)*size}" width="${size+.1}" height="${size+.1}" href="/api/radar/map/${provider}/${z}/${((x%n)+n)%n}/${y}.png"/>`);
 }
 return tiles.join('');
}
function radarMapMarkup(data,meta,zoom,radius=null){
 const geometry=radarGeometry(meta.latitude,zoom,radius);zoom=geometry.effective;
 const size=radius?geometry.size:RADAR_W,left=(RADAR_W-size)/2,top=(RADAR_H-size)/2;
 const project=(lon,lat)=>radarProject(lon,lat,meta.longitude,meta.latitude,zoom);
 const paths=[];
 for(const country of data.countries){
  const polys=country.geometry.type==='Polygon'?[country.geometry.coordinates]:country.geometry.coordinates;
  for(const rings of polys){
   const points=rings.flat();if(!points.length)continue;
   const bounds=points.map(p=>project(...p));
   if(Math.max(...bounds.map(p=>p[0]))<0||Math.min(...bounds.map(p=>p[0]))>RADAR_W||Math.max(...bounds.map(p=>p[1]))<0||Math.min(...bounds.map(p=>p[1]))>RADAR_H)continue;
   const path=rings.map(r=>r.map((p,i)=>{const [x,y]=project(...p);return (i?'L':'M')+x.toFixed(1)+' '+y.toFixed(1);}).join('')+'Z').join('');
   paths.push(`<path d="${path}"/>`);
  }
 }
 const labels=[],occupied=[[400,150]];
 for(const city of [...data.cities].sort((a,b)=>a.rank-b.rank)){
  const [x,y]=project(...city.coordinates);
  if(x<25||x>745||y<20||y>280||occupied.some(p=>Math.abs(x-p[0])<(p[0]===400?40:90)&&Math.abs(y-p[1])<18))continue;
  occupied.push([x,y]);labels.push(`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2"/><text x="${(x+(x<400?-6:6)).toFixed(1)}" y="${(y+4).toFixed(1)}" text-anchor="${x<400?'end':'start'}">${escapeText(city.name)}</text>`);
 }
 const scaleLabel=radarScaleLabel(meta.latitude,zoom);
 return `<svg id="radar-map" viewBox="0 0 800 300" data-map-style="${radarMapStyle()}" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Radarübersicht um ${escapeText(channel.location||channel.name)}"><rect width="800" height="300" fill="#112c43"/><g class="radar-land" fill-rule="evenodd">${paths.join('')}</g><g class="radar-grid"><path d="M200 0V300M400 0V300M600 0V300M0 75H800M0 150H800M0 225H800"/></g><g class="radar-streets">${radarStreetTiles(meta,zoom)}</g><image id="radar-echoes" x="${left}" y="${top}" width="${size}" height="${size}"/><image id="radar-coverage" x="${left}" y="${top}" width="${size}" height="${size}" opacity=".45"/><g class="radar-cities" opacity=".8">${labels.join('')}</g><g class="radar-location"><title>${escapeText(channel.address||channel.location||channel.name)} · ${meta.latitude}, ${meta.longitude}</title><path class="radar-pin" d="M400 150C395 142 388 135 388 126a12 12 0 0 1 24 0c0 9-7 16-12 24Z"/><circle class="radar-pin-center" cx="400" cy="126" r="4"/><text x="413" y="141">${escapeText(channel.location||channel.name)}</text></g><g class="radar-attribution"><rect x="280" y="281" width="520" height="19" fill="#102739df"/><text x="793" y="294" text-anchor="end">${escapeText(radarMapStyle()==='overview'?'Karte: Natural Earth':radarMapCredit())}</text></g><g class="radar-scale"><path d="M24 269v6h100v-6"/><text x="24" y="261">≈ ${scaleLabel}</text></g></svg>`;
}
function showRadar(content){
 const signature=JSON.stringify([id,channel.latitude,channel.longitude,channel.radar_zoom||6,channel.radar_radius_km,radarMapStyle(),channel.motion]);
 if(radarState?.signature===signature&&document.getElementById('radar-card'))return;
 radarState={signature,radius:channel.radar_radius_km||null,zoom:channel.radar_radius_km?radarGeometry(channel.latitude,6,channel.radar_radius_km).source:(channel.radar_zoom||6),meta:null,index:-1,busy:false,metaBusy:false,lastMeta:0,lastFrame:0,paused:channel.motion===false,sequence:0,coverage:false,error:'',retry:0};
 content.innerHTML=`<div id="radar-card" class="radar-card ${broadcastRender?'radar-broadcast':''}"><div class="radar-heading"><div><strong>Niederschlagsradar</strong><span id="radar-status">Radarquelle wird geladen …</span></div><div class="radar-zoom"><button id="radar-zoom-out" type="button" aria-label="Radar herauszoomen">−</button><span id="radar-zoom-label"></span><button id="radar-zoom-in" type="button" aria-label="Radar hineinzoomen">+</button></div></div><div class="radar-stage"><div id="radar-geography"></div><div id="radar-loading" class="radar-loading">Echte Radarbilder werden geladen …</div><div class="radar-source-badge">MESSDATEN · KEINE PROGNOSE</div></div><div class="radar-timeline"><button id="radar-play" type="button"></button><span id="radar-time">Noch kein Radarbild</span><input id="radar-slider" type="range" min="0" max="0" value="0" aria-label="Radarbild auf der Zeitachse wählen"><span id="radar-age"></span></div><div class="radar-foot"><div class="radar-legend"><span>Schwächere Echos</span><i></i><span>Stärkere Echos</span></div><span id="radar-coverage-status">Abdeckung wird geprüft</span><div><a href="https://www.rainviewer.com/" target="_blank" rel="noopener">Radar: RainViewer</a> · <a href="${radarBaseStyle().startsWith('satellite')?'https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9':'https://www.openstreetmap.org/copyright'}" target="_blank" rel="noopener">${radarMapStyle()==='overview'?'Karte: Natural Earth':radarMapCredit()}</a> · Bildzeit = Kompositzeit</div><small>Straßenkarte nach Radar-Zoom / Distanz. Stecknadel = gespeicherte GPS-Position. Abgedunkelt: keine Radarabdeckung. Keine Echos können auch Datenlücken bedeuten.</small></div></div>`;
 const state=radarState;
 document.getElementById('radar-play').onclick=()=>{state.paused=!state.paused;radarLabels(state);};
 document.getElementById('radar-slider').onchange=e=>{state.paused=true;radarFrame(state,Number(e.target.value));};
 for(const [key,step] of [['radar-zoom-out',-1],['radar-zoom-in',1]])document.getElementById(key).onclick=()=>radarZoom(state,step);
 radarLabels(state);radarLoad(state);
}
function radarLabels(state){
 if(state!==radarState||!document.getElementById('radar-card'))return;
 document.getElementById('radar-play').textContent=state.paused?'▶ Abspielen':'Ⅱ Pause';
 document.getElementById('radar-zoom-label').textContent=state.radius?'± '+Math.round(Math.cos(channel.latitude*Math.PI/180)*40075/(2*2**radarGeometry(channel.latitude,6,state.radius).effective))+' km (ca.)':'Ausschnitt '+state.zoom+'/7';
 document.getElementById('radar-zoom-out').disabled=state.radius?state.radius>=5000:state.zoom<=1;document.getElementById('radar-zoom-in').disabled=state.radius?state.radius<=1:state.zoom>=7;
 if(state.meta){const newest=state.meta.frames.at(-1).time,age=Math.max(0,Math.floor((Date.now()/1000-newest)/60));document.getElementById('radar-age').textContent=`Neuester Stand: ${age} Min.`;document.getElementById('radar-status').textContent=state.error||(state.meta.stale?'QUELLE VERALTET · ':'')+'Vergangene Radar-Komposite · automatisch aktualisiert';}
}
async function radarLoad(state){
 if(state.metaBusy||state!==radarState)return;state.metaBusy=true;state.lastMeta=Date.now();
 try{
  const response=await fetch(`/api/radar/${id}`,{cache:'no-store'});const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Radarquelle nicht erreichbar');
  const geography=await radarGeography();if(state!==radarState||!document.getElementById('radar-card'))return;
  const old=state.meta;state.meta=data;state.error='';
  document.getElementById('radar-slider').max=data.frames.length-1;
  if(!old||old.position!==data.position){document.getElementById('radar-geography').innerHTML=radarMapMarkup(geography,data,state.zoom,state.radius);radarWatchTiles();radarGoogleMount(state);state.index=-1;radarCoverage(state);}
  radarLabels(state);await radarFrame(state,data.frames.length-1);
 }catch(error){if(state!==radarState||!document.getElementById('radar-card'))return;state.error=error.message;if(state.meta)state.meta.stale=true;document.getElementById('radar-status').textContent=error.message;const loading=document.getElementById('radar-loading');loading.textContent=state.index<0?'Keine Radardaten verfügbar · '+error.message:'Radarquelle nicht erreichbar · vorheriges Bild bleibt sichtbar';loading.hidden=false;}
 finally{state.metaBusy=false;}
}
function loadRadarImage(url){return new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>reject(Error('Radarbild momentan nicht ladbar'));image.src=url;});}
async function radarFrame(state,index){
 if(!state.meta||state!==radarState||state.busy||!document.getElementById('radar-map'))return;
 const frame=state.meta.frames[index];if(!frame)return;
 state.busy=true;const sequence=++state.sequence;state.lastFrame=Date.now();
 const url=`/api/radar/${id}/image/${frame.time}?zoom=${state.zoom}&position=${state.meta.position}`;
 try{
  await loadRadarImage(url);if(state!==radarState||sequence!==state.sequence||!document.getElementById('radar-map'))return;
  document.getElementById('radar-echoes').setAttribute('href',url);state.index=index;state.error='';
  document.getElementById('radar-slider').value=index;
  const zone=weather?.data?.timezone||'UTC';document.getElementById('radar-time').textContent=new Date(frame.time*1000).toLocaleString('de-DE',{timeZone:zone,day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})+' · Bildzeit';
  document.getElementById('radar-loading').hidden=true;document.getElementById('radar-card').dataset.frame=frame.time;radarLabels(state);
 }catch(error){if(state!==radarState||!document.getElementById('radar-card'))return;state.error=state.index<0?error.message:error.message+' · vorheriges Bild';state.retry=Date.now()+10000;document.getElementById('radar-status').textContent=state.error;if(state.index<0)document.getElementById('radar-loading').textContent='Keine Radarbilder verfügbar';}
 finally{if(sequence===state.sequence)state.busy=false;}
}
async function radarCoverage(state){
 state.coverage=false;
 const url=`/api/radar/${id}/coverage?zoom=${state.zoom}&position=${state.meta.position}`,position=state.meta.position,zoom=state.zoom;
 try{await loadRadarImage(url);if(state!==radarState||position!==state.meta?.position||zoom!==state.zoom||!document.getElementById('radar-map'))return;document.getElementById('radar-coverage').setAttribute('href',url);state.coverage=true;document.getElementById('radar-coverage-status').textContent='Abdeckungsmaske aktiv';}
 catch(_){if(state===radarState&&document.getElementById('radar-card'))document.getElementById('radar-coverage-status').textContent='Abdeckung derzeit nicht prüfbar';}
}
function radarZoom(state,step){
 if(!state.meta)return;if(state.radius){state.radius=Math.max(1,Math.min(5000,Math.round(state.radius*2**(-step))));state.zoom=radarGeometry(state.meta.latitude,6,state.radius).source;}else state.zoom=Math.max(1,Math.min(7,state.zoom+step));state.sequence++;state.busy=false;state.index=-1;state.error='';
 document.getElementById('radar-geography').innerHTML=radarMapMarkup(radarMapData,state.meta,state.zoom,state.radius);radarWatchTiles();radarGoogleMount(state);document.getElementById('radar-loading').hidden=false;document.getElementById('radar-loading').textContent='Radarbild für den Ausschnitt wird geladen …';
 radarLabels(state);radarCoverage(state);radarFrame(state,state.meta.frames.length-1);
}
setInterval(()=>{
 const state=radarState;if(!state||!document.getElementById('radar-card'))return;
 radarLabels(state);
 if(Date.now()-state.lastMeta>180000)radarLoad(state);
 if(state.meta&&!state.paused&&!state.busy&&Date.now()>state.retry&&Date.now()-state.lastFrame>1600)radarFrame(state,(state.index+1)%state.meta.frames.length);
},400);

function radarWatchTiles(){
 const tiles=[...document.querySelectorAll('.radar-street-tile')];
 for(const tile of tiles)tile.addEventListener('error',()=>{document.querySelectorAll('.radar-streets').forEach(g=>g.remove());const text=document.querySelector('.radar-attribution text');if(text)text.textContent='Kartenquelle nicht verfügbar · Ersatzkarte: Natural Earth';},{once:true});
}

function radarGoogleMount(state){if(radarRequestedGoogle()&&typeof mountGoogleRadar==='function')mountGoogleRadar(state);}
