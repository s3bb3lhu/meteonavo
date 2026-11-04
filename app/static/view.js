const id=Number(location.pathname.split('/').pop());
const broadcastRender=new URLSearchParams(location.search).get('render')==='1';
const weatherPages=['current','daily','hourly','wind','precipitation','radar','country','traffic','webcams'];
const initialPreviewPage=new URLSearchParams(location.search).get('page');
let selectedPreviewPage=!broadcastRender&&weatherPages.includes(initialPreviewPage)?initialPreviewPage:null;
let channel=null,weather=null,error='',pageIndex=0,lastSwitch=Date.now(),fetching=false,lastRenderKey='';
const requestedTheme=new URLSearchParams(location.search).get('theme');
const previewTheme=Object.hasOwn(designPresets,requestedTheme)?requestedTheme:null;
function activeTheme(){return designPresets[previewTheme]?previewTheme:(channel?.theme||'classic');}
function applyDesign(){
 const screen=document.querySelector('.tv'),theme=activeTheme(),preset=designPresets[theme]||designPresets.classic;
 screen.dataset.frame=typeof selectedFrame==='function'?selectedFrame(channel):'design';
 applyFrameOptions(screen,channel);
 screen.dataset.theme=theme;screen.classList.toggle('no-motion',channel?.motion===false);screen.classList.toggle('cinema-layout',cinematicFamily.has(theme));document.querySelector('.date-frame').hidden=false;
 applyTvLogo(screen,channel);
 const customAccent=new URLSearchParams(location.search).get('accent'),customBase=new URLSearchParams(location.search).get('base');
 document.documentElement.style.setProperty('--accent',!broadcastRender&&/^#[0-9a-fA-F]{6}$/.test(customAccent)?customAccent:(designPresets[previewTheme]?preset.color:channel.color));
 document.documentElement.style.setProperty('--bg',!broadcastRender&&/^#[0-9a-fA-F]{6}$/.test(customBase)?customBase:(designPresets[previewTheme]?preset.background:channel.background));
 screen.style.setProperty('--accent',document.documentElement.style.getPropertyValue('--accent'),'important');
 $('brand-name').textContent=theme==='classic'?'WEATHER CHANNEL STUDIO':preset.name.toUpperCase();
 $('design-preview').textContent=designPresets[previewTheme]?'DESIGNVORSCHAU':'';
 if(lastNewsData&&!lastNewsData.enabled)paintNews(lastNewsData);
}
const $=id=>document.getElementById(id);
const escapeText=s=>String(s??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=(v,unit='')=>v==null?'—':`${Number(v).toLocaleString('de-DE',{maximumFractionDigits:1})}${unit}`;
function condition(c){return weatherLabel(c,sceneState.night);}
const metric=(name,value)=>`<div class="metric"><span class="metric-label">${studioIcon(({Gefühlt:'thermometer',Luftfeuchte:'drop',Wind:'wind',Heute:'sun',Richtung:'compass'})[name]||'clock')}${escapeText(name)}</span><br><strong>${escapeText(value)}</strong></div>`;
async function update(){if(fetching)return;fetching=true;try{const r=await fetch('/api/channels',{cache:'no-store'});if(!r.ok)throw Error('Konfiguration nicht erreichbar');const next=(await r.json()).find(c=>c.id===id);if(channel&&(channel.latitude!==next.latitude||channel.longitude!==next.longitude))weather=null;if(channel&&JSON.stringify([channel.latitude,channel.longitude,channel.country_code,channel.warning_region,channel.warnings_enabled])!==JSON.stringify([next.latitude,next.longitude,next.country_code,next.warning_region,next.warnings_enabled]))warningData={status:'loading',items:[]};channel=next;applyDesign();$('place').textContent=channel.location||channel.name;const w=await fetch(`/api/weather/${id}`,{cache:'no-store'});if(!w.ok)throw Error(w.status===409?'Bitte zuerst einen Ort konfigurieren':'Wetterdienst nicht erreichbar');weather=await w.json();error='';}catch(e){error=e.message;}finally{fetching=false;render();}}
function render(){
 if(typeof refreshWarningTicker==='function')refreshWarningTicker();
 const now=new Date(),timeZone=weather?.data?.timezone||'UTC';
 $('clock').textContent=now.toLocaleTimeString('de-DE',{timeZone,hour:'2-digit',minute:'2-digit',second:'2-digit'});
 $('date-weekday').textContent=now.toLocaleDateString('de-DE',{timeZone,weekday:'long'});
 $('date').textContent=now.toLocaleDateString('de-DE',{timeZone,day:'2-digit',month:'long',year:'numeric'});
 $('ticker-clock').textContent=now.toLocaleTimeString('de-DE',{timeZone,hour:'2-digit',minute:'2-digit'});
 if(!channel)return;
 syncScene(weather?.data,activeTheme(),channel.motion);
 const usingLandscape=typeof syncLandscape==='function'&&syncLandscape();
 if(!usingLandscape&&typeof syncPlacePhoto==='function')syncPlacePhoto();
 const onAir=channel.pages[pageIndex%channel.pages.length];
 const pageSeconds=onAir==='traffic'&&typeof trafficPageSeconds==='function'?trafficPageSeconds(channel.seconds):(onAir==='webcams'&&typeof cameraPageSeconds==='function'?cameraPageSeconds(channel.seconds):channel.seconds);
 if(selectedPreviewPage===null&&Date.now()-lastSwitch>=pageSeconds*1000){pageIndex++;lastSwitch=Date.now();}
 const kind=selectedPreviewPage||channel.pages[pageIndex%channel.pages.length];
 if(kind!=='webcams'&&typeof stopCamera==='function')stopCamera();
 $('content').dataset.page=kind;
 if(typeof syncTrafficVisit==='function')syncTrafficVisit(kind);
 if(typeof syncPreviewControls==='function')syncPreviewControls(kind);
 const titles={current:'Aktuelles Modellwetter',daily:'Die nächsten 7 Tage · Prognose',hourly:'Die nächsten Stunden · Prognose',wind:'Wind · Modellwert und Prognose',precipitation:'Regen und Schnee · Prognose',radar:'Niederschlagsradar · vergangene Messbilder',country:'Wetter im Land · Modellwerte',traffic:'Verkehr aus der Region',webcams:'Kamerafenster aus der Region'};
 $('title').textContent=titles[kind];
 const age=weather?(Date.now()/1000-weather.fetched_at):0;
 $('status').textContent=(error?'Verbindungsfehler · ':'')+(weather?(weather.stale||age>1200?'WETTERDATEN VERALTET':''):'Keine Daten');
 const renderKey=JSON.stringify([kind,weather?.fetched_at,error,activeTheme(),channel.motion,channel.icon_set,channel.latitude,channel.longitude,channel.radar_radius_km,channel.radar_map_style,channel.radar_zoom,channel.landscape_mood,channel.frame_style,channel.frame_custom,channel.frame_color,channel.frame_width,channel.frame_radius,channel.frame_opacity,channel.overview_places,channel.traffic_radius_km,sceneState.night]);
 if(renderKey===lastRenderKey){if(kind==='traffic'&&typeof tickTraffic==='function')tickTraffic();return;}
 lastRenderKey=renderKey;
 const navPages=selectedPreviewPage?weatherPages:channel.pages;
 $('page-dots').innerHTML=navPages.map((page,i)=>`<span class="${selectedPreviewPage?page===kind?'active':'':i===pageIndex%channel.pages.length?'active':''}"></span>`).join('');
 const content=$('content');content.classList.remove('page-enter');void content.offsetWidth;content.classList.add('page-enter');
 if(kind==='webcams'&&typeof showCameraPage==='function'){showCameraPage();return;}
 if(['country','traffic','webcams'].includes(kind)){if(typeof showRegional==='function')showRegional(kind);return;}
 if(kind==='radar'){if(typeof showRadar==='function')showRadar(content);else content.textContent='Radaransicht wird geladen …';return;}
 if(!weather){$('content').textContent=error||'Wetterdaten werden geladen …';return;}
 const d=weather.data,c=d.current,h=d.hourly;
 let start=h.time.findIndex(t=>t>=c.time);if(start<0)start=0;
 if(kind==='current')$('content').innerHTML=`<div class="now-layout"><div><div class="hero">${num(c.temperature_2m,' °C')}</div><div class="weather-description">${escapeText(condition(c.weather_code))}</div></div><div class="weather-visual">${weatherArt(c.weather_code,false,sceneState.night)}</div></div><div class="metrics">${metric('Gefühlt',num(c.apparent_temperature,' °C'))}${metric('Luftfeuchte',num(c.relative_humidity_2m,' %'))}${metric('Wind',num(c.wind_speed_10m,' km/h'))}${metric('Heute',num(d.daily.temperature_2m_min[0])+' / '+num(d.daily.temperature_2m_max[0],' °C'))}</div>`;
 else if(kind==='daily')$('content').innerHTML='<div class="week">'+d.daily.time.map((t,i)=>`<div class="day"><div class="day-date">${new Date(t+'T12:00:00').toLocaleDateString('de-DE',{weekday:'short',day:'2-digit'})}</div>${weatherArt(d.daily.weather_code[i],true)}<div class="condition">${escapeText(weatherLabel(d.daily.weather_code[i],false))}</div><strong>${num(d.daily.temperature_2m_max[i],'°')}</strong>${num(d.daily.temperature_2m_min[i],'°')}${typeof dayRange==='function'&&cinematicFamily.has(activeTheme())?dayRange(d.daily,i):''}<div class="day-rain">Regen ${num(d.daily.precipitation_probability_max[i],'%')}</div></div>`).join('')+'</div>';
 else if(kind==='wind')$('content').innerHTML=`<div class="now-layout"><div><div class="hero">${num(c.wind_speed_10m,' km/h')}</div><div class="weather-description">Wind am Standort</div></div><div class="weather-visual"><div class="compass"><div class="wind-rings"></div><div class="wind-arrow" style="--wind-direction:${Number(c.wind_direction_10m)||0}deg"><svg viewBox="0 0 100 100" aria-hidden="true"><path d="M50 5 73 78 50 65 27 78Z" fill="currentColor"/><path d="M50 5v60L27 78Z" fill="#e9f6ff" opacity=".8"/><circle cx="50" cy="52" r="5" fill="#173044"/></svg></div></div></div></div><div class="metrics">${metric('Richtung',num(c.wind_direction_10m,'°'))}${metric('In 3 Stunden',num(h.wind_speed_10m[start+3],' km/h'))}${metric('In 6 Stunden',num(h.wind_speed_10m[start+6],' km/h'))}</div>`;
 else if(cinematicFamily.has(activeTheme())&&typeof forecastGraphic==='function')$('content').innerHTML=forecastGraphic(h,start,kind);
 else {let rows='';for(let i=start;i<Math.min(start+6,h.time.length);i++){rows+=`<tr><td>${escapeText(h.time[i].slice(11))}</td>`+(kind==='hourly'?`<td>${num(h.temperature_2m[i],' °C')}</td><td>${num(h.precipitation_probability[i],' %')}</td><td>${num(h.wind_speed_10m[i],' km/h')}</td>`:`<td>${num(h.rain[i],' mm')}</td><td>${num(h.snowfall[i],' cm')}</td><td>${num(h.precipitation_probability[i],' %')}</td>`)+'</tr>';}$('content').innerHTML=`<table><thead><tr><th>Ortszeit (${escapeText(d.timezone)})</th>${kind==='hourly'?'<th>Temperatur</th><th>Niederschlag</th><th>Wind</th>':'<th>Regen</th><th>Schnee</th><th>Wahrscheinlichkeit</th>'}</tr></thead><tbody>${rows}</tbody></table>`;}
 if(typeof decorateConcept==='function')decorateConcept();
}
let newsFetching=false,lastNewsUrl=null,lastNewsKey='',lastNewsData=null;
function drawNews(data){
 lastNewsData=data;
 const ticker=$('ticker'),track=$('ticker-track');
 ticker.classList.toggle('has-warning',!!data.warning);
 ticker.dataset.warningLevel=data.warningLevel||'';
 ticker.hidden=!data.enabled&&!cinematicFamily.has(activeTheme());
 if(!data.enabled){lastNewsKey='';track.replaceChildren();track.classList.remove('running');if(cinematicFamily.has(activeTheme())){$('ticker-label').textContent='NACHRICHTEN';$('ticker-source').textContent='RSS nicht eingerichtet';const hint=document.createElement('span');hint.className='ticker-group';hint.textContent='RSS-Nachrichtenquelle im Kanalformular hinzufügen.';track.append(hint);}return;}
 $('ticker-label').textContent=data.warning?'WETTERWARNUNG':data.stale?'RSS · VERALTET':'NACHRICHTEN';
 $('ticker-source').textContent=data.source||'RSS';
 $('ticker-source').title=data.fetched_at?`Letzter Abruf: ${new Date(data.fetched_at*1000).toLocaleString('de-DE')}`:data.message;
 const key=JSON.stringify([data.headlines,data.source,data.warning,data.warningLevel]);
 if(key===lastNewsKey)return;
 lastNewsKey=key;
 track.replaceChildren();
 const headlines=data.headlines||[];
 track.classList.toggle('running',headlines.length>0);
 const text=headlines.length?headlines.join('   •   '):(data.message||'Noch keine Schlagzeilen verfügbar');
 for(let i=0;i<(headlines.length?2:1);i++){
   const group=document.createElement('span');group.className='ticker-group';group.textContent=text;
   if(i===1)group.setAttribute('aria-hidden','true');
   track.append(group);
 }
 // Keep a stable speed regardless of the feed's headline count.
 requestAnimationFrame(()=>track.style.setProperty('--ticker-duration',`${Math.max(20,track.scrollWidth/2/30)}s`));
}
async function updateNews(){
 if(newsFetching||!channel)return;
 const url=channel.rss_url||'';
 if(url!==lastNewsUrl){lastNewsUrl=url;lastNewsKey='';paintNews({enabled:!!url,source:'RSS',headlines:[],stale:false,message:'Nachrichten werden geladen …'});}
 if(!url){paintNews({enabled:false});return;}
 newsFetching=true;
 try{
   const r=await fetch(`/api/news/${id}`,{cache:'no-store'});
   if(!r.ok)throw Error('RSS-Abruf fehlgeschlagen');
   const data=await r.json();
   if(url===(channel.rss_url||''))paintNews(data);
 }catch(e){
   if(url===(channel.rss_url||'')){
     $('ticker-label').textContent='RSS · VERBINDUNGSFEHLER';
     paintNews({...(lastNewsData||{}),enabled:true,source:lastNewsData?.source||'RSS',headlines:lastNewsData?.headlines||[],stale:true,message:'Nachrichten derzeit nicht erreichbar'});
   }
 }finally{newsFetching=false;}
}
let lastRssData={enabled:false},warningData={status:'loading',items:[]},warningFetching=false;
function paintNews(data){lastRssData=data;refreshWarningTicker();}
function refreshWarningTicker(){
 const now=Date.now()/1000,items=(warningData.items||[]).filter(w=>w.expires>now).sort((a,b)=>b.level-a.level),tz=weather?.data?.timezone||'UTC';
 const date=t=>new Date(t*1000).toLocaleString('de-DE',{timeZone:tz,day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
 const warnings=items.map(w=>`WETTERWARNUNG · Stufe ${w.level===4?'Rot':w.level===3?'Orange':'Gelb'} · ${w.area}: ${w.headline} · ${w.onset?'ab '+date(w.onset)+' · ':''}gültig bis ${date(w.expires)} · ${warningData.status==='stale'?'QUELLE VERALTET · ':''}${w.source}`);
 const unavailable=['stale','unavailable','needs_region','unsupported'].includes(warningData.status)?[warningData.message||'Warnlage derzeit nicht prüfbar']:[];
 const headlines=[...warnings,...unavailable,...(lastRssData.headlines||[])];
 drawNews({...lastRssData,enabled:lastRssData.enabled||headlines.length>0,source:items.length?'MeteoAlarm · amtliche Warnungen':lastRssData.source||'Warninformationen',headlines,warning:items.length>0,warningLevel:items[0]?.level||0});
}
async function updateWarnings(){
 if(warningFetching||!channel)return;warningFetching=true;
 const configKey=JSON.stringify([channel.latitude,channel.longitude,channel.country_code,channel.warning_region,channel.warnings_enabled]);
 try{const r=await fetch(`/api/warnings/${id}`,{cache:'no-store'});if(!r.ok)throw Error();const next=await r.json();if(configKey===JSON.stringify([channel.latitude,channel.longitude,channel.country_code,channel.warning_region,channel.warnings_enabled]))warningData=next;}
 catch(_){warningData={...warningData,status:'stale',message:'Amtliche Warnquelle nicht erreichbar · keine Entwarnung ableitbar'};}
 finally{warningFetching=false;refreshWarningTicker();}
}
update().then(()=>{updateNews();updateWarnings();});setInterval(updateWarnings,60000);setInterval(()=>update().then(()=>{if(channel&&(channel.rss_url||'')!==lastNewsUrl)updateNews();updateWarnings();}),15000);setInterval(updateNews,60000);setInterval(render,1000);

