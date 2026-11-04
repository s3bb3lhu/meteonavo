const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx=vm.createContext({setInterval(){}});vm.runInContext(fs.readFileSync('app/static/radar.js','utf8'),ctx);
const center=vm.runInContext('radarProject(8,50,8,50,6)',ctx);assert.equal(center[0],400);assert.equal(center[1],150);
const tile=vm.runInContext('radarProject(8+360/64,50,8,50,6)',ctx);assert.equal(tile[0],1200,'A source tile width must project to 800 viewport units');
assert.ok(vm.runInContext('radarProject(8,51,8,50,6)[1]',ctx)<150,'North is upwards');
assert.ok(vm.runInContext('radarProject(7,50,8,50,6)[0]',ctx)<400,'West is left');
console.log('Radar: Web-Mercator center, source tile scale, north and west orientation OK');

for(const radius of [1,2,5,10,25,50,100,200,500,2000,5000]){
 const g=vm.runInContext(`radarGeometry(50,6,${radius})`,ctx);
 assert.ok(g.source>=1&&g.source<=7);
 assert.ok(g.size>=800,'Source image must cover the entire viewport');
 const kmPerPixel=Math.cos(50*Math.PI/180)*40075/(800*2**g.effective);
 assert.ok(Math.abs(kmPerPixel*400-radius)<1e-8,'Requested distance reaches the east/west edge');
 assert.ok(Math.abs(g.size/800-2**(g.effective-g.source))<1e-8,'Image and map use identical scale');
}
console.log('Radar distance 1–5000 km: projection, image coverage and distance OK');
assert.equal(vm.runInContext('radarScaleLabel(50,radarGeometry(50,6,1).effective)',ctx),'250 m','A 1 km radius must show a useful scale instead of zero km');

vm.runInContext("var channel={radar_map_style:'streets'};var broadcastRender=true;var location={search:''};",ctx);
ctx.URLSearchParams=URLSearchParams;
for(const zoom of [1,4,7,10]){
 const tiles=vm.runInContext(`radarStreetTiles({latitude:50,longitude:8},${zoom})`,ctx);
 assert.ok((tiles.match(/<image /g)||[]).length<=20,'Only visible tiles are requested');
 assert.ok(tiles.includes('/api/radar/map/streets/'));
}
vm.runInContext("channel.radar_map_style='satellite-night'",ctx);
assert.ok(vm.runInContext('radarStreetTiles({latitude:38.64,longitude:.02},7)',ctx).includes('/api/radar/map/satellite/'));
vm.runInContext("channel.radar_map_style='overview'",ctx);
assert.equal(vm.runInContext('radarStreetTiles({latitude:50,longitude:8},7)',ctx),'');
console.log('Radar: bounded visible street/satellite tiles, shared projection and overview OK');
