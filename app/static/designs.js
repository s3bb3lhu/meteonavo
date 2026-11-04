// Local vector artwork only: no external fonts, images or fabricated radar.
const designPresets = {
 classic:{name:'Studio Classic',color:'#33c9f2',background:'#102338',description:'Die vertraute, klare Studioansicht.'},
 aurora:{name:'Aurora Glass',color:'#69edcf',background:'#10172c',description:'Polarlicht, sanfte Lichtflächen und transparente Karten.'},
 noir:{name:'Midnight Broadcast',color:'#ffad55',background:'#141619',description:'Graphit, warme Akzente und markante TV-Typografie.'},
 solar:{name:'Solar Horizon',color:'#db593c',background:'#f6e9da',description:'Warme Sandtöne, Abendlicht und großzügige Formen.'},
 arctic:{name:'Arctic Minimal',color:'#087fab',background:'#eaf4fa',description:'Helles Eisblau, feine Linien und ruhige Datenkarten.'},
 sky:{name:'Living Sky',color:'#b5e8ff',background:'#163d64',description:'Bewegter Himmel mit Sonne, Mond, Wolken und passenden Wettereffekten.'},
 city:{name:'City Weather',color:'#ffcfa0',background:'#172e49',description:'Illustrierte Stadtsilhouette mit Abendlicht und leuchtenden Fenstern.'},
 nature:{name:'Nature Window',color:'#a9e4c9',background:'#183e49',description:'Animierter See, Wald und Berge mit wechselnder Lichtstimmung.'},
 cinematic:{name:'Cinematic Weather',color:'#e9dbbe',background:'#142c3d',description:'Erzeugte Fotolandschaft mit sanfter Kamerafahrt, Licht- und Wettereffekten.'},
 flow:{name:'Atmosphere Flow',color:'#c9c7ff',background:'#252448',description:'Weiche Lichtströme und Partikel, passend zu Wetter und Tageszeit.'},
 'cinema-glass':{name:'Cinematic Glass',color:'#99e2da',background:'#142c3d',description:'Glasrahmen für Ort, Zeit und Datum; ruhiges Nachrichtenband in Petrol.'},
 'cinema-prime':{name:'Cinematic Prime',color:'#ffb25e',background:'#142c3d',description:'Markante Senderoptik mit klaren Rahmen und hellem Nachrichtenlaufband.'},
 'cinema-panorama':{name:'Cinematic Panorama',color:'#e9d2aa',background:'#142c3d',description:'Viel Landschaft, feine goldene Rahmen und ein elegantes dunkles Nachrichtenband.'},
 'metro-red':{name:'Metro Red',color:'#ff6a70',background:'#221324',description:'Ortsfotografie mit roten Glasrahmen, dunklem Bordeaux und präziser Studiografik.'},
 'ocean-blue':{name:'Ocean Blue',color:'#7acaff',background:'#071e3d',description:'Ortsfotos, blaue Lichtkanten und kühle moderne Datenflächen.'},
 'forest-green':{name:'Forest Green',color:'#7becbd',background:'#0a2925',description:'Ortsfotografie, smaragdgrüne Rahmen und ruhige Naturfarben.'},
 'retro-terminal':{name:'Retro Terminal',color:'#9bf26e',background:'#09170d',description:'Grüne Bildschirmoptik, Rastergrafik und Monospace-Typografie.'},
 'retro-sunset':{name:'Retro Sunset',color:'#ffd078',background:'#2d1843',description:'Violett, Koralle, grafische Streifensonne und kantige Retro-Rahmen.'},
 'prism-gradient':{name:'Prism Gradient',color:'#cbb8ff',background:'#202140',description:'Moderne Verläufe in Blau, Lila und Petrol mit feinen Leuchtrahmen.'},
 'city-photo':{name:'Local Panorama',color:'#f4d1a0',background:'#182838',description:'Freies Archivfoto aus der Ortsumgebung, Lichtstimmung und Wettereffekte passend zu den Daten.'}
};
const cinematicFamily=new Set(['cinematic','cinema-glass','cinema-prime','cinema-panorama','metro-red','ocean-blue','forest-green','retro-terminal','retro-sunset','prism-gradient','city-photo']);
function studioIcon(name){
 const shapes={
  pin:'<path d="M12 22s7-7 7-13a7 7 0 0 0-14 0c0 6 7 13 7 13Z"/><circle cx="12" cy="9" r="2.5"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 2v6M17 2v6M3 11h18M7 15h2M12 15h2M7 18h2"/>',
  thermometer:'<path d="M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0Z"/><path d="M12 8v10"/><circle cx="12" cy="18" r="1.5"/>',
  drop:'<path d="M12 2S5 10 5 15a7 7 0 0 0 14 0c0-5-7-13-7-13Z"/><path d="M8 15a4 4 0 0 0 4 4"/>',
  wind:'<path d="M2 8h13a3 3 0 1 0-3-3M2 12h17a3 3 0 1 1-3 3M2 16h6a3 3 0 1 1-3 3"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3M4 4l2 2M18 18l2 2M4 20l2-2M18 6l2-2"/>',
  compass:'<circle cx="12" cy="12" r="9"/><path d="m16 8-3 7-5 1 3-7Z"/>',
  globe:'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 9h18M3 15h18"/>'
 };
 return `<svg class="data-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${shapes[name]||shapes.clock}</svg>`;
}
