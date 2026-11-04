let weatherArtCounter=0;
function illustratedWeatherArt(code,small=false,night=false){
 const kind=weatherKind(code),id=`wx-${++weatherArtCounter}`;
 const hasCloud=!['clear','unknown'].includes(kind);
 const celestial=['clear','fair','partly','showers','snow-showers'].includes(kind);
 const rainy=['drizzle','ice-drizzle','rain','ice-rain','showers','storm'].includes(kind);
 const snowy=['snow','snow-showers'].includes(kind);
 const frozen=['ice-drizzle','ice-rain'].includes(kind);
 const stormy=['storm','hail'].includes(kind);
 const cx=hasCloud?159:120,cy=hasCloud?61:87,r=hasCloud?32:43;
 const cloud='M56 137C31 137 24 111 38 95C45 87 55 84 65 87C69 59 101 47 124 64C134 71 140 82 141 94C165 85 188 100 187 118C186 132 175 141 157 141H56Z';
 const dark=stormy||['rain','ice-rain','overcast'].includes(kind);
 const defs=`<defs>
 <radialGradient id="${id}-volume" cx=".32" cy=".2" r=".85"><stop stop-color="${dark?'#e3e7ec':'#ffffff'}"/><stop offset=".48" stop-color="${dark?'#9caab9':'#eef2f6'}"/><stop offset=".78" stop-color="${dark?'#5e7085':'#bdcbd9'}"/><stop offset="1" stop-color="${dark?'#394b63':'#7d93ac'}"/></radialGradient>
 <radialGradient id="${id}-halo"><stop stop-color="#ffeeb2" stop-opacity=".6"/><stop offset=".5" stop-color="#ffc65a" stop-opacity=".18"/><stop offset="1" stop-color="#ffbe50" stop-opacity="0"/></radialGradient>
 <filter id="${id}-soft" x="-.5" y="-.5" width="2" height="2"><feGaussianBlur stdDeviation="2.5"/></filter>
 <clipPath id="${id}-cloudclip"><path d="${cloud}"/></clipPath>
 <linearGradient id="${id}-cloud" x1="0" y1="0" x2="0.8" y2="1"><stop stop-color="#ffffff"/><stop offset=".5" stop-color="#e9f3f9"/><stop offset="1" stop-color="#8eb2ce"/></linearGradient>
 <linearGradient id="${id}-back"><stop stop-color="#8faac8"/><stop offset="1" stop-color="#536d90"/></linearGradient>
 <radialGradient id="${id}-sun" cx=".35" cy=".25" r=".85"><stop stop-color="#fff8cd"/><stop offset=".45" stop-color="#ffce61"/><stop offset="1" stop-color="#f59b38"/></radialGradient>
 <linearGradient id="${id}-rain" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#bdefff"/><stop offset="1" stop-color="#479bd3"/></linearGradient>
 <radialGradient id="${id}-moon" cx=".3" cy=".2"><stop stop-color="#ffffff"/><stop offset="1" stop-color="#abc7ef"/></radialGradient>
 <linearGradient id="${id}-bolt"><stop stop-color="#fff8b3"/><stop offset="1" stop-color="#ffb23f"/></linearGradient>
 <mask id="${id}-crescent"><rect width="240" height="200" fill="white"/><circle cx="${cx+19}" cy="${cy-12}" r="${r}" fill="black"/></mask></defs>`;
 let art='';
 if(celestial){
  if(night){
   art+=`<g class="moon-icon"><circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#${id}-moon)" mask="url(#${id}-crescent)"/><circle cx="${cx-17}" cy="${cy+9}" r="4" fill="#809fca" opacity=".3"/><circle cx="${cx-7}" cy="${cy+23}" r="2.5" fill="#809fca" opacity=".25"/></g>`;
   if(!hasCloud)art+='<g class="wx-stars" fill="#dbeaff"><path d="m67 39 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z"/><path d="m177 66 2 5 5 2-5 2-2 5-2-5-5-2 5-2Z"/></g>';
  }else{
   art+=`<g class="wx-sun"><circle cx="${cx}" cy="${cy}" r="${r*1.8}" fill="url(#${id}-halo)"/><g class="sun-rays" style="transform-origin:${cx}px ${cy}px" stroke="#ffe4a0" stroke-width="2" opacity=".4" filter="url(#${id}-soft)">${Array.from({length:16},(_,i)=>`<path d="M${cx} ${cy-r+3}v-23" transform="rotate(${i*22.5} ${cx} ${cy})"/>`).join('')}</g><circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#${id}-sun)"/><ellipse cx="${cx-r*.2}" cy="${cy-r*.3}" rx="${r*.6}" ry="${r*.4}" fill="#fff9d8" opacity=".28" filter="url(#${id}-soft)"/></g>`;
  }
 }
 if(hasCloud){
  if(['overcast','fog','storm','hail'].includes(kind))art+=`<path d="${cloud}" transform="translate(21,-15) scale(.88)" fill="url(#${id}-back)" opacity=".85"/>`;
  const transform=kind==='fair'?'translate(28,24) scale(.76)':'';
  art+=`<g class="wx-cloud" transform="${transform}"><path d="${cloud}" fill="#142439" opacity=".22" transform="translate(0,5)" filter="url(#${id}-soft)"/><g clip-path="url(#${id}-cloudclip)"><path d="${cloud}" fill="url(#${id}-volume)"/>${[[60,111,28],[98,93,33],[129,112,29],[162,119,25]].map(([x,y,r])=>`<ellipse cx="${x}" cy="${y}" rx="${r}" ry="${r*.86}" fill="url(#${id}-volume)" filter="url(#${id}-soft)"/>`).join('')}<ellipse cx="113" cy="143" rx="82" ry="12" fill="${dark?'#32445c':'#8199ae'}" opacity=".3" filter="url(#${id}-soft)"/></g></g>`;
 }
 if(rainy){
  const count=['drizzle','ice-drizzle'].includes(kind)?3:([65,67,82].includes(Number(code))?5:4);
  const drizzle=kind.includes('drizzle');
  art+=`<g class="wx-precip ${drizzle?'wx-drizzle':'wx-rain'}" stroke="url(#${id}-rain)" stroke-width="${drizzle?3:5}" stroke-linecap="round">${Array.from({length:count},(_,i)=>`<path d="m${66+i*23} ${153+i%2*5}-${drizzle?3:7} ${drizzle?8:20}"/>`).join('')}</g>`;
 }
 if(snowy||frozen){
  art+='<g class="wx-flakes" stroke="#d5f2ff" stroke-width="2.2" stroke-linecap="round">';
  const count=frozen?1:3;
  for(let i=0;i<count;i++){
   const x=frozen?170:72+i*40,y=166+i%2*6;
   art+=`<path d="M${x-8} ${y}h16M${x-4} ${y-7}l8 14M${x-4} ${y+7}l8-14"/>`;
  }art+='</g>';
 }
 if(kind==='snow-grains'||kind==='hail')art+='<g class="wx-pellets" fill="#e9f7ff" stroke="#85b9df" stroke-width="1.5"><circle cx="66" cy="161" r="4"/><circle cx="91" cy="177" r="4"/><circle cx="149" cy="166" r="4"/><circle cx="173" cy="180" r="4"/></g>';
 if(stormy)art+=`<path class="wx-bolt" d="m117 127-18 30h16l-9 30 34-42h-19l12-18Z" fill="url(#${id}-bolt)" stroke="#fff3b0" stroke-width="1.3"/>`;
 if(kind==='fog')art+=`<g class="wx-fog" stroke="#dce3e9" opacity=".8" filter="url(#${id}-soft)" stroke-width="8" stroke-linecap="round"><path d="M47 151h128M65 164h128M42 177h117"/></g>`;
 if(kind==='unknown')art+='<g fill="none" stroke="#a9c1d8" stroke-width="4" stroke-linecap="round"><circle cx="120" cy="95" r="48" stroke-dasharray="6 8"/><path d="M108 80a13 13 0 1 1 18 12q-6 3-6 12M120 118v1"/></g>';
 return `<svg class="weather-art wx-icon ${small?'small':''}" data-weather-kind="${kind}" viewBox="0 0 240 200" role="img" aria-label="${weatherLabel(code,night)}"><title>${weatherLabel(code,night)}</title>${defs}${art}</svg>`;
}
