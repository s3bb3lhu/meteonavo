const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx=vm.createContext({setInterval(){},escapeText:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'),num:(n,u='')=>String(n)+u,weatherArt:()=>'<svg></svg>'});
vm.runInContext(fs.readFileSync('app/static/regional.js','utf8'),ctx);
const data={map:{name:'Deutschland',geometry:{coordinates:[[[5,47],[15,47],[15,55],[5,55],[5,47]]]}},places:Array.from({length:8},(_,i)=>({name:i===0?'<Ort>':'Stadt '+i,latitude:50+i*.05,longitude:10+i*.05,current:{temperature_2m:10+i,weather_code:3,is_day:1}}))};
ctx.data=data;const svg=vm.runInContext('countryGraphic(data)',ctx);
assert.equal((svg.match(/class="country-temperature"/g)||[]).length,8);
assert.ok(svg.includes('&lt;Ort&gt;')&&!svg.includes('<Ort>'));
assert.ok(svg.includes('17°')&&svg.includes('class="country-leader"'));
const boxes=[...svg.matchAll(/<rect x="([\d.]+)" y="([\d.]+)" width="160" height="65"/g)].map(m=>({x:+m[1],y:+m[2]}));
assert.equal(boxes.length,8);
for(let i=0;i<boxes.length;i++)for(let j=0;j<i;j++){const a=boxes[i],b=boxes[j];assert.ok(a.x>=b.x+160||b.x>=a.x+160||a.y>=b.y+65||b.y>=a.y+65,'Labels must not overlap');}
console.log('TV-Landeskarte: Ortsnamen, echte Temperaturwerte, Escaping und kollisionsfreie Beschriftung OK');
