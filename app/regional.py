"""Country model weather, regional traffic and daily webcam link discovery."""
import asyncio
import gzip
import json
import math
import re
import hashlib
import os
import time
from urllib.parse import urlsplit
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
import httpx
from .radio_proxy import open_public

SEEDS=[
 dict(name='Frankfurt · Goetheturm',latitude=50.0838,longitude=8.7285,url='https://goetheturm.panocloud.webcam/',source='Stadt Frankfurt',reference='https://frankfurt.de/aktuelle-meldung/meldungen/goetheturm-mit-webcam/'),
 dict(name='Calp · Arenal-Bol und Hafen',latitude=38.642,longitude=.049,url='https://calp.es/en/webcams',source='Ayuntamiento de Calp',reference='https://calp.es/en/webcams'),
 dict(name='Calp · Arenal-Bol',latitude=38.641,longitude=.049,url='https://ibericam.com/alicante/webcam-calpe-playa-del-arenal-bol/',source='Ibericam / Ayuntamiento de Calp',reference='https://calp.es/en/webcams'),
 dict(name='Valencia · Kameranetz',latitude=39.455,longitude=-.35,url='https://www.comunitatvalenciana.com/es/webcams',source='Turisme Comunitat Valenciana',reference='https://www.comunitatvalenciana.com/es/webcams')]


def km(a,b,c,d):
    x=math.sin(math.radians(c-a)/2)**2+math.cos(math.radians(a))*math.cos(math.radians(c))*math.sin(math.radians(d-b)/2)**2
    return 6371*2*math.asin(min(1,math.sqrt(x)))


