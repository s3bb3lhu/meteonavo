function gpsNumber(value,label,min,max){
 const text=String(value).trim();if(!text)return null;
 if(!/^[+-]?\d+(?:[.,]\d+)?$/.test(text))throw Error(label+': Bitte eine Dezimalzahl eingeben.');
 const number=Number(text.replace(',','.'));
 if(!Number.isFinite(number)||number<min||number>max)throw Error(`${label}: gültiger Bereich ${min} bis ${max}.`);
 return number;
}
function gpsPair(value){
 const text=String(value).trim();let parts;
 if(text.includes(';'))parts=text.split(';');
 else if(text.includes(',')&&text.split(',').length===2)parts=text.split(',');
 else parts=text.split(/\s+/);
 if(parts.length!==2)throw Error('Zwei Koordinaten eingeben: Breitengrad, Längengrad. Bei Dezimalkomma mit Semikolon trennen.');
 const latitude=gpsNumber(parts[0],'Breitengrad',-90,90),longitude=gpsNumber(parts[1],'Längengrad',-180,180);
 if(latitude===null||longitude===null)throw Error('Beide Koordinaten eingeben.');
 return {latitude,longitude};
}
