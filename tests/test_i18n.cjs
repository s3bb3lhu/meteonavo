const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const catalogue=JSON.parse(fs.readFileSync('app/static/ui-translations.json','utf8'));
const ctx=vm.createContext({window:{StudioUI:{prefs:{language:'de'}}},fetch:async()=>({ok:true,json:async()=>catalogue}),document:{body:null,documentElement:{lang:'de'},dispatchEvent(){}},MutationObserver:class{observe(){}},CustomEvent:class{},setTimeout,clearTimeout,console});
vm.runInContext(fs.readFileSync('app/static/i18n.js','utf8'),ctx);
(async()=>{await ctx.window.I18N.ready;
for(const [index,lang] of ['en','fr','es'].entries()){
 ctx.window.I18N.setLanguage(lang);
 for(const [source,values] of Object.entries(catalogue))assert.equal(ctx.window.I18N.text(source),values[index],source+' / '+lang);
 assert.equal(ctx.window.I18N.text('METEONOVA'),'METEONOVA');assert.equal(ctx.window.I18N.text('Calp'),'Calp');
 assert.ok(!ctx.window.I18N.text('TomTom Traffic erreichbar (HTTP 200). 0 Ereignisse im Testumkreis. Auch null Ereignisse sind ein erfolgreicher API-Test. Der vollständige Umkreis wird in passende Teilflächen aufgeteilt.').includes('erreichbar'));
}
ctx.window.I18N.setLanguage('de');assert.equal(ctx.window.I18N.text('Benutzername'),'Benutzername');
console.log(Object.keys(catalogue).length+' Texte in EN/FR/ES, Rückwechsel, Nutzernamen und dynamischer TomTom-Test übersetzt');
})().catch(e=>{console.error(e);process.exitCode=1});
