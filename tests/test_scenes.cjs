const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context=vm.createContext({URLSearchParams,Date,Intl,location:{search:''}});
vm.runInContext(fs.readFileSync('app/static/designs.js','utf8'),context);
vm.runInContext(fs.readFileSync('app/static/weather-icons.js','utf8'),context);
vm.runInContext(fs.readFileSync('app/static/scenes.js','utf8'),context);
vm.runInContext(`const sample={timezone:'Europe/Berlin',daily:{time:['2026-11-02'],sunrise:['2026-11-02T07:15'],sunset:['2026-11-02T17:00']},current:{is_day:1}};`,context);
for(const [time,expected] of [['06:15','dawn'],['12:00','day'],['16:00','dusk'],['22:00','night']]){
 assert.equal(vm.runInContext(`dayPeriod(sample,new Date('2026-11-02T${time}:00Z'))`,context),expected);
}
assert.equal(vm.runInContext("dayPeriod({timezone:'America/New_York',daily:{time:['2026-11-01'],sunrise:['2026-11-01T06:30'],sunset:['2026-11-01T16:50']},current:{is_day:1}},new Date('2026-11-01T11:30:00Z'))",context),'dawn');
assert.equal(vm.runInContext("dayPeriod({timezone:'UTC',daily:{},current:{is_day:0}})",context),'night');
assert.equal(vm.runInContext('dayPeriod(null)',context),'unknown');
for(const [code,kind] of [[0,'clear'],[1,'clouds'],[3,'clouds'],[45,'fog'],[51,'rain'],[67,'rain'],[71,'snow'],[77,'snow'],[80,'rain'],[85,'snow'],[95,'storm'],[99,'storm'],[100,'unknown'],[null,'unknown']]){
 assert.equal(vm.runInContext(`weatherScene(${JSON.stringify(code)})`,context),kind);
}
assert.match(vm.runInContext('weatherArt(0,false,true)',context),/moon-icon/);
assert.ok(!vm.runInContext('weatherArt(0,false,true)',context).includes('class="sun"'));
console.log('Zeitzonen, Sonnenauf-/untergang, Dämmerung, DST, Polarnacht, Wettercodes und Nachtsymbol OK');
