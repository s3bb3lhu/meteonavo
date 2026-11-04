const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let note='',created,readyEvents,mutes=0,plays=0,destroyed=0;const timers=new Map();let count=0;
const media={append(frame){this.frame=frame},replaceChildren(){}};
class Player{constructor(frame,{events}){created=this;readyEvents=events;this.frame=frame}mute(){mutes++}playVideo(){plays++}getPlayerState(){return 0}destroy(){destroyed++}}
const ctx=vm.createContext({window:{YT:{Player}},document:{getElementById:id=>id==='camera-media'?media:null,createElement:()=>({}),head:{append(){}}},location:{origin:'http://server:7373'},URL,Date,setTimeout:f=>{timers.set(++count,f);return count},clearTimeout:id=>timers.delete(id),clearInterval(){},cameraNote:(text)=>note=text,broadcastRender:true,media,state:{sequence:1,rotationSeconds:30},item:{id:'yt',youtube_id:'M7lc1UVf-VE',name:'YouTube'}});
vm.runInContext('let cameraView=state',ctx);vm.runInContext(fs.readFileSync('app/static/youtube-camera.js','utf8'),ctx);vm.runInContext('cameraView=state',ctx);
(async()=>{await vm.runInContext('mountYoutubeCamera(state,item,media,1)',ctx);
const url=new URL(media.frame.src);assert.equal(url.hostname,'www.youtube-nocookie.com');assert.equal(url.searchParams.get('origin'),'http://server:7373');assert.equal(url.searchParams.get('enablejsapi'),'1');assert.equal(url.searchParams.get('mute'),'1');assert.equal(media.frame.referrerPolicy,'strict-origin-when-cross-origin');
readyEvents.onReady({target:created});assert.equal(mutes,1);assert.equal(plays,1);readyEvents.onStateChange({data:1});assert.ok(note.includes('wiedergegeben'));
readyEvents.onError({data:153});assert.ok(note.includes('Identifikation'));assert.equal(ctx.state.forceMount,true);
const previous=note;ctx.state.sequence=2;readyEvents.onError({data:100});assert.equal(note,previous,'Old-player events must not overwrite a new source');
vm.runInContext('stopYoutubeCamera(state)',ctx);assert.equal(destroyed,1);assert.equal(ctx.state.youtube,null);
assert.ok(vm.runInContext('youtubeCameraError(150)',ctx).includes('Einbettung'));
console.log('YouTube: offizieller Embed, Origin/Referrer, stummer Start, echte Statusereignisse, Fehler und Player-Cleanup OK');
})().catch(e=>{console.error(e);process.exitCode=1});
