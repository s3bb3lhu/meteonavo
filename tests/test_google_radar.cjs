const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('app/static/google-radar.js','utf8');
async function scenario(){
 let external=0,constructed=0,config={key:'browser-test-key',configured:true,broadcast_enabled:false},lastOptions,listener;
 const nodes={},classes=new Set(),credit={};
 const container=nodes['radar-geography']={isConnected:true,clientWidth:1000,clientHeight:500,classList:{add:c=>classes.add(c),remove:c=>classes.delete(c)},prepend(){}};
 nodes['radar-map']={};
 const document={getElementById:id=>nodes[id],createElement:tag=>({tag,setAttribute(){}}),querySelector:s=>s.includes('nth-of-type')?credit:{append:node=>nodes[node.id]=node},head:{append:script=>{external++;assert.ok(script.src.startsWith('https://maps.googleapis.com/maps/api/js?'));queueMicrotask(()=>ctx.window.meteonavoGoogleReady());}}};
 class Map{constructor(){constructed++;}setOptions(options){lastOptions=options;if(listener){const fn=listener;listener=null;queueMicrotask(fn);}}}
 const maps={Map,RenderingType:{RASTER:'RASTER'},event:{trigger(){},addListenerOnce(_m,_event,fn){listener=fn;return fn;},removeListener(){listener=null;}}};
 const ctx=vm.createContext({window:{google:{maps}},document,URLSearchParams,setTimeout,clearTimeout,setInterval(){},ResizeObserver:class{observe(){}disconnect(){}},fetch:async()=>({ok:true,json:async()=>config})});
 vm.runInContext(fs.readFileSync('app/static/radar.js','utf8'),ctx);vm.runInContext(source,ctx);
 vm.runInContext("var channel={radar_map_style:'google-hybrid'};var id=1,broadcastRender=false,location={search:''};radarState={zoom:7,radius:1,meta:{latitude:50,longitude:8}};",ctx);
 await vm.runInContext('mountGoogleRadar(radarState)',ctx);
 assert.equal(constructed,1);assert.equal(external,1);assert.ok(classes.has('google-active'));
 assert.equal(lastOptions.center.lat,50);assert.equal(lastOptions.center.lng,8);assert.equal(lastOptions.mapTypeId,'hybrid');assert.equal(lastOptions.tilt,0);
 // The SVG uses xMidYMid slice. A tall viewport must use the same crop scale.
 const effective=vm.runInContext('radarGeometry(50,7,1).effective',ctx);
 assert.ok(Math.abs(256*2**lastOptions.zoom-Math.max(1000,500*800/300)*2**effective)<1e-6);
 assert.equal(credit.textContent,'Karte: Google Maps');
 await vm.runInContext('mountGoogleRadar(radarState)',ctx);
 assert.equal(constructed,1,'Rotating back to radar must reuse the map');assert.equal(external,1,'SDK loads once');
 config={key:'',configured:true,broadcast_enabled:false};
 await vm.runInContext('broadcastRender=true;mountGoogleRadar(radarState)',ctx);
 assert.ok(!classes.has('google-active'));assert.match(nodes['radar-google-status'].textContent,/Sendestream ausgeschaltet/);
 assert.equal(credit.textContent,vm.runInContext('radarMapCredit()',ctx));assert.equal(external,1);
 config={key:'different-key',configured:true,broadcast_enabled:true};
 await vm.runInContext('mountGoogleRadar(radarState)',ctx);
 assert.match(nodes['radar-google-status'].textContent,/neu laden/);assert.equal(external,1);
 ctx.window.gm_authFailure();assert.ok(!classes.has('google-active'));assert.match(nodes['radar-google-status'].textContent,/Website-Beschränkung/);
 // Missing keys and existing providers must not contact Google at all.
 const fresh=vm.createContext({document,setTimeout,clearTimeout,URLSearchParams,fetch:async()=>({ok:true,json:async()=>({key:'',configured:false})}),radarState:{},id:1,broadcastRender:false,radarRequestedGoogle:()=>true,radarBaseStyle:()=> 'streets',radarMapCredit:()=> 'OSM'});
 vm.runInContext(source,fresh);await vm.runInContext('mountGoogleRadar(radarState)',fresh);assert.equal(external,1);
}
scenario().then(()=>console.log('Google radar: projection, aspect crop, SDK/map reuse, key change, auth failure and broadcast/key fallback OK')).catch(e=>{console.error(e);process.exitCode=1;});
