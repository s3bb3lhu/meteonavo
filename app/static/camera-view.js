let cameraView=null;const cameraCursor=new Map();
function cameraResumeIndex(signature,items){const previous=items.findIndex(x=>x.id===cameraCursor.get(signature));return items.length?(previous+1)%items.length:0;}
function cameraPageSeconds(fallback){return cameraView?.items.length?Math.max(fallback,cameraView.items.length*(cameraView.rotationSeconds||60)):fallback;}
function pauseCameraVideo(){const v=document.getElementById('camera-video');if(v){v.pause();v.removeAttribute('src');v.load();}}
function stopCamera(){
 if(!cameraView)return;cameraView.sequence++;if(typeof stopYoutubeCamera==='function')stopYoutubeCamera(cameraView);pauseCameraVideo();if(cameraView.hls)cameraView.hls.destroy();if(cameraView.objectUrl)URL.revokeObjectURL(cameraView.objectUrl);clearInterval(cameraView.timer);cameraView=null;
}
function cameraNote(text,error=false){const note=document.getElementById('camera-state');if(note){note.textContent=text;note.classList.toggle('camera-error',error);}}
async function cameraHlsLibrary(){
 if(window.Hls)return window.Hls;
 await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='/assets/hls.js';script.onload=resolve;script.onerror=reject;document.head.append(script);});return window.Hls;
}
async function cameraSnapshot(state,item,sequence){
 let pendingUrl=null;
 try{
  const response=await fetch(item.media+(item.media.includes('?')?'&':'?')+'t='+Date.now(),{cache:'no-store'});if(!response.ok)throw Error('Kein aktuelles Kamerabild verfügbar');
  const blob=await response.blob();if(state!==cameraView||sequence!==state.sequence)return;
  const url=URL.createObjectURL(blob),image=new Image();pendingUrl=url;image.src=url;await image.decode();if(state!==cameraView||sequence!==state.sequence){URL.revokeObjectURL(url);return;}
  const previous=state.objectUrl;state.objectUrl=url;image.id='camera-image';image.alt=item.name;document.getElementById('camera-media').replaceChildren(image);if(previous)URL.revokeObjectURL(previous);
  const zone=weather?.data?.timezone||'UTC',captured=Number(response.headers.get('X-Camera-Captured-At'))||null,file=response.headers.get('X-Camera-File-Date'),imageTime=captured?new Date(captured*1000):file?new Date(file):null,age=imageTime?(Date.now()-imageTime.getTime())/1000:null;
  cameraNote(`${age>1800?'BILD VERALTET · ':''}Aktualisiertes Einzelbild · ${imageTime?(captured?'Aufnahmezeit ':'Dateistand ')+imageTime.toLocaleString('de-DE',{timeZone:zone}):'Aufnahmezeit vom Anbieter nicht angegeben'}`,age>1800);
 }catch(e){if(pendingUrl)URL.revokeObjectURL(pendingUrl);if(state===cameraView&&sequence===state.sequence){document.getElementById('camera-media').replaceChildren();cameraNote(e.message,true);}}
}
async function mountCamera(state,index){
 if(state!==cameraView)return;const sequence=++state.sequence;if(typeof stopYoutubeCamera==='function')stopYoutubeCamera(state);pauseCameraVideo();state.index=index;
 if(state.hls){state.hls.destroy();state.hls=null;}if(state.objectUrl){URL.revokeObjectURL(state.objectUrl);state.objectUrl=null;}
 const item=state.items[index],media=document.getElementById('camera-media');media.replaceChildren();state.mounted=Date.now();state.lastImage=0;
 if(!item){document.getElementById('camera-name').textContent='Keine Wetterkamera eingerichtet';cameraNote('Keine direkt darstellbare Kamera im Umkreis eingerichtet.',true);return;}
 cameraCursor.set(state.signature,item.id);
 document.getElementById('camera-name').textContent=item.name;
 document.getElementById('camera-source').textContent=`${item.source||'Eigene Quelle'}${item.distance_km!==null?' · '+item.distance_km+' km':''}`;
 const link=document.getElementById('camera-provider');link.href=item.url||item.media;link.hidden=broadcastRender;
 document.getElementById('camera-position').textContent=`${index+1} / ${state.items.length}`;
 if(!item.available){cameraNote(item.message||'Kameraquelle nicht erreichbar',true);media.innerHTML='<div class="camera-placeholder">Kamera momentan nicht verfügbar</div>';return;}
 cameraNote('Anbieteransicht wird geladen · Aufnahmezeit siehe Kamerabild');
 if(item.kind==='iframe'){
  const frame=document.createElement('iframe');frame.id='camera-player';frame.src=item.media;frame.title=item.name;frame.allow='autoplay; fullscreen';frame.setAttribute('sandbox','allow-scripts allow-same-origin');frame.referrerPolicy='strict-origin-when-cross-origin';
  frame.onerror=()=>cameraNote('Anbieterplayer konnte nicht geladen werden',true);
  frame.onload=()=>{if(state===cameraView&&sequence===state.sequence)cameraNote('Anbieteransicht · Aufnahmezeit im Kamerabild beachten');};media.append(frame);
 }else if(item.kind==='youtube'){await mountYoutubeCamera(state,item,media,sequence);}
 else if(item.kind==='image'){state.lastImage=Date.now();await cameraSnapshot(state,item,sequence);}
 else{
  const video=document.createElement('video');video.id='camera-video';video.autoplay=true;video.muted=true;video.playsInline=true;video.controls=!broadcastRender;media.append(video);
  video.onplaying=()=>cameraNote('Videostream wird wiedergegeben · Aufnahmezeit siehe Anbieter');video.onwaiting=()=>cameraNote('Videostream puffert …');video.onerror=()=>{state.forceMount=true;cameraNote('Kameravideo momentan nicht abspielbar',true);};
  try{
   if(video.canPlayType('application/vnd.apple.mpegurl'))video.src=item.media;
   else{const Hls=await cameraHlsLibrary();if(state!==cameraView||sequence!==state.sequence)return;if(!Hls.isSupported())throw Error('Browser unterstützt dieses Videoformat nicht');state.hls=new Hls({maxBufferLength:8,backBufferLength:0});state.hls.loadSource(item.media);state.hls.attachMedia(video);state.hls.on(Hls.Events.ERROR,(_,e)=>{if(e.fatal){state.forceMount=true;cameraNote('Kamerastream unterbrochen',true);}});}
   await video.play();
  }catch(e){cameraNote(e.name==='NotAllowedError'?'Wiedergabe im Player starten':e.message,true);}
 }
}
async function showCameraPage(){
 const signature=JSON.stringify([id,channel.latitude,channel.longitude]);
 if(cameraView?.signature===signature&&document.getElementById('camera-stage'))return;
 stopCamera();const state=cameraView={signature,sequence:0,index:0,items:[],hls:null,objectUrl:null,mounted:0,lastImage:0,lastCheck:0,paused:false,timer:null};
 $('content').innerHTML='<div class="camera-heading"><div><strong id="camera-name">Wetterkamera wird geladen …</strong><small id="camera-source"></small></div><div class="camera-actions"><button id="camera-prev" type="button">‹</button><span id="camera-position"></span><button id="camera-next" type="button">›</button><button id="camera-pause" type="button">Wechsel pausieren</button><a id="camera-provider" target="_blank" rel="noopener">Anbieter ↗</a></div></div><div id="camera-stage"><div id="camera-media"></div></div><div id="camera-state" role="status">Kameraquellen werden geprüft …</div>';
 document.getElementById('camera-prev').onclick=()=>{if(state.items.length)mountCamera(state,(state.index-1+state.items.length)%state.items.length);};document.getElementById('camera-next').onclick=()=>{if(state.items.length)mountCamera(state,(state.index+1)%state.items.length);};
 document.getElementById('camera-pause').onclick=e=>{state.paused=!state.paused;e.target.textContent=state.paused?'Wechsel fortsetzen':'Wechsel pausieren';};
 async function refresh(){
  state.lastCheck=Date.now();try{
   const r=await fetch(`/api/cameras/${id}`,{cache:'no-store'});if(!r.ok)throw Error('Kameraquellen momentan nicht erreichbar');const data=await r.json();if(state!==cameraView)return;
   const previous=state.items[state.index],old=JSON.stringify(state.items.map(x=>[x.id,x.media,x.available]));state.items=data.items.some(x=>x.available)?data.items.filter(x=>x.available):data.items;state.rotationSeconds=data.rotation_seconds||60;
   if(state.forceMount||!previous||old!==JSON.stringify(state.items.map(x=>[x.id,x.media,x.available]))){state.forceMount=false;await mountCamera(state,previous?Math.max(0,state.items.findIndex(x=>x.id===previous.id)):cameraResumeIndex(state.signature,state.items));}
  }catch(e){if(state===cameraView){state.forceMount=true;document.getElementById('camera-media').replaceChildren();cameraNote(e.message,true);}}
 }
 await refresh();if(state!==cameraView)return;
 state.timer=setInterval(()=>{
  if(!document.getElementById('camera-stage')){stopCamera();return;}
  if(Date.now()-state.lastCheck>60000)refresh();
  if(state.items.length>1&&!state.paused&&Date.now()-state.mounted>(state.rotationSeconds||60)*1000)mountCamera(state,(state.index+1)%state.items.length);
  const item=state.items[state.index];if(item?.kind==='image'&&item.available&&Date.now()-state.lastImage>30000){state.lastImage=Date.now();cameraSnapshot(state,item,state.sequence);}
 },1000);
}
