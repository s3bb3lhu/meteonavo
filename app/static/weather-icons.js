// A complete local WMO icon family with unique SVG gradients per instance.

function weatherKind(code){
 if(code===null||code===undefined||!Number.isFinite(Number(code)))return 'unknown';
 code=Number(code);
 if(code===0)return 'clear';if(code===1)return 'fair';if(code===2)return 'partly';if(code===3)return 'overcast';
 if(code===45||code===48)return 'fog';if([51,53,55].includes(code))return 'drizzle';
 if(code===56||code===57)return 'ice-drizzle';if([61,63,65].includes(code))return 'rain';
 if(code===66||code===67)return 'ice-rain';if([71,73,75].includes(code))return 'snow';
 if(code===77)return 'snow-grains';if([80,81,82].includes(code))return 'showers';
 if(code===85||code===86)return 'snow-showers';if(code===95)return 'storm';
 if(code===96||code===99)return 'hail';return 'unknown';
}
function weatherLabel(code,night=false){
 return ({clear:night?'Klar':'Sonnig',fair:night?'Meist klar':'Heiter',partly:'Wolkig',overcast:'Bedeckt',fog:'Nebel',drizzle:'Nieselregen','ice-drizzle':'Gefrierender Nieselregen',rain:'Regen','ice-rain':'Gefrierender Regen',snow:'Schneefall','snow-grains':'Schneegriesel',showers:'Regenschauer','snow-showers':'Schneeschauer',storm:'Gewitter',hail:'Gewitter mit Hagel',unknown:'Keine Wetterangabe'})[weatherKind(code)];
}
// One photographic atlas; each viewport isolates exactly one weather cutout.
function weatherPhotoCell(code,night=false){
 const kind=weatherKind(code);
 return ({clear:night?1:0,fair:night?3:2,partly:night?5:4,overcast:6,fog:7,drizzle:8,'ice-drizzle':10,rain:9,'ice-rain':10,snow:11,'snow-grains':11,showers:night?9:12,'snow-showers':night?11:13,storm:14,hail:15})[kind];
}
function weatherArt(code,small=false,night=false){
 const queryIcons=typeof location!=='undefined'?new URLSearchParams(location.search):null;
 const iconStyle=queryIcons?.get('render')!=='1'&&['photographic','illustrated'].includes(queryIcons?.get('icons'))?queryIcons.get('icons'):(typeof channel!=='undefined'?channel?.icon_set:'photographic');
 if(iconStyle==='illustrated'&&typeof illustratedWeatherArt==='function')return illustratedWeatherArt(code,small,night);
 const kind=weatherKind(code),label=weatherLabel(code,night),cell=weatherPhotoCell(code,night);
 if(cell===undefined)return `<svg class="weather-art wx-icon ${small?'small':''}" data-weather-kind="unknown" viewBox="0 0 240 200" role="img" aria-label="${label}"><title>${label}</title><text x="120" y="125" text-anchor="middle" fill="#bacada" font-size="80">?</text></svg>`;
 const x=(cell%4)*240,y=Math.floor(cell/4)*240;
 return `<svg class="weather-art wx-icon wx-photo ${night?'moon-icon':''} ${small?'small':''}" data-weather-kind="${kind}" data-photo-cell="${cell}" viewBox="${x+16} ${y+12} 208 216" role="img" aria-label="${label}"><title>${label}</title><image href="/static/weather/photographic-atlas-v1.webp" width="960" height="960"/></svg>`;
}
