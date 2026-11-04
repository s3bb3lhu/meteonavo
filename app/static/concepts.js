// Approved concepts implemented with real channel data and configurable colors.
const conceptPresets={
 'panorama-glass':{name:'B1 · Panorama Glass',color:'#edbd75',background:'#132b3d',description:'Viel Landschaft, feine Glasrahmen und kompakte Wetterkarten.'},
 'editorial-light':{name:'B2 · Editorial Light',color:'#2356bf',background:'#eef2f5',description:'Helle Flächen, klare Linien und eine großzügige Fotoansicht.'},
 'ruby-broadcast':{name:'B3 · Ruby Broadcast',color:'#c3324e',background:'#181e35',description:'Markante TV-Rahmen, schräge Kanten und kräftige Farbakzente.'},
 'forest-terrain':{name:'B4 · Forest Terrain',color:'#55b88c',background:'#102e29',description:'Ruhige Naturfarben, grafische Linien und große Landschaften.'},
 'retro-broadcast':{name:'C1 · Retro Broadcast',color:'#2455a8',background:'#eae7df',description:'Kantige TV-Optik, helle Flächen und kräftige Retro-Typografie.'},
 'retro-digital':{name:'C2 · Retro Digital',color:'#81ddc3',background:'#071713',description:'Digitale Temperaturanzeige, feines Raster und kontrastreiche Rahmen.'},
 'aurora-gradient':{name:'C3 · Aurora Gradient',color:'#c06ba9',background:'#243147',description:'Weiche Farbverläufe, gerundete Glasflächen und fließende Linien.'},
 'alpine-luxe':{name:'C4 · Alpine Luxe',color:'#d4bb83',background:'#233848',description:'Feine Schmucklinien, ruhige Typografie und viel Fotopanorama.'}
};
Object.assign(designPresets,conceptPresets);
for(const key of Object.keys(conceptPresets)){cinematicFamily.add(key);if(typeof sceneThemes!=='undefined')sceneThemes.add(key);}
const landscapeTiles={dawn:[1,113,576,332],day:[586,113,576,332],rain:[1175,113,575,332],dusk:[1,508,576,338],night:[586,508,576,338],snow:[1175,508,575,338]};
function landscapeChoice(choice,period,kind){
 if(choice!=='auto')return Object.hasOwn(landscapeTiles,choice)?choice:null;
 if(kind==='snow')return 'snow';if(period==='night')return 'night';
 if(['rain','storm','fog'].includes(kind))return 'rain';
 if(period==='dawn')return 'dawn';if(period==='dusk')return 'dusk';return 'day';
}
let landscapeKey='';
function syncLandscape(){
 const params=new URLSearchParams(location.search),requested=params.get('landscape');
 const choice=!broadcastRender&&['off','auto',...Object.keys(landscapeTiles)].includes(requested)?requested:(channel.landscape_mood||'off');
 const screen=document.querySelector('.tv'),mood=landscapeChoice(choice,sceneState.period,sceneState.weather);
 screen.classList.toggle('has-landscape',!!mood);screen.dataset.landscape=mood||'';screen.dataset.landscapeAuto=String(choice==='auto');
 if(!mood){if(landscapeKey){const photo=document.querySelector('.scene-photo');if(photo){photo.replaceChildren();photo.style.removeProperty('background-image');}landscapeKey='';}return false;}
 if(!sceneBuilt){$('weather-scene').innerHTML=sceneMarkup();sceneBuilt=true;}
 screen.classList.add('has-scene');screen.classList.remove('place-photo-active');screen.dataset.period=sceneState.period;screen.dataset.weather=sceneState.weather;
 const [x,y,w,h]=landscapeTiles[mood];
 if(landscapeKey!==mood){const photo=document.querySelector('.scene-photo');photo.style.backgroundImage='none';photo.innerHTML=`<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><image href="/static/backgrounds/landscape-moods-v1.webp" x="${-x}" y="${-y}" width="1752" height="897"/></svg>`;landscapeKey=mood;}
 $('source').textContent='';return true;
}
function digitalTemperature(value){
 if(value==null||!Number.isFinite(Number(value)))return '—';
 const chars=Number(value).toFixed(1),map={'0':'abcdef','1':'bc','2':'abged','3':'abgcd','4':'fgbc','5':'afgcd','6':'afgecd','7':'abc','8':'abcdefg','9':'abfgcd','-':'g'},segments={a:[6,0,24,5],b:[30,5,5,25],c:[30,35,5,25],d:[6,60,24,5],e:[1,35,5,25],f:[1,5,5,25],g:[6,30,24,5]};
 let x=0,paths='';for(const char of chars){if(char==='.'){paths+=`<circle cx="${x+3}" cy="62" r="3"/>`;x+=12;continue;}paths+=`<g transform="translate(${x})">${[...(map[char]||'')].map(s=>{const [a,b,w,h]=segments[s];return `<rect x="${a}" y="${b}" width="${w}" height="${h}" rx="1"/>`;}).join('')}</g>`;x+=43;}
 return `<svg class="digital-temperature" viewBox="0 0 ${x+58} 70" role="img" aria-label="${escapeText(num(value,' Grad Celsius'))}"><g fill="currentColor">${paths}</g><text x="${x}" y="28" fill="currentColor" font-size="24">°C</text></svg>`;
}
function decorateConcept(){if(activeTheme()==='retro-digital'&&$('content').dataset.page==='current'){const hero=document.querySelector('.hero');if(hero)hero.innerHTML=digitalTemperature(weather?.data?.current?.temperature_2m);}}