def in_ring(lon,lat,ring):
    inside=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if (a[1]>lat)!=(b[1]>lat) and lon<(b[0]-a[0])*(lat-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside


def country_for(data,lon,lat):
    for country in data['countries']:
        g=country['geometry'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
        for rings in polys:
            if in_ring(lon,lat,rings[0]) and not any(in_ring(lon,lat,r) for r in rings[1:]):
                return dict(name=country['name'],geometry=dict(type='Polygon',coordinates=rings))
    return None


class TrafficKey(BaseModel):
    key:str=Field(default='',max_length=128,pattern=r'^[A-Za-z0-9_-]*$')


class TrafficTest(TrafficKey):
    channel_id:int=Field(default=1,ge=1,le=5)


def tomtom_boxes(lat,lon,radius):
    # Keep each request safely below TomTom's 10,000 km² limit.
    dy=radius/111.32;dx=min(180,dy/max(.01,math.cos(math.radians(lat))))
    west,east=max(-180,lon-dx),min(180,lon+dx);south,north=max(-85,lat-dy),min(85,lat+dy)
    count=max(1,math.ceil(2*radius/80))
    return [(west+(east-west)*x/count,south+(north-south)*y/count,west+(east-west)*(x+1)/count,south+(north-south)*(y+1)/count) for y in range(count) for x in range(count)]


def traffic_error(status):
    if status in (401,403):return 'TomTom lehnt den Schlüssel ab oder Traffic Incident Details ist für diesen Schlüssel nicht freigeschaltet.'
    if status==429:return 'TomTom-Kontingent oder Anfragelimit erreicht. Später erneut testen.'
    if status==400:return 'TomTom hat die Verkehrsabfrage abgelehnt (HTTP 400). API-Berechtigung und Anfrageparameter prüfen.'
    return 'TomTom ist derzeit nicht erreichbar. Netzwerkverbindung oder Anbieterstatus prüfen.'


def road_priority(roads):
    return 0 if any(re.fullmatch(r'(?:A|AP|B|E|M|N|S|SS)[ -]?\d+[A-Z]?',road.strip(),re.I) for road in roads) else 1


async def tomtom_fetch(key,lat,lon,radius):
    boxes=tomtom_boxes(lat,lon,radius);semaphore=asyncio.Semaphore(3)
    async with httpx.AsyncClient(timeout=20) as client:
        async def fetch(box):
            async with semaphore:
                try:
                    r=await client.get('https://api.tomtom.com/traffic/services/5/incidentDetails',params=dict(key=key,bbox=','.join(str(v) for v in box),language='de-DE',timeValidityFilter='present',fields='{incidents{type,geometry{type,coordinates},properties{id,iconCategory,events{description},from,to,roadNumbers}}}'))
                    if r.status_code!=200:return [],r.status_code
                    payload=r.json()
                    if not isinstance(payload.get('incidents'),list):return [],502
                    return payload['incidents'],200
                except (httpx.HTTPError,ValueError,TypeError):return [],503
        results=await asyncio.gather(*(fetch(box) for box in boxes))
    failures=[status for _,status in results if status!=200]
    if len(failures)==len(results):raise HTTPException(failures[0],traffic_error(failures[0]))
    items={}
    for incidents,status in results:
        for incident in incidents:
            try:
                geometry=incident['geometry'];points=geometry['coordinates'];points=[points] if geometry['type']=='Point' else points
                near=min(points,key=lambda point:km(lat,lon,point[1],point[0]));distance=km(lat,lon,near[1],near[0])
                if distance>radius:continue
                props=incident['properties'];identity=props.get('id') or hashlib.sha256(json.dumps(incident,sort_keys=True).encode()).hexdigest()
                roads=[re.sub(r'\s+','',str(road)).upper() for road in (props.get('roadNumbers') or []) if str(road).strip()]
                items[identity]=dict(id=identity,title=(f'{props.get("from","")} → {props.get("to","")}' if props.get('from') or props.get('to') else 'Verkehrsmeldung'),description=' · '.join(e.get('description','') for e in props.get('events',[])),latitude=near[1],longitude=near[0],distance_km=round(distance,1),road=' / '.join(roads[:2]),road_numbers=roads,priority=road_priority(roads))
            except (KeyError,TypeError,ValueError,IndexError):continue
    return dict(items=sorted(items.values(),key=lambda x:(x['priority'],x['distance_km'])),status='partial' if failures else 'ok',requests=len(boxes),failed_requests=len(failures),message=(traffic_error(failures[0])+' Ein Teil der Daten konnte geladen werden.' if failures else 'Gemeldete Ereignisse im Luftlinienradius. Keine Meldungen bedeuten nicht automatisch freie Straßen.'))


def install(m):
    tasks={};traffic_locks={};geography=None
    def init():
        with m.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS regional_cache (key TEXT PRIMARY KEY,stamp REAL,payload TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS regional_settings (key TEXT PRIMARY KEY,value TEXT)')
    def cached(key):
        init()
        with m.db() as c:row=c.execute('SELECT stamp,payload FROM regional_cache WHERE key=?',(key,)).fetchone()
        return (row[0],json.loads(row[1])) if row else (0,None)
    def store(key,data):
        with m.db() as c:c.execute('INSERT OR REPLACE INTO regional_cache VALUES (?,?,?)',(key,time.time(),json.dumps(data)))
    def launch(key,fn):
        if key not in tasks or tasks[key].done():tasks[key]=asyncio.create_task(fn())
    def mapdata():
        nonlocal geography
        if geography is None:geography=json.loads(gzip.decompress((m.STATIC/'maps/radar-geography.json.gz').read_bytes()))
        return geography
    def coords(i):
        ch=m.get_channel(i)
        if ch['latitude'] is None:raise HTTPException(409,'Bitte einen Standort konfigurieren')
        return ch

    @m.app.get('/api/country/{i}')
    async def country(i:int):
        ch=coords(i);shape=country_for(mapdata(),ch['longitude'],ch['latitude'])
        selected=ch['overview_places']
        if not selected:
            selected=[dict(name=ch['location'] or ch['name'],latitude=ch['latitude'],longitude=ch['longitude'],country_code=ch['country_code'])]
            if shape:
                ring=shape['geometry']['coordinates'][0]
                for city in sorted(mapdata()['cities'],key=lambda x:x['rank']):
                    lon,lat=city['coordinates']
                    if in_ring(lon,lat,ring) and km(lat,lon,ch['latitude'],ch['longitude'])>30:
                        selected.append(dict(name=({'Munich':'München','Cologne':'Köln','Nuremberg':'Nürnberg','Dusseldorf':'Düsseldorf','Hanover':'Hannover'}.get(city['name'],city['name']) if ch['country_code']=='DE' else city['name']),latitude=lat,longitude=lon,country_code=ch['country_code']))
                    if len(selected)>=6:break
        key='country:'+json.dumps(selected,sort_keys=True);stamp,data=cached(key)
        if not data or time.time()-stamp>600:
            try:
                async with httpx.AsyncClient(timeout=25) as client:
                    r=await client.get('https://api.open-meteo.com/v1/forecast',params=dict(latitude=','.join(str(x['latitude']) for x in selected),longitude=','.join(str(x['longitude']) for x in selected),current='temperature_2m,weather_code,is_day',timezone='auto',forecast_days=1))
                    r.raise_for_status();items=r.json();items=items if isinstance(items,list) else [items]
                    if len(items)!=len(selected):raise ValueError('Incomplete forecast')
                    data=[dict(**place,current=item['current'],timezone=item.get('timezone','UTC')) for place,item in zip(selected,items)]
                    store(key,data);stamp=time.time()
            except (httpx.HTTPError,ValueError,KeyError):
                if not data:raise HTTPException(503,'Länderwetter derzeit nicht verfügbar')
        return dict(country=ch['country_code'],map=shape,places=data,stale=time.time()-stamp>900,source='Open-Meteo · Modellwetter',fetched_at=stamp)

    async def webcams_refresh(ch,key):
        old_stamp,old=cached(key)
        try:
            query='''SELECT ?item ?itemLabel ?webcam ?location WHERE {
              SERVICE wikibase:around { ?item wdt:P625 ?location . bd:serviceParam wikibase:center "Point(%s %s)"^^geo:wktLiteral; wikibase:radius "100". }
              ?item wdt:P4238 ?webcam . SERVICE wikibase:label {bd:serviceParam wikibase:language "de,en".}
            } LIMIT 40'''%(ch['longitude'],ch['latitude'])
            query='PREFIX wikibase: <http://wikiba.se/ontology#> PREFIX wdt: <http://www.wikidata.org/prop/direct/> PREFIX bd: <http://www.bigdata.com/rdf#> PREFIX geo: <http://www.opengis.net/ont/geosparql#> '+query
            async with httpx.AsyncClient(timeout=40,headers={'User-Agent':'WeatherChannelStudio/0.3 (regional webcam link directory)'}) as client:
                r=await client.get('https://query.wikidata.org/sparql',params={'query':query,'format':'json'});r.raise_for_status();bindings=r.json()['results']['bindings']
            items=[]
            for b in bindings:
                try:
                    lon,lat=map(float,b['location']['value'].removeprefix('Point(').removesuffix(')').split())
                    url=b['webcam']['value'];p=urlsplit(url)
                    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:continue
                    items.append(dict(name=b['itemLabel']['value'],latitude=lat,longitude=lon,url=url,source='Wikidata · Anbieterlink',reference=b['item']['value']))
                except (KeyError,ValueError):continue
            status='ok'
        except (httpx.HTTPError,ValueError,KeyError):
            items=(old or {}).get('items',[]);status='partial' if not old else 'stale'
        items=items+SEEDS
        unique={x['url']:x for x in items if km(ch['latitude'],ch['longitude'],x['latitude'],x['longitude'])<=100}
        result=[]
        for item in unique.values():
            item={**item,'distance_km':round(km(ch['latitude'],ch['longitude'],item['latitude'],item['longitude']),1)}
            # A successful page fetch is not proof that the camera itself is live.
            def probe():
                conn=None
                try:
                    conn,response,url=open_public(item['url']);response.read(512);return True
                except Exception:return False
                finally:
                    if conn:conn.close()
            item['page_reachable']=await asyncio.to_thread(probe);item['checked_at']=time.time()
            result.append(item)
        result.sort(key=lambda x:x['distance_km'])
        store(key,dict(items=result[:30],status=status,discovery_at=time.time() if status=='ok' else old_stamp or None))

    @m.app.get('/api/webcams/{i}')
    async def webcams(i:int):
        ch=coords(i);key=f'webcams:{ch["latitude"]:.5f}:{ch["longitude"]:.5f}';stamp,data=cached(key)
        if time.time()-stamp>86400:launch(key,lambda:webcams_refresh(ch,key))
        data=data or dict(items=[dict(**x,distance_km=round(km(ch['latitude'],ch['longitude'],x['latitude'],x['longitude']),1),page_reachable=None,checked_at=None) for x in SEEDS if km(ch['latitude'],ch['longitude'],x['latitude'],x['longitude'])<=100],status='loading')
        return dict(**data,checked_at=stamp or None,stale=bool(stamp and time.time()-stamp>90000),radius_km=100,message='Kameraseiten beim Anbieter öffnen. Erreichbare Seite bedeutet nicht, dass die Kamera aktuell sendet. Quellenprüfung täglich; keine Videoübernahme in den Sendestream.')

    async def autobahn_refresh():
        old_stamp,old=cached('traffic:DE')
        items=[];failed=0
        async with httpx.AsyncClient(timeout=15,headers={'User-Agent':'WeatherChannelStudio/0.3'}) as client:
            try:
                r=await client.get('https://verkehr.autobahn.de/o/autobahn/');r.raise_for_status();roads=r.json()['roads']
            except (httpx.HTTPError,ValueError,KeyError):
                store('traffic:DE',dict(items=(old or {}).get('items',[]),status='stale',observed_at=(old or {}).get('observed_at')));return
            semaphore=asyncio.Semaphore(4)
            async def road(name,kind):
                nonlocal failed
                async with semaphore:
                    try:
                        await asyncio.sleep(.2)
                        r=await client.get(f'https://verkehr.autobahn.de/o/autobahn/{name}/services/{kind}');r.raise_for_status()
                        for x in r.json().get(kind,[]):
                            try:
                                coord=x.get('coordinate') or {};lat=float(coord['lat']);lon=float(coord['long'])
                            except (KeyError,ValueError,TypeError):continue
                            desc=x.get('description') or [];desc=[desc] if isinstance(desc,str) else desc
                            title=str(x.get('title') or x.get('subtitle') or 'Verkehrsmeldung')[:300]
                            if x.get('future'):title='Geplant · '+title
                            items.append(dict(id=x.get('identifier',''),road=name,title=title,description=' · '.join(str(v) for v in desc if v)[:700],latitude=lat,longitude=lon,kind=kind))
                    except (httpx.HTTPError,ValueError,KeyError,TypeError):failed+=1
            await asyncio.gather(*(road(name,kind) for name in roads for kind in ('warning','roadworks','closure')))
        store('traffic:DE',dict(items=items or (old or {}).get('items',[]) if failed else items,status='partial' if failed else 'ok',observed_at=time.time() if items or not failed else (old or {}).get('observed_at'),failed_requests=failed,total_requests=len(roads)*3))

    def traffic_key():
        init()
        with m.db() as c:row=c.execute('SELECT value FROM regional_settings WHERE key="tomtom"').fetchone()
        return row[0] if row else os.getenv('TOMTOM_API_KEY','')

    @m.app.get('/api/regional/settings',dependencies=[Depends(m.auth)])
    def regional_settings():return dict(tomtom_configured=bool(traffic_key()))

    @m.app.put('/api/regional/settings',dependencies=[Depends(m.auth)])
    def regional_settings_save(body:TrafficKey):
        init()
        with m.db() as c:c.execute('INSERT OR REPLACE INTO regional_settings VALUES ("tomtom",?)',(body.key,))
        return dict(tomtom_configured=bool(body.key))

    @m.app.post('/api/regional/test',dependencies=[Depends(m.auth)])
    async def regional_test(body:TrafficTest):
        key=body.key.strip() or traffic_key()
        if not key:return dict(ok=False,message='Kein TomTom-Schlüssel hinterlegt oder eingegeben.')
        ch=coords(body.channel_id)
        try:
            result=await tomtom_fetch(key,ch['latitude'],ch['longitude'],min(10,ch['traffic_radius_km']))
            return dict(ok=True,upstream_status=200,incident_count=len(result['items']),message=f"TomTom Traffic erreichbar (HTTP 200). {len(result['items'])} Ereignisse im Testumkreis. Auch null Ereignisse sind ein erfolgreicher API-Test. Der vollständige Umkreis wird in passende Teilflächen aufgeteilt.")
        except HTTPException as error:return dict(ok=False,upstream_status=error.status_code,message=error.detail)

    @m.app.get('/api/traffic/{i}')
    async def traffic(i:int):
        ch=coords(i);radius=ch['traffic_radius_km'];key_value=traffic_key()
        if not key_value:
            if ch['country_code']!='DE':return dict(items=[],status='unsupported',radius_km=radius,source='Keine Verkehrsquelle verbunden',message='Für dieses Land einen TomTom-Traffic-Schlüssel in den Regionseinstellungen hinterlegen. Fehlende Daten bedeuten nicht freie Straßen.')
            stamp,data=cached('traffic:DE')
            if time.time()-stamp>600:launch('traffic:DE',autobahn_refresh)
            data=data or dict(items=[],status='loading')
            result=[dict(**x,distance_km=round(km(ch['latitude'],ch['longitude'],x['latitude'],x['longitude']),1)) for x in data['items'] if km(ch['latitude'],ch['longitude'],x['latitude'],x['longitude'])<=radius]
            result.sort(key=lambda x:x['distance_km'])
            observed=data.get('observed_at')
            return dict(items=result[:30],status='stale' if observed and time.time()-observed>1200 else data['status'],observed_at=observed,radius_km=radius,source='Autobahn GmbH · deutsche Autobahnen',message='Nur gemeldete Ereignispunkte im Luftlinienradius; keine vollständige Straßenabdeckung. Keine Meldungen bedeuten nicht freie Straßen.')
        digest=hashlib.sha256(key_value.encode()).hexdigest()[:12]
        cachekey=f'tomtom:v3:{digest}:{i}:{ch["latitude"]}:{ch["longitude"]}:{radius}'
        async with traffic_locks.setdefault(cachekey,asyncio.Lock()):
            stamp,data=cached(cachekey)
            if data is None or time.time()-stamp>300:
                try:
                    data=await tomtom_fetch(key_value,ch['latitude'],ch['longitude'],radius)
                    store(cachekey,data);stamp=time.time()
                except HTTPException as error:
                    if data is None:return dict(items=[],status='error',source='TomTom Traffic',radius_km=radius,message=error.detail,upstream_status=error.status_code)
                    return dict(**{**data,'items':data['items'][:30],'status':'stale','message':error.detail+' Vorherige Meldungen bleiben sichtbar.'},source='TomTom Traffic',radius_km=radius,observed_at=stamp)
        return dict(**{**data,'items':data['items'][:30],'status':'stale' if time.time()-stamp>600 else data['status']},observed_at=stamp,radius_km=radius,source='TomTom Traffic')

    async def loop():
        while True:
            for i in range(1,6):
                ch=m.get_channel(i)
                if ch['latitude'] is not None:
                    try:
                        await webcams(i)
                        if ch['enabled'] and 'traffic' in ch['pages']:await traffic(i)
                    except Exception:pass
            await asyncio.sleep(300)
    async def shutdown():
        for task in tasks.values():task.cancel()
        await asyncio.gather(*tasks.values(),return_exceptions=True)
    m.regional_loop=loop;m.regional_shutdown=shutdown
