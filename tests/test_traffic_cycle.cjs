const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');let now=100000;const content={dataset:{page:'traffic'},innerHTML:''};
const ctx=vm.createContext({Date:class extends Date{static now(){return now}},setInterval(){},id:1,channel:{latitude:50,longitude:8,traffic_radius_km:100,seconds:20},lastSwitch:now,$:()=>content,escapeText:s=>String(s??''),num:(n,u='')=>String(n)+u});
vm.runInContext(fs.readFileSync('app/static/regional.js','utf8'),ctx);
function data(n,status='ok'){return {items:Array.from({length:n},(_,i)=>({id:i,title:'Meldung '+(i+1),description:'Beschreibung',distance_km:i,road:'A3'})),status,radius_km:100,source:'Test',message:''};}
function enter(n,status='ok'){ctx.lastSwitch=now;ctx.testData=data(n,status);vm.runInContext("syncTrafficVisit('current');syncTrafficVisit('traffic');renderRegional('traffic',testData)",ctx);}
for(const [items,pages] of [[9,3],[6,2],[3,1],[1,1]]){
 enter(items);assert.equal(vm.runInContext('trafficPageSeconds(20)',ctx),pages*20);
 for(let i=0;i<pages;i++){vm.runInContext('tickTraffic()',ctx);assert.equal(vm.runInContext('trafficCurrentPage()',ctx),i);assert.ok(content.innerHTML.includes('Seite '+(i+1)+'/'+pages));now+=20000;}
}
enter(9);ctx.nextData=data(3);vm.runInContext("renderRegional('traffic',nextData)",ctx);assert.equal(vm.runInContext('trafficPageCount(trafficVisit.data)',ctx),3,'Current cycle keeps a stable snapshot');
now+=60000;enter(3);assert.equal(vm.runInContext('trafficPageSeconds(20)',ctx),20,'Next visit uses the smaller dataset');
enter(0);assert.equal(vm.runInContext('trafficPageSeconds(20)',ctx),10);assert.ok(content.innerHTML.includes('Keine Verkehrsmeldungen'));
enter(0,'error');assert.equal(vm.runInContext('trafficPageSeconds(20)',ctx),10);assert.ok(!content.innerHTML.includes('>Keine Verkehrsmeldungen<'),'Source failure must never claim no traffic');
now+=1000;ctx.lastSwitch=now;vm.runInContext("syncTrafficVisit('current');syncTrafficVisit('traffic')",ctx);now+=5000;ctx.testData=data(6);vm.runInContext("renderRegional('traffic',testData)",ctx);assert.equal(vm.runInContext('trafficPageSeconds(20)',ctx),45,'Loading time must not shorten display time');
console.log('Verkehr: 3/2/1 Seiten vollständig, geänderte Anzahl beim nächsten Besuch, 10 Sekunden Leerhinweis und Fehlerunterscheidung OK');
