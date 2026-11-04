const $=id=>document.getElementById(id);let channels=[],results=[];
const fields=['name','location','latitude','longitude','color','background','seconds','rss_url','theme'];
const tokenKey='weather-studio-admin-token';
try{$('token').value=sessionStorage.getItem(tokenKey)||'';}catch(_){}
function rememberToken(){try{if($('remember-token').checked&&$('token').value.trim())sessionStorage.setItem(tokenKey,$('token').value.trim());else sessionStorage.removeItem(tokenKey);}catch(_){}}
$('token').addEventListener('input',rememberToken);
$('remember-token').addEventListener('change',rememberToken);
function message(text,success=false){for(const id of ['message','save-message']){$(id).textContent=text;$(id).style.color=success?'#8ce6b0':'#ffdb8a';}}
async function request(url,options={}){const r=await fetch(url,{...options,headers:{'Content-Type':'application/json',Authorization:`Bearer ${$('token').value.trim()}`,...options.headers}});if(!r.ok){if(r.status===401)throw Error('Admin-Token fehlt oder ist ungültig. Bitte oben das Token aus deiner .env eingeben und erneut speichern.');throw Error(`${r.status}: ${await r.text()}`);}return r.json();}
function edit(id){const c=channels.find(x=>x.id===id);$('cid').value=id;for(const f of fields)$(f).value=c[f]??'';$('enabled').checked=c.enabled;$('motion').checked=c.motion!==false;paintDesignChoices();$('pages').value=c.pages.join(',');$('preview-tab').href=`/view/${id}`;$('preview-channel').textContent=`Kanal ${id} · ${c.name}`;}
async function load(){channels=await request('/api/channels');const streams=await request('/api/streams');$('channels').replaceChildren();for(const c of channels){const a=document.createElement('article');const title=document.createElement('h2');title.textContent=`${c.id} · ${c.name}`;const p=document.createElement('p');p.textContent=`${c.location||'Noch kein Ort'} · ${c.enabled?(streams.find(s=>s.id===c.id).ready?'Stream bereit':'Stream startet / offline'):'Deaktiviert'}`;const b=document.createElement('button');b.textContent='Bearbeiten';b.onclick=()=>edit(c.id);const preview=document.createElement('a');preview.href=`/view/${c.id}`;preview.target='_blank';preview.rel='noopener';preview.textContent='Live-Vorschau ↗';const link=document.createElement('a');link.href=`/live/${c.id}/index.m3u8`;link.textContent=' HLS öffnen';a.append(title,p,b,preview,link);$('channels').append(a);}}
$('preview-popup').onclick=()=>{window.open(`/view/${Number($('cid').value)||1}`,'_blank','popup=yes,width=1280,height=720,resizable=yes,scrollbars=no,noopener');};
$('lookup').onclick=async()=>{try{results=await request(`/api/locations?q=${encodeURIComponent($('search').value)}`);$('results').replaceChildren(new Option('Ort auswählen …',''));results.forEach((r,i)=>$('results').add(new Option([r.name,r.admin1,r.country].filter(Boolean).join(', '),String(i))));message(results.length?'Treffer auswählen.':'Keine Treffer. Koordinaten können manuell eingegeben werden.');}catch(e){message(e.message);}};
$('results').onchange=()=>{if($('results').value==='')return;const r=results[Number($('results').value)];$('location').value=r.name;$('latitude').value=r.latitude;$('longitude').value=r.longitude;};
$('form').addEventListener('invalid',e=>message(`Bitte „${e.target.closest('label')?.textContent.trim()||'Eingabe'}“ prüfen: ${e.target.validationMessage}`),true);
$('form').onsubmit=async e=>{
 e.preventDefault();
 if(!$('token').value.trim()){message('Zum Speichern bitte oben dein Admin-Token eingeben.');$('token').focus();return;}
 rememberToken();const button=$('save');button.disabled=true;button.textContent='Wird gespeichert …';
 try{
  const c={};for(const f of fields)c[f]=['latitude','longitude','seconds'].includes(f)?Number($(f).value):$(f).value;
  c.enabled=$('enabled').checked;c.motion=$('motion').checked;c.pages=$('pages').value.split(',').map(x=>x.trim());
  await request(`/api/channels/${$('cid').value}`,{method:'PUT',body:JSON.stringify(c)});
  message('Gespeichert. Vorschau und Stream übernehmen die Änderungen innerhalb von etwa 15 Sekunden.',true);
  try{await load();}catch(_){message('Gespeichert. Die Kanalliste konnte noch nicht aktualisiert werden.',true);}
 }catch(error){message(error.message);}
 finally{button.disabled=false;button.textContent='Speichern und übernehmen';}
};
load().then(()=>edit(1)).catch(e=>message(e.message));setInterval(()=>load().catch(()=>{}),15000);

function paintDesignChoices(){
 $('design-picker').replaceChildren();
 for(const [key,preset] of Object.entries(designPresets)){
  if(key==='classic')continue;
  const card=document.createElement('div');card.className='design-choice';card.dataset.theme=key;card.classList.toggle('active',$('theme').value===key);
  const title=document.createElement('strong');title.textContent=preset.name;
  const description=document.createElement('small');description.textContent=preset.description;
  const actions=document.createElement('div');actions.className='design-actions';
  const choose=document.createElement('button');choose.type='button';choose.textContent='Auswählen';choose.onclick=()=>chooseDesign(key);
  const preview=document.createElement('a');preview.href=`/view/${Number($('cid').value)||1}?theme=${key}`;preview.target='_blank';preview.rel='noopener';preview.textContent='Animierte Vorschau ↗';
  actions.append(choose,preview);
  if(['sky','city','nature','cinematic','flow','cinema-glass','cinema-prime','cinema-panorama'].includes(key))for(const [period,label] of [['day','Tag testen'],['night','Nacht testen']]){
   const demo=document.createElement('a');demo.href=`/view/${Number($('cid').value)||1}?theme=${key}&demo=1&period=${period}&weather=clear`;demo.target='_blank';demo.rel='noopener';demo.textContent=label;actions.append(demo);
  }
  card.append(title,description,actions);$('design-picker').append(card);
 }
}
function chooseDesign(key){const preset=designPresets[key];$('theme').value=key;$('color').value=preset.color;$('background').value=preset.background;paintDesignChoices();message(`${preset.name} ausgewählt. Zum Übernehmen bitte speichern.`);}
$('theme').onchange=()=>chooseDesign($('theme').value);
