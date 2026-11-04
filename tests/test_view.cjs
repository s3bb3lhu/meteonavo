// Browser-free rendering checks with a small DOM fixture; no image/codec claim.
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const elements={};const make=()=>({textContent:'',innerHTML:'',children:[],dataset:{},style:{setProperty(){}},classList:{toggle(){},add(){},remove(){}},setAttribute(){},replaceChildren(){this.children=[];},append(child){this.children.push(child);},scrollWidth:2000});const el=id=>elements[id]??=make();
const context=vm.createContext({location:{pathname:'/view/1',search:''},URLSearchParams,document:{getElementById:el,querySelector:el,createElement:make,documentElement:{style:{setProperty(){}}}},innerWidth:1280,innerHeight:720,addEventListener(){},requestAnimationFrame:f=>f(),setInterval(){},fetch:()=>new Promise(()=>{}),Date,Number,String,Error});
vm.runInContext(fs.readFileSync('app/static/designs.js','utf8'),context);
vm.runInContext(fs.readFileSync('app/static/weather-icons.js','utf8'),context);
vm.runInContext(fs.readFileSync('app/static/scenes.js','utf8'),context);
vm.runInContext(fs.readFileSync('app/static/view.js','utf8'),context);
vm.runInContext(`channel={location:'Ort',pages:['current'],seconds:20};weather={stale:false,fetched_at:Date.now()/1000,data:{timezone:'Europe/Berlin',current:{time:'2026-11-02T12:00',temperature_2m:10,weather_code:3,wind_speed_10m:15,wind_direction_10m:90,relative_humidity_2m:70,apparent_temperature:8},daily:{time:['2026-11-02'],weather_code:[3],temperature_2m_max:[12],temperature_2m_min:[4],precipitation_probability_max:[50]},hourly:{time:['2026-11-02T12:00'],temperature_2m:[10],rain:[1],snowfall:[0],precipitation_probability:[50],wind_speed_10m:[15]}}};`,context);
for(const kind of ['current','daily','hourly','wind','precipitation','radar']){
 vm.runInContext(`channel.pages=['${kind}'];render();`,context);
 assert.ok(el('content').innerHTML.length>40,kind);
 assert.ok(!el('content').innerHTML.includes('undefined'),kind);
}
assert.match(el('content').textContent,/Radaransicht wird geladen/);
vm.runInContext("weather.stale=true;render();",context);assert.match(el('status').textContent,/VERALTET/);
assert.equal(vm.runInContext("escapeText('<script>')",context),'&lt;script&gt;');
vm.runInContext("channel.pages=['current','daily'];lastSwitch=0;render();",context);assert.match(el('title').textContent,/7 Tage/);
console.log('6 Wetterseiten, Radarhinweis, Veraltet-Markierung, Escaping und Seitenwechsel OK');
vm.runInContext(`paintNews({enabled:true,source:'Quelle',headlines:['<img src=x onerror=alert(1)>','Zweite Meldung'],stale:false});`,context);
assert.equal(el('ticker-track').children[0].textContent,'<img src=x onerror=alert(1)>   •   Zweite Meldung');
assert.equal(el('ticker-track').children.length,2);
const first=el('ticker-track').children[0];
vm.runInContext(`paintNews({enabled:true,source:'Quelle',headlines:['<img src=x onerror=alert(1)>','Zweite Meldung'],stale:true});`,context);
assert.equal(el('ticker-track').children[0],first,'Feed-Poll darf Laufband nicht neu starten');
assert.match(el('ticker-label').textContent,/VERALTET/);
vm.runInContext('paintNews({enabled:false});',context);assert.equal(el('ticker').hidden,true);
console.log('Ticker: Text statt HTML, nahtlose Wiederholung, stabiler Lauf, Ausfallstatus und Abschalten OK');

vm.runInContext("warningData={status:'ok',items:[{headline:'TEST WARNUNG',area:'Testkreis',level:3,onset:Date.now()/1000,expires:Date.now()/1000+3600,source:'Testquelle'}]};paintNews({enabled:true,headlines:['RSS NACHRICHT'],source:'RSS',stale:false});",context);
assert.ok(el('ticker-track').children[0].textContent.indexOf('TEST WARNUNG')<el('ticker-track').children[0].textContent.indexOf('RSS NACHRICHT'));
assert.equal(el('ticker').dataset.warningLevel,3);
vm.runInContext("lastRssData={enabled:false};warningData={status:'ok',items:[{expires:1}]};refreshWarningTicker();",context);
assert.equal(el('ticker').dataset.warningLevel,'');
assert.ok(!el('ticker-track').children.some(c=>c.textContent.includes('TEST WARNUNG')));
assert.ok(!el('status').textContent.includes('Abruf '));
console.log('Warnungen vor RSS, Ablauf entfernt Warntext und Warnstufe, keine Abrufzeit OK');
