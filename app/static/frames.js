// Frame systems are independent of the weather layout and its data.
const framePresets={design:'Rahmen der Designvorlage','fine-line':'D1 · Fine Line','broadcast-edge':'D2 · Broadcast Edge',contour:'D3 · Contour Frame','retro-chrome':'D4 · Retro Chrome','soft-ribbon':'D5 · Soft Ribbon','corner-brackets':'D6 · Corner Brackets'};
function selectedFrame(channel){const requested=new URLSearchParams(location.search).get('frame');return !broadcastRender&&Object.hasOwn(framePresets,requested)?requested:(channel.frame_style||'design');}

function applyFrameOptions(screen,channel){
 const q=new URLSearchParams(location.search),preview=!broadcastRender;
 const custom=preview&&q.has('frame_custom')?q.get('frame_custom')==='1':channel.frame_custom===true;
 for(const part of ['top','middle']){const key='frame_'+part+'_opacity',raw=preview&&q.has(key)?q.get(key):channel[key];const value=raw===null||raw===undefined||raw===''?null:Number(raw);screen.classList.toggle('frame-'+part+'-custom',value!==null&&Number.isFinite(value));screen.style.setProperty('--frame-'+part+'-opacity',Math.max(0,Math.min(100,value??85))+'%');}
 screen.classList.toggle('custom-frame',custom&&screen.dataset.frame!=='design');
 const color=preview&&q.has('frame_color')?q.get('frame_color'):channel.frame_color;
 screen.style.setProperty('--frame-accent',custom&&/^#[0-9a-fA-F]{6}$/.test(color)?color:'var(--accent)');
 for(const [key,min,max,fallback,unit] of [['width',1,8,2,'px'],['radius',0,48,16,'px'],['opacity',20,100,85,'%']]){
  const field='frame_'+key,value=Number(preview&&q.has(field)?q.get(field):(channel[field]??fallback));
  screen.style.setProperty('--frame-'+key,Math.min(max,Math.max(min,Number.isFinite(value)?value:fallback))+unit);
 }
}

function applyTvLogo(screen,channel){
 const q=new URLSearchParams(location.search),preview=!broadcastRender;
 const pick=key=>preview&&q.has(key)?q.get(key):channel[key];let mode=pick('logo_mode');
 if(!['off','location','free'].includes(mode))mode='off';
 let logo=document.getElementById('tv-logo');
 if(!logo){logo=document.createElement('div');logo.id='tv-logo';logo.innerHTML='<img alt="TV-Logo">';screen.append(logo);}
 const visible=mode!=='off'&&/^[a-f0-9]{16}$/.test(channel.logo_version||'');logo.hidden=!visible;
 screen.classList.toggle('has-location-logo',visible&&mode==='location');
 if(!visible)return;
 const number=(key,min,max,fallback)=>{const value=Number(pick(key)??fallback);return Math.max(min,Math.min(max,Number.isFinite(value)?value:fallback));};
 const width=number('logo_width',30,250,90),height=Math.min(100,width*.65),opacity=number('logo_opacity',0,100,100);
 screen.style.setProperty('--tv-logo-width',width+'px');logo.style.width=width+'px';logo.style.height=height+'px';logo.style.opacity=opacity/100;
 const image=logo.querySelector('img'),src='/api/logo/'+id+'/image?v='+channel.logo_version;if(image.getAttribute('src')!==src)image.src=src;
 logo.className=mode==='location'?'logo-location':'logo-free';
 if(mode==='location'){const locationFrame=screen.querySelector('.location-frame');if(logo.parentElement!==locationFrame)locationFrame.append(logo);logo.style.left='12px';logo.style.top='50%';}
 else{if(logo.parentElement!==screen)screen.append(logo);logo.style.left=(1280-width)*number('logo_x',0,100,90)/100+'px';logo.style.top=(632-height)*number('logo_y',0,100,5)/100+'px';}
}
