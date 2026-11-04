// Forecast charts use only supplied model values. Missing values remain gaps.
function forecastGraphic(h,start,kind){
 const indices=Array.from({length:Math.max(0,Math.min(6,h.time.length-start))},(_,i)=>start+i);
 const valid=v=>typeof v==='number'&&Number.isFinite(v);
 const values=indices.map(i=>kind==='hourly'?h.temperature_2m[i]:h.rain[i]);
 const known=values.filter(valid),lo=Math.min(...known,0),hi=Math.max(...known,1),spread=Math.max(hi-lo,1);
 const x=i=>70+i*188,y=v=>133-(v-lo)/spread*90;
 let chart='<path class="chart-grid" d="M35 43H1060M35 88H1060M35 133H1060"/>';
 if(kind==='hourly'){
  for(let i=1;i<values.length;i++)if(valid(values[i-1])&&valid(values[i]))chart+=`<path d="M${x(i-1)} ${y(values[i-1])}L${x(i)} ${y(values[i])}" fill="none" stroke="var(--accent)" stroke-width="3" stroke-linecap="round"/>`;
 }
 values.forEach((v,i)=>{
  if(valid(v))chart+=kind==='hourly'?`<circle cx="${x(i)}" cy="${y(v)}" r="5" fill="var(--accent)" stroke="#12293c" stroke-width="3"/>`:`<rect x="${x(i)-28}" y="${y(v)}" width="56" height="${Math.max(2,133-y(v))}" rx="5" fill="var(--accent)" opacity=".7"/>`;
  chart+=`<text class="chart-value" x="${x(i)}" y="${valid(v)?y(v)-15:95}" text-anchor="middle">${num(v,kind==='hourly'?'°':' mm')}</text><text x="${x(i)}" y="164" text-anchor="middle">${escapeText(h.time[indices[i]].slice(11))}</text>`;
 });
 const tiles=indices.map(i=>`<div class="forecast-tile"><b>${escapeText(h.time[i].slice(11))}</b><strong>${num(h.precipitation_probability[i],' %')}</strong><small>${kind==='hourly'?'Wind '+num(h.wind_speed_10m[i],' km/h'):'Schnee '+num(h.snowfall[i],' cm')}</small></div>`).join('');
 const text=kind==='hourly'?'Temperaturverlauf':'Regenmenge';
 return `<div class="forecast-graphic"><div class="forecast-caption"><strong>${text}</strong><span>Prognose · ${indices.length} Stunden · Ortszeit</span></div><svg class="forecast-svg" viewBox="0 0 1080 180" role="img" aria-label="${text} für die nächsten Stunden">${chart}</svg><div class="forecast-grid">${tiles}</div><div class="forecast-key">${kind==='hourly'?'Linie: Temperatur':'Balken: Regenmenge'} · Karten: Niederschlagswahrscheinlichkeit je Stunde</div></div>`;
}
function dayRange(d,i){
 const values=[...d.temperature_2m_min,...d.temperature_2m_max].filter(v=>typeof v==='number'&&Number.isFinite(v));
 const min=d.temperature_2m_min[i],max=d.temperature_2m_max[i];
 if(!values.length||typeof min!=='number'||typeof max!=='number')return '';
 const lo=Math.min(...values),range=Math.max(1,Math.max(...values)-lo),left=Math.max(0,(min-lo)/range*100),width=Math.max(2,(max-min)/range*100);
 return `<div class="day-range" aria-hidden="true"><i style="margin-left:${left}%;width:${Math.min(width,100-left)}%"></i></div>`;
}
