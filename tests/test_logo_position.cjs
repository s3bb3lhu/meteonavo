const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx=vm.createContext({broadcastRender:true});vm.runInContext(fs.readFileSync('app/static/logo-position.js','utf8'),ctx);
let box=vm.runInContext('logoEditorGeometry(100,590,200)',ctx);assert.equal(box.logo_width,100);assert.equal(box.logo_x,50);assert.equal(box.logo_mode,'free');
box=vm.runInContext('logoEditorGeometry(400,2000,2000)',ctx);assert.equal(box.logo_width,250);assert.equal(box.logo_x,100);assert.equal(box.logo_y,100);
box=vm.runInContext('logoEditorGeometry(1,-20,-10)',ctx);assert.equal(box.logo_width,30);assert.equal(box.logo_x,0);assert.equal(box.logo_y,0);
for(const width of [30,90,150,250]){ctx.width=width;box=vm.runInContext('logoEditorGeometry(width,1280-width,632-Math.min(100,width*.65))',ctx);assert.equal(box.logo_x,100);assert.equal(box.logo_y,100);}
console.log('Logo-Editor: begrenzte Größe, genaue Prozentpositionen, Schutz des Newstickers und keine Aktivierung im Broadcast OK');
