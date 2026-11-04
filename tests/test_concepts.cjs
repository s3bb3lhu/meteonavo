const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');const c=vm.createContext({designPresets:{},cinematicFamily:new Set(),sceneThemes:new Set()});vm.runInContext(fs.readFileSync('app/static/concepts.js','utf8'),c);
assert.equal(vm.runInContext('Object.keys(conceptPresets).length',c),8);
for(const [period,weather,expected] of [['dawn','clear','dawn'],['day','clear','day'],['day','rain','rain'],['dusk','clear','dusk'],['night','clouds','night'],['night','rain','night'],['night','snow','snow']])assert.equal(vm.runInContext(`landscapeChoice('auto','${period}','${weather}')`,c),expected);
assert.equal(vm.runInContext("landscapeChoice('off','day','clear')",c),null);
assert.equal(vm.runInContext("landscapeChoice('rain','night','snow')",c),'rain');
for(const [x,y,w,h] of vm.runInContext('Object.values(landscapeTiles)',c)){assert.ok(x>=0&&y>=0&&x+w<=1752&&y+h<=897);}
console.log('Eight concepts, six landscape regions, manual override, night rain and snowfall selection OK');
