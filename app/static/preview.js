// Local preview navigation only. It never writes channel configuration.
const previewPageNames={current:'Tageswetter',daily:'7 Tage',hourly:'Stundenwetter',wind:'Wind',precipitation:'Regen / Schnee · Prognose',radar:'Radar · Messbilder',country:'Landeswetter',traffic:'Verkehr',webcams:'Wetterkameras'};
function syncPreviewControls(kind){
 if(broadcastRender)return;
 const controls=document.getElementById('preview-controls');
 if(!controls)return;
 for(const button of controls.querySelectorAll('[data-preview-page]'))button.setAttribute('aria-pressed',String(button.dataset.previewPage===kind));
 const automatic=selectedPreviewPage===null;
 document.getElementById('preview-auto').setAttribute('aria-pressed',String(automatic));
 document.getElementById('preview-state').textContent=`Vorschau · ${previewPageNames[kind]||kind} · ${automatic?'Automatik':'manuell angehalten'}`;
}
function selectPreviewPage(kind){
 if(broadcastRender||!Object.hasOwn(previewPageNames,kind))return;
 selectedPreviewPage=kind;lastSwitch=Date.now();lastRenderKey='';
 const url=new URL(location.href);url.searchParams.set('page',kind);history.replaceState(null,'',url);
 render();
}
function stepPreview(direction){
 const keys=Object.keys(previewPageNames),kind=selectedPreviewPage||document.getElementById('content').dataset.page||'current';
 selectPreviewPage(keys[(keys.indexOf(kind)+direction+keys.length)%keys.length]);
}
(() => {
 const controls=document.getElementById('preview-controls');
 if(broadcastRender){controls.hidden=true;return;}
 controls.hidden=false;document.body.classList.add('has-preview-controls');
 for(const button of controls.querySelectorAll('[data-preview-page]'))button.addEventListener('click',()=>selectPreviewPage(button.dataset.previewPage));
 document.getElementById('preview-previous').onclick=()=>stepPreview(-1);
 document.getElementById('preview-next').onclick=()=>stepPreview(1);
 document.getElementById('preview-auto').onclick=()=>{
  selectedPreviewPage=null;lastSwitch=Date.now();lastRenderKey='';
  const url=new URL(location.href);url.searchParams.delete('page');history.replaceState(null,'',url);render();
 };
 document.getElementById('preview-fullscreen').onclick=async()=>{
  try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(_){}
 };
 document.addEventListener('keydown',event=>{
  if(event.ctrlKey||event.metaKey||event.altKey||['INPUT','SELECT','TEXTAREA'].includes(event.target.tagName))return;
  if(event.key==='ArrowRight'){event.preventDefault();stepPreview(1);}
  if(event.key==='ArrowLeft'){event.preventDefault();stepPreview(-1);}
 });
 window.dispatchEvent(new Event('resize'));
 if(channel)render();
})();

// Translate only preview controls; weather programme content stays channel-owned.
if(!broadcastRender&&['en','fr','es'].includes(new URLSearchParams(location.search).get('ui_lang'))){window.PreviewOnlyI18N=true;const script=document.createElement('script');script.src='/static/i18n.js?v=youtube-1';document.body.append(script);}
