const $=id=>document.getElementById(id),channelId=Number(location.pathname.split('/').pop()),video=$('stream-video'),source=`/live/${channelId}/index.m3u8`;
let hls=null,started=false,checking=false,retryAt=0;
$('stream-url').value=location.origin+source;$('stream-preview').href=`/view/${channelId}`;$('stream-settings').href=`/settings?channel=${channelId}`;
function status(message){$('stream-status').textContent=message;}
function reset(){if(hls){hls.destroy();hls=null;}video.pause();video.removeAttribute('src');video.load();started=false;}
function start(){
 if(started)return;started=true;status('Videostream wird verbunden …');
 if(video.canPlayType('application/vnd.apple.mpegurl'))video.src=source;
 else if(window.Hls&&Hls.isSupported()&&window.MediaSource&&MediaSource.isTypeSupported('video/mp4; codecs="avc1.42E01E"')){
  hls=new Hls({liveSyncDurationCount:3,maxBufferLength:20});hls.loadSource(source);hls.attachMedia(video);
  hls.on(Hls.Events.MANIFEST_PARSED,()=>video.play().catch(e=>{if(started&&e.name==='NotAllowedError')status('Zum Starten auf die Wiedergabetaste im Video klicken.');}));
  hls.on(Hls.Events.ERROR,(_,data)=>{if(!data.fatal)return;reset();retryAt=Date.now()+5000;status('Verbindung zum Stream unterbrochen · automatischer Neuversuch …');});
 }else{started=false;retryAt=Date.now()+30000;status('Dieser Browser unterstützt die benötigte H.264/HLS-Wiedergabe nicht. Bitte einen aktuellen Chrome/Edge/Safari verwenden oder die HLS-Adresse unten in VLC öffnen.');return;}
 video.play().catch(()=>{});
}
async function check(){
 if(checking||Date.now()<retryAt)return;checking=true;
 try{
  const [a,b]=await Promise.all([fetch('/api/streams',{cache:'no-store'}),fetch('/api/channels',{cache:'no-store'})]);if(!a.ok||!b.ok)throw Error();
  const state=(await a.json()).find(s=>s.id===channelId),channel=(await b.json()).find(c=>c.id===channelId);
  if(!state||!channel){status('Kanal nicht vorhanden.');return;}$('stream-title').textContent=channel.name;
  if(!state.enabled){if(started)reset();status('Dieser Kanal ist deaktiviert. In den Kanaleinstellungen aktivieren und speichern.');}
  else if(!state.ready){if(started)reset();status('Stream startet oder Renderer ist noch nicht bereit · erneute Prüfung läuft …');}
  else start();
 }catch(_){status('Studio derzeit nicht erreichbar · erneute Prüfung läuft …');}finally{checking=false;}
}
video.addEventListener('playing',()=>{status('Stream läuft · H.264 / AAC · 720p');document.documentElement.dataset.playing='true';});
video.addEventListener('waiting',()=>{if(started)status('Videodaten werden gepuffert …');});
video.addEventListener('error',()=>{if(!started)return;reset();retryAt=Date.now()+5000;status('Videostream momentan nicht abspielbar · erneuter Verbindungsversuch folgt.');});
$('stream-sound').onclick=()=>{video.muted=!video.muted;$('stream-sound').textContent=video.muted?'Ton einschalten':'Ton ausschalten';if(!video.paused)return;video.play().catch(()=>status('Bitte die Wiedergabetaste im Video anklicken.'));};
$('stream-retry').onclick=()=>{reset();retryAt=0;check();};
check();setInterval(check,4000);
