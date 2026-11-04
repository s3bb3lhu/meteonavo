// Official Maps JavaScript API only; no Google tiles pass through our tile cache.
// Reuse one map across page rotations so frames/rotations don't create new maps.
let googleRadarSDK=null,googleRadarKey='',googleRadarMap=null,googleRadarHost=null,googleRadarObserver=null,googleRadarAuthFailed=false;
function googleRadarZoom(width,effective,height=0){return Math.log2(Math.max(width,height*800/300)/256)+effective;}
function googleRadarFallback(state,message){
 if(state!==radarState||!document.getElementById('radar-map'))return;
 document.getElementById('radar-geography').classList.remove('google-active');
 if(googleRadarHost)googleRadarHost.hidden=true;
 const note=document.getElementById('radar-google-status');if(note)note.textContent=message+' · Ersatzkarte: '+(radarBaseStyle()==='satellite'?'Esri':'OpenStreetMap');
 const credit=document.querySelector('.radar-foot a:nth-of-type(2)');if(credit){credit.textContent=radarMapCredit();credit.href=radarBaseStyle()==='satellite'?'https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9':'https://www.openstreetmap.org/copyright';}
}
function loadGoogleRadarSDK(key){
 if(googleRadarSDK){if(key!==googleRadarKey)return Promise.reject(Error('Google-Key geändert: Vorschau neu laden'));return googleRadarSDK;}
 googleRadarKey=key;
 googleRadarSDK=new Promise((resolve,reject)=>{
  const script=document.createElement('script');let settled=false;
  const finish=error=>{if(settled)return;settled=true;clearTimeout(timer);error?reject(Error(error)):resolve(window.google.maps);};
  const timer=setTimeout(()=>finish('Google Maps antwortet nicht'),20000);
  window.meteonavoGoogleReady=()=>finish();
  window.gm_authFailure=()=>{googleRadarAuthFailed=true;finish('Google-Key, Abrechnung oder Website-Beschränkung prüfen');googleRadarFallback(radarState,'Google-Key, Abrechnung oder Website-Beschränkung prüfen');};
  const query=new URLSearchParams({key,callback:'meteonavoGoogleReady',loading:'async',v:'quarterly'});
  script.src='https://maps.googleapis.com/maps/api/js?'+query;script.async=true;
  script.onerror=()=>finish('Google Maps konnte nicht geladen werden');document.head.append(script);
 });
 return googleRadarSDK;
}
async function mountGoogleRadar(state){
 if(state!==radarState||!radarRequestedGoogle())return;
 const container=document.getElementById('radar-geography');
 if(!document.getElementById('radar-google-status')){const note=document.createElement('small');note.id='radar-google-status';note.setAttribute('role','status');document.querySelector('.radar-foot').append(note);}
 const note=document.getElementById('radar-google-status');note.textContent='Google Maps wird geladen …';
 try{
  const response=await fetch(`/api/maps/google/client/${id}?broadcast=${broadcastRender?'true':'false'}`,{cache:'no-store'});
  if(!response.ok)throw Error('Google-Konfiguration nicht verfügbar');const config=await response.json();
  if(!config.key)throw Error(broadcastRender&&config.configured&&!config.broadcast_enabled?'Google im Sendestream ausgeschaltet':'Kein Google-Key gespeichert');
  const maps=await loadGoogleRadarSDK(config.key);
  if(state!==radarState||!container.isConnected)return;
  if(googleRadarAuthFailed)throw Error('Google-Key, Abrechnung oder Website-Beschränkung prüfen');
  if(!googleRadarHost){googleRadarHost=document.createElement('div');googleRadarHost.className='radar-google-map';googleRadarHost.setAttribute('aria-label','Google-Karte mit separater RainViewer-Radarüberlagerung');}
  container.prepend(googleRadarHost);googleRadarHost.hidden=false;
  const update=()=>{
   if(state!==radarState||!container.isConnected||!googleRadarMap)return;
   const effective=radarGeometry(state.meta.latitude,state.zoom,state.radius).effective;
   const zoom=googleRadarZoom(container.clientWidth,effective,container.clientHeight);
   googleRadarMap.setOptions({center:{lat:state.meta.latitude,lng:state.meta.longitude},zoom,mapTypeId:channel.radar_map_style.slice(7),tilt:0,heading:0});
  };
  const reused=!!googleRadarMap;
  if(!googleRadarMap)googleRadarMap=new maps.Map(googleRadarHost,{disableDefaultUI:true,gestureHandling:'none',keyboardShortcuts:false,clickableIcons:false,isFractionalZoomEnabled:true,renderingType:maps.RenderingType?.RASTER});
  maps.event.trigger(googleRadarMap,'resize');
  googleRadarObserver?.disconnect();googleRadarObserver=new ResizeObserver(update);googleRadarObserver.observe(container);
  // Keep the fallback until the official map has loaded its tiles.
  const loaded=reused?Promise.resolve():new Promise((resolve,reject)=>{const timer=setTimeout(()=>{maps.event.removeListener(listener);reject(Error('Google-Karte nicht vollständig geladen'));},20000);const listener=maps.event.addListenerOnce(googleRadarMap,'tilesloaded',()=>{clearTimeout(timer);resolve();});});
  update();await loaded;
  if(state!==radarState||!container.isConnected||googleRadarAuthFailed)return;
  container.classList.add('google-active');note.textContent='Karte: Google Maps · Radar: RainViewer · Satellitenbilder sind Archivaufnahmen';
  const credit=document.querySelector('.radar-foot a:nth-of-type(2)');if(credit){credit.textContent='Karte: Google Maps';credit.href='https://maps.google.com/';}
 }catch(_error){googleRadarFallback(state,_error.message);}
}
