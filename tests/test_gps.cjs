const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const ctx=vm.createContext({});vm.runInContext(fs.readFileSync('app/static/gps.js','utf8'),ctx);
for(const s of ['38.64, 0.02','38,64; 0,02','38.64 0.02'])assert.equal(JSON.stringify(vm.runInContext(`gpsPair(${JSON.stringify(s)})`,ctx)),JSON.stringify({latitude:38.64,longitude:.02}));
assert.equal(JSON.stringify(vm.runInContext("gpsPair('0, -180')",ctx)),JSON.stringify({latitude:0,longitude:-180}));
for(const s of ['91, 0','0, 181','hello','38,64,0,02',';','NaN, 2'])assert.throws(()=>vm.runInContext(`gpsPair(${JSON.stringify(s)})`,ctx));
console.log('GPS: Dezimalpunkt/-komma, Koordinatenpaar, Null, negative Werte und Bereichsprüfung OK');
