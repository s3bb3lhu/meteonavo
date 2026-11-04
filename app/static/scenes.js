// Atmospheric illustrations, never a webcam or a precipitation observation.
const sceneThemes = new Set(['sky','city','nature','cinematic','flow','cinema-glass','cinema-prime','cinema-panorama','metro-red','ocean-blue','forest-green','retro-terminal','retro-sunset','prism-gradient','city-photo']);
let sceneState = {period:'unknown',weather:'unknown',night:false};
let sceneBuilt=false,lastSceneKey='';
function localParts(now, timezone){
 const parts=new Intl.DateTimeFormat('en-GB',{timeZone:timezone||'UTC',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now);
 const values=Object.fromEntries(parts.map(p=>[p.type,p.value]));
 return {date:`${values.year}-${values.month}-${values.day}`,minutes:Number(values.hour)*60+Number(values.minute)};
}
function dayPeriod(data, now=new Date()){
 if(!data)return 'unknown';
 let local;
 try{local=localParts(now,data.timezone);}catch(_){return 'unknown';}
 const index=data.daily?.time?.indexOf(local.date)??-1;
 const minutes=value=>typeof value==='string'&&value.includes('T')?Number(value.slice(11,13))*60+Number(value.slice(14,16)):null;
 const sunrise=index>=0?minutes(data.daily?.sunrise?.[index]):null;
 const sunset=index>=0?minutes(data.daily?.sunset?.[index]):null;
 if(sunrise!==null&&sunset!==null&&Number.isFinite(sunrise)&&Number.isFinite(sunset)){
  if(Math.abs(local.minutes-sunrise)<=45)return 'dawn';
  if(Math.abs(local.minutes-sunset)<=45)return 'dusk';
  return local.minutes>sunrise&&local.minutes<sunset?'day':'night';
 }
 // Polar day/night and cached payloads without sunrise/sunset use the API flag.
 if(data.current?.is_day===1)return 'day';
 if(data.current?.is_day===0)return 'night';
 return 'unknown';
}
function weatherScene(code){
 if(code===null||code===undefined||!Number.isFinite(Number(code)))return 'unknown';
 code=Number(code);
 if(code===0)return 'clear';
 if(code>=1&&code<=3)return 'clouds';
 if(code===45||code===48)return 'fog';
 if(code>=51&&code<=67||code>=80&&code<=82)return 'rain';
 if(code>=71&&code<=77||code===85||code===86)return 'snow';
 if(code>=95&&code<=99)return 'storm';
 return 'unknown';
}
function sceneMarkup(){
 const stars=Array.from({length:46},(_,i)=>`<i style="left:${(i*137.5)%100}%;top:${(i*19.7)%58}%;--delay:${i%9}s"></i>`).join('');
 const drops=Array.from({length:48},(_,i)=>`<i style="left:${(i*37.7)%105}%;top:${(i*23.1)%110-15}%;--delay:-${i%13/3}s;--duration:${1.3+i%4/5}s"></i>`).join('');
 const flakes=Array.from({length:32},(_,i)=>`<i style="left:${(i*61.8)%105}%;top:${(i*31.7)%110-15}%;--delay:-${i%11}s;--duration:${8+i%7}s;--size:${3+i%4}px"></i>`).join('');
 let buildings='',windows='';
 for(let i=0;i<26;i++){
  const x=i*52-12,height=58+(i*37)%160,width=38+i%3*5;
  buildings+=`<rect x="${x}" y="${660-height}" width="${width}" height="${height+60}" rx="2"/>`;
  for(let row=0;row<Math.floor(height/19)-1;row++)for(let col=0;col<3;col++){
   if((i+row+col)%4!==0)windows+=`<rect x="${x+7+col*10}" y="${674-height+row*19}" width="4" height="7" opacity="${.3+((i+row)%6)/10}"/>`;
  }
 }
 const trees=Array.from({length:23},(_,i)=>{const x=i*65-40,y=540+(i*17)%80;return `<path d="M${x} ${y+140}v-100m-35 65 35-52 35 52m-62-27 27-44 27 44m-48-25 21-35 21 35"/>`;}).join('');
 return `<div class="scene-sky"></div><div class="scene-photo"></div><div class="scene-stars">${stars}</div><div class="scene-orb"></div><div class="scene-clouds">${Array.from({length:6},(_,i)=>`<div class="scene-cloud cloud-${i}" style="--i:${i}"></div>`).join('')}</div>
 <svg class="scene-nature" viewBox="0 0 1280 720" preserveAspectRatio="none"><path class="far-mountain" d="M0 520 160 365 275 440 470 300 670 475 870 340 1080 430 1280 325V720H0Z"/><path class="near-mountain" d="M0 600 185 445 370 550 580 420 795 560 1065 465 1280 550V720H0Z"/><path class="lake" d="M0 602Q350 560 630 610T1280 590V720H0Z"/><g class="lake-ripples" fill="none"><path d="M0 640h1280M60 660h1100M0 685h1280M220 620h580M360 707h800"/></g><g class="forest">${trees}</g></svg>
 <svg class="scene-city" viewBox="0 0 1280 720" preserveAspectRatio="none"><path class="city-haze" d="M0 600Q350 470 650 580T1280 560V720H0Z"/><g class="buildings">${buildings}</g><g class="windows">${windows}</g><path class="street" d="M0 687H1280"/></svg>
 <div class="flow-ribbon ribbon-one"></div><div class="flow-ribbon ribbon-two"></div><div class="flow-ribbon ribbon-three"></div>
 <div class="scene-rain">${drops}</div><div class="scene-snow">${flakes}</div><div class="scene-fog"></div><div class="scene-flash"></div><div class="scene-scrim"></div>`;
}
function syncScene(data, theme, motion, now=new Date()){
 const screen=document.querySelector('.tv');
 const hasScene=sceneThemes.has(theme);
 screen.classList.toggle('has-scene',hasScene);
 screen.dataset.scene=cinematicFamily.has(theme)?'cinematic':theme;
 screen.dataset.cloudCover=String(data?.current?.weather_code??'');
 let period=dayPeriod(data,now),kind=weatherScene(data?.current?.weather_code);
 const params=new URLSearchParams(location.search);
 const demo=hasScene&&params.get('demo')==='1';
 if(demo){
  if(['dawn','day','dusk','night'].includes(params.get('period')))period=params.get('period');
  if(['clear','clouds','rain','snow','fog','storm'].includes(params.get('weather')))kind=params.get('weather');
 }
 sceneState={period,weather:kind,night:period==='night'||(['dawn','dusk'].includes(period)&&data?.current?.is_day===0)};
 if(!hasScene){$('scene-note').textContent='';return;}
 if(!sceneBuilt){$('weather-scene').innerHTML=sceneMarkup();sceneBuilt=true;}
 const key=JSON.stringify([theme,period,kind,motion,demo]);
 if(key===lastSceneKey)return;
 lastSceneKey=key;
 screen.dataset.period=period;screen.dataset.weather=kind;
 const photo=period==='night'&&kind==='clear'?'night':kind==='clear'?'day':'lake';
 const file=photo==='lake'?'cinematic-lake.png':`cinematic-${photo}.png`;
 screen.dataset.photo=photo;
 screen.style.setProperty('--scene-photo',`url('/static/backgrounds/${file}')`);
 const periods={dawn:'Morgendämmerung',day:'Tag',dusk:'Abenddämmerung',night:'Nacht',unknown:'ohne Zeitdaten'};
 const weatherNames={clear:'klar',clouds:'bewölkt',rain:'Regen',snow:'Schnee',fog:'Nebel',storm:'Gewitter',unknown:'ohne Wetterdaten'};
 $('scene-note').textContent=demo?`HINTERGRUNDSIMULATION · ${periods[period]} · ${weatherNames[kind]}`:`${periods[period]} · ${weatherNames[kind]}`;
}
