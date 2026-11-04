// Official YouTube embed only: no extraction, downloads or access restriction bypass.
let youtubeCameraApiPromise=null;
function youtubeCameraError(code){return ({2:'Ungültiger YouTube-Videolink',5:'YouTube-Video in diesem Browser nicht abspielbar',100:'YouTube-Video wurde entfernt, ist privat oder nicht verfügbar',101:'Der Anbieter erlaubt keine YouTube-Einbettung',150:'Der Anbieter erlaubt keine YouTube-Einbettung',153:'YouTube akzeptiert die Player-Identifikation nicht. Browser/Server-Adresse und Referrer prüfen.'})[code]||'YouTube-Wiedergabe blockiert oder derzeit nicht verfügbar';}
function youtubeCameraApi(){
 if(window.YT?.Player)return Promise.resolve(window.YT);
 if(youtubeCameraApiPromise)return youtubeCameraApiPromise;
 youtubeCameraApiPromise=new Promise((resolve,reject)=>{let done=false;const script=document.createElement('script'),previous=window.onYouTubeIframeAPIReady;const finish=error=>{if(done)return;done=true;clearTimeout(timer);if(error){script.remove();youtubeCameraApiPromise=null;reject(error);}else resolve(window.YT);};const timer=setTimeout(()=>finish(Error('YouTube-Player konnte nicht geladen werden')),20000);window.onYouTubeIframeAPIReady=()=>{try{if(typeof previous==='function')previous();}catch(_){}if(window.YT?.Player)finish();};script.src='https://www.youtube.com/iframe_api';script.async=true;script.onerror=()=>finish(Error('YouTube-Player konnte nicht geladen werden'));document.head.append(script);});return youtubeCameraApiPromise;
}
function stopYoutubeCamera(state){if(!state)return;clearTimeout(state.youtubeTimer);state.youtubeTimer=null;if(state.youtube){try{state.youtube.destroy();}catch(_){}state.youtube=null;}}
async function mountYoutubeCamera(state,item,media,sequence){
 const current=()=>state===cameraView&&sequence===state.sequence&&document.getElementById('camera-media');
 const failed=message=>{if(!current())return;cameraNote(message,true);state.forceMount=true;state.mounted=Date.now()-Math.max(0,(state.rotationSeconds||60)-5)*1000;};
 if(!/^[A-Za-z0-9_-]{11}$/.test(item.youtube_id||'')){failed('Ungültiger YouTube-Videolink');return;}
 const url=new URL('https://www.youtube-nocookie.com/embed/'+item.youtube_id);for(const [key,value] of Object.entries({enablejsapi:1,origin:location.origin,autoplay:1,mute:1,playsinline:1,controls:broadcastRender?0:1,rel:0}))url.searchParams.set(key,value);
 const frame=document.createElement('iframe');frame.id='camera-player';frame.src=url.href;frame.title=item.name;frame.allow='autoplay; encrypted-media; picture-in-picture; fullscreen';frame.allowFullscreen=true;frame.referrerPolicy='strict-origin-when-cross-origin';media.append(frame);cameraNote('YouTube-Player wird geladen · Wiedergabe noch nicht bestätigt');
 try{const YT=await youtubeCameraApi();if(!current())return;
  state.youtube=new YT.Player(frame,{events:{onReady:event=>{if(!current()){event.target.destroy();return;}event.target.mute();event.target.playVideo();if(event.target.getPlayerState?.()===1){clearTimeout(state.youtubeTimer);cameraNote('YouTube-Video wird wiedergegeben · Aufnahmezeit und Live-Status siehe Anbieter');}else cameraNote('YouTube bereit · Wiedergabe wird gestartet');},onStateChange:event=>{if(!current())return;if(event.data===1){clearTimeout(state.youtubeTimer);cameraNote('YouTube-Video wird wiedergegeben · Aufnahmezeit und Live-Status siehe Anbieter');}else if(event.data===3)cameraNote('YouTube puffert …');else if(event.data===0)failed('YouTube-Video oder Liveübertragung beendet');},onError:event=>{clearTimeout(state.youtubeTimer);failed(youtubeCameraError(event.data));},onAutoplayBlocked:()=>failed('YouTube-Autoplay blockiert. Wiedergabe im Player starten.')}});
  state.youtubeTimer=setTimeout(()=>failed('YouTube wurde nicht gestartet. Freigabe, Region oder erforderliche Anmeldung beim Anbieter prüfen.'),18000);
 }catch(error){failed(error.message);}
}
