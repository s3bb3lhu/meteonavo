const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context=vm.createContext({});vm.runInContext(fs.readFileSync('app/static/weather-icons.js','utf8'),context);
const expected={0:'clear',1:'fair',2:'partly',3:'overcast',45:'fog',48:'fog',51:'drizzle',53:'drizzle',55:'drizzle',56:'ice-drizzle',57:'ice-drizzle',61:'rain',63:'rain',65:'rain',66:'ice-rain',67:'ice-rain',71:'snow',73:'snow',75:'snow',77:'snow-grains',80:'showers',81:'showers',82:'showers',85:'snow-showers',86:'snow-showers',95:'storm',96:'hail',99:'hail'};
const ids=new Set();
for(const [code,kind] of Object.entries(expected)){
 assert.equal(vm.runInContext(`weatherKind(${code})`,context),kind);
 for(const night of [false,true]){
  const svg=vm.runInContext(`weatherArt(${code},false,${night})`,context);
  assert.match(svg,new RegExp(`data-weather-kind="${kind}"`));assert.match(svg,/aria-label=/);
  assert.ok(!svg.includes('undefined'));
  for(const id of svg.matchAll(/id="([^"]+)"/g)){assert.ok(!ids.has(id[1]));ids.add(id[1]);}
  if(['overcast','fog','rain','snow','storm','hail'].includes(kind))assert.ok(!svg.includes('class="wx-sun"'));
 }
}
assert.equal(vm.runInContext('weatherKind(null)',context),'unknown');
assert.equal(vm.runInContext('weatherKind(999)',context),'unknown');
assert.match(vm.runInContext('weatherArt(0,false,true)',context),/moon-icon/);
assert.ok(!vm.runInContext('weatherArt(0,false,true)',context).includes('wx-sun'));
assert.equal(vm.runInContext('weatherPhotoCell(0,true)',context),1);
assert.equal(vm.runInContext('weatherPhotoCell(3)',context),6);
assert.equal(vm.runInContext('weatherPhotoCell(95)',context),14);
assert.match(vm.runInContext('weatherArt(65)',context),/photographic-atlas-v1.webp/);
console.log('28 WMO-Codes, Tag/Nacht, eindeutige SVG-Verläufe und korrekte Wolken-/Niederschlagsgrafiken OK');
