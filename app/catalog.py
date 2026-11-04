"""Persistent Radio Browser catalogue: daily, country-by-country, with mirror fallback."""
import asyncio
import json
import logging
import time
import httpx
from .regions import COUNTRIES, german_state

MIRRORS=['https://de1.api.radio-browser.info','https://nl1.api.radio-browser.info','https://at1.api.radio-browser.info']
log=logging.getLogger(__name__)

def init_catalog(db):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS stations (id TEXT PRIMARY KEY,country TEXT,state TEXT,name TEXT,payload TEXT)')
        c.execute('CREATE INDEX IF NOT EXISTS stations_country ON stations(country,state)')
        c.execute('CREATE TABLE IF NOT EXISTS catalog_status (country TEXT PRIMARY KEY,stamp REAL,attempt REAL,error TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS catalog_meta (key TEXT PRIMARY KEY,value TEXT)')
        version=c.execute("SELECT value FROM catalog_meta WHERE key='version'").fetchone()
        if not version or version[0]!='2':
            c.execute('UPDATE catalog_status SET stamp=NULL,attempt=0')
            c.execute("INSERT OR REPLACE INTO catalog_meta VALUES ('version','2')")
        c.execute('CREATE TABLE IF NOT EXISTS geocache (key TEXT PRIMARY KEY,stamp REAL,payload TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS music (id TEXT PRIMARY KEY,title TEXT,path TEXT,duration REAL,bytes INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS playlists (id TEXT PRIMARY KEY,name TEXT,tracks TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS warning_cache (key TEXT PRIMARY KEY,stamp REAL,payload TEXT)')

async def radio_get(path,params=None):
    for mirror in MIRRORS:
        try:
            async with httpx.AsyncClient(timeout=35,headers={'User-Agent':'WeatherChannelStudio/0.2'}) as client:
                async with client.stream('GET',mirror+path,params=params) as response:
                    response.raise_for_status();body=bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body)>32*1024*1024:raise ValueError('Senderantwort zu groß')
            return json.loads(body)
        except (httpx.HTTPError,ValueError):
            continue
    raise ValueError('Radio-Verzeichnis derzeit nicht erreichbar')

def station_record(row,code):
    if not row.get('stationuuid') or row.get('countrycode','').upper()!=code:return None
    return (row['stationuuid'],code,german_state(row.get('state')) if code=='DE' else row.get('state',''),
            str(row.get('name',''))[:200],json.dumps(row,ensure_ascii=False))

async def sync_country(db,code):
    now=time.time()
    try:
        data=[]
        for offset in range(0,100000,1000):
            batch=await radio_get('/json/stations/bycountrycodeexact/'+code,{'limit':1000,'offset':offset,'order':'name','reverse':'false'})
            if not isinstance(batch,list):raise ValueError('Ungültiges Senderverzeichnis')
            data.extend(batch)
            if len(batch)<1000:break
            await asyncio.sleep(.2)
        else:raise ValueError('Senderverzeichnis unvollständig')
        records=[r for row in data if (r:=station_record(row,code))]
        with db() as con:
            con.execute('DELETE FROM stations WHERE country=?',(code,))
            con.executemany('INSERT OR REPLACE INTO stations VALUES (?,?,?,?,?)',records)
            con.execute('INSERT OR REPLACE INTO catalog_status VALUES (?,?,?,?)',(code,now,now,''))
    except Exception:
        with db() as con:
            con.execute('INSERT INTO catalog_status VALUES (?,NULL,?,?) ON CONFLICT(country) DO UPDATE SET attempt=excluded.attempt,error=excluded.error',(code,now,'Aktualisierung fehlgeschlagen; gespeicherte Sender bleiben verfügbar'))

async def catalogue_loop(db):
    await asyncio.sleep(3)
    while True:
        # Germany first; all other countries are loaded without the user opening them.
        for code in ['DE']+[c for c in COUNTRIES if c!='DE']:
            with db() as con:row=con.execute('SELECT stamp,attempt FROM catalog_status WHERE country=?',(code,)).fetchone()
            if not row or time.time()-(row[0] or 0)>86400 and time.time()-row[1]>900:
                await sync_country(db,code)
                await asyncio.sleep(.4)
        await asyncio.sleep(300)
