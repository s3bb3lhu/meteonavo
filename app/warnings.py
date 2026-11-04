"""Official MeteoAlarm Atom warnings, exact region matching, expiry and stale handling."""
import asyncio
import json
import re
import time
import unicodedata
from datetime import datetime
import httpx
from defusedxml import ElementTree as ET

FEEDS=dict(zip('AD AT BE BA BG HR CY CZ DK EE FI FR DE GR HU IS IE IT LV LT LU MT MD ME NL MK NO PL PT RO RS SK SI ES SE CH UA GB'.split(),
 'andorra austria belgium bosnia-herzegovina bulgaria croatia cyprus czechia denmark estonia finland france germany greece hungary iceland ireland italy latvia lithuania luxembourg malta moldova montenegro netherlands republic-of-north-macedonia norway poland portugal romania serbia slovakia slovenia spain sweden switzerland ukraine united-kingdom'.split()))
ATOM='{http://www.w3.org/2005/Atom}';CAP='{urn:oasis:names:tc:emergency:cap:1.2}'
locks={}
attempts={}

def normalized(value):
    value=unicodedata.normalize('NFKD',value.casefold()).encode('ascii','ignore').decode()
    return re.sub(r'[^a-z0-9]','',re.sub(r'^(landkreis|kreis|stadt|district|city of)\s+','',value))

def stamp(value):
    try:return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
    except (ValueError,AttributeError):return None

def parse_feed(body,now=None):
    now=time.time() if now is None else now
    root=ET.fromstring(body,forbid_dtd=True)
    if root.tag!=ATOM+'feed':raise ValueError('Kein amtlicher Atom-Feed')
    warnings=[];regions=set()
    for e in root.findall(ATOM+'entry'):
        val=lambda key:e.findtext(CAP+key,'')
        area=val('areaDesc');regions.add(area)
        if val('status') not in ('Actual','') or val('message_type')=='Cancel' or val('scope') not in ('Public',''):continue
        expires=stamp(val('expires'));onset=stamp(val('onset'))
        if expires is None or expires<=now:continue
        level={'Extreme':4,'Severe':3,'Moderate':2,'Minor':2}.get(val('severity'),0)
        if level<2:continue
        # A feed region is an explicit administrative warning region, not a whole-country alert.
        codes=[g.findtext('value','') or g.findtext(CAP+'value','') or g.findtext(ATOM+'value','') for g in e.findall(CAP+'geocode')]
        warnings.append(dict(id=val('identifier') or e.findtext(ATOM+'id',''),headline=e.findtext(ATOM+'title','Wetterwarnung'),area=area,codes=codes,level=level,onset=onset,expires=expires,sent=stamp(val('sent')) or 0,source='MeteoAlarm / nationaler Wetterdienst',url='https://meteoalarm.org'))
    return dict(items=warnings,regions=sorted(r for r in regions if r))

async def country_feed(db,country):
    if country not in FEEDS:return dict(items=[],regions=[],status='unsupported',message='Für dieses Land ist keine amtliche Warnquelle angebunden.')
    async with locks.setdefault(country,asyncio.Lock()):
        key='feed:'+country
        with db() as c:cached=c.execute('SELECT stamp,payload FROM warning_cache WHERE key=?',(key,)).fetchone()
        if cached and time.time()-cached[0]<300:
            data=json.loads(cached[1]);return {**data,'status':'ok','message':''}
        if time.time()-attempts.get(country,0)<60:
            data=json.loads(cached[1]) if cached and time.time()-cached[0]<3600 else dict(items=[],regions=[])
            return {**data,'status':'stale' if data['items'] else 'unavailable','message':'Amtliche Warnquelle derzeit nicht erreichbar. Keine Entwarnung ableitbar.'}
        attempts[country]=time.time()
        try:
            async with httpx.AsyncClient(timeout=25,headers={'User-Agent':'WeatherChannelStudio/0.2'}) as client:
                async with client.stream('GET','https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-'+FEEDS[country]) as response:
                    response.raise_for_status();body=bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body)>8*1024*1024:raise ValueError('Warnfeed zu groß')
            data=parse_feed(body)
            with db() as c:c.execute('INSERT OR REPLACE INTO warning_cache VALUES (?,?,?)',(key,time.time(),json.dumps(data)))
            return {**data,'status':'ok','message':''}
        except Exception:
            data=json.loads(cached[1]) if cached and time.time()-cached[0]<3600 else dict(items=[],regions=[])
            return {**data,'status':'stale' if data['items'] else 'unavailable','message':'Amtliche Warnquelle derzeit nicht erreichbar. Keine Entwarnung ableitbar.'}

async def dwd_region(db,lat,lon):
    key=f'dwd:{lat}:{lon}'
    with db() as c:row=c.execute('SELECT stamp,payload FROM warning_cache WHERE key=?',(key,)).fetchone()
    if row and time.time()-row[0]<2592000:return json.loads(row[1])
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r=await client.get('https://maps.dwd.de/geoserver/dwd/ows',params=dict(service='WFS',version='2.0.0',request='GetFeature',typeNames='dwd:Warngebiete_Kreise',outputFormat='application/json',srsName='EPSG:4326',bbox=f'{lon-.000001},{lat-.000001},{lon+.000001},{lat+.000001},EPSG:4326'))
            r.raise_for_status();features=r.json().get('features',[])
        # A tiny bounding box must identify exactly one official region.
        if len(features)!=1:return []
        props=features[0].get('properties',{})
        names=[str(v) for k,v in props.items() if isinstance(v,str) and ('name' in k.lower())]
        with db() as c:c.execute('INSERT OR REPLACE INTO warning_cache VALUES (?,?,?)',(key,time.time(),json.dumps(names)))
        return names
    except Exception:return []

async def channel_warnings(db,ch):
    if not ch.get('warnings_enabled',True):return dict(status='disabled',items=[],message='')
    country=ch.get('country_code','');data=await country_feed(db,country)
    if data['status'] in ['unsupported','unavailable']:return data
    explicit=ch.get('warning_region','')
    names=[explicit] if explicit else [ch.get('county',''),ch.get('location','')]
    dwd_names=[]
    if not explicit and country=='DE' and ch.get('latitude') is not None:
        dwd_names=await dwd_region(db,ch['latitude'],ch['longitude']);names=dwd_names or names
    normalized_names={normalized(n) for n in names if n}
    matching=[w for w in data['items'] if normalized(w['area']) in normalized_names or explicit in w['codes'] and explicit]
    now=time.time();unique={}
    for w in matching:
        if w['expires']<=now:continue
        key=(w['id'],w['area'])
        if key not in unique or w['sent']>unique[key]['sent']:unique[key]=w
    items=sorted(unique.values(),key=lambda w:(-w['level'],w['onset'] or 0))
    resolved=bool(explicit or country=='DE' and dwd_names or any(normalized(r) in normalized_names for r in data['regions']))
    if not items and data['items'] and not resolved:return dict(status='needs_region',items=[],message='Warnregion bitte in den Kanaleinstellungen bestätigen. Keine regionale Entwarnung möglich.',regions=data['regions'])
    return dict(status=data['status'],items=items,message=data['message'],regions=data['regions'],region=', '.join(n for n in names if n))
