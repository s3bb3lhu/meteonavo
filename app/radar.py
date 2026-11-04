"""Cached, bounded access to real past radar composites. No synthetic nowcast."""
import asyncio
import hashlib
import json
import re
import struct
import time
from collections import deque
from pathlib import Path
from fastapi import APIRouter,HTTPException,Query,Request
from fastapi.responses import FileResponse
import httpx

HOST='https://tilecache.rainviewer.com'
METADATA='https://api.rainviewer.com/public/weather-maps.json'

def parse_metadata(data,now=None):
    now=time.time() if now is None else now
    if data.get('host')!=HOST:raise ValueError('Unbekannter Radar-Bildserver')
    frames=[]
    for f in data.get('radar',{}).get('past',[]):
        stamp=f.get('time');path=f.get('path','')
        if not isinstance(stamp,int) or not now-10800<=stamp<=now+300:continue
        if not re.fullmatch(r'/v2/radar/[A-Za-z0-9_-]{1,64}',path):continue
        frames.append(dict(time=stamp,path=path))
    frames=sorted({f['time']:f for f in frames}.values(),key=lambda f:f['time'])[-13:]
    if not frames:raise ValueError('Keine aktuellen vergangenen Radarbilder')
    return dict(frames=frames,generated=data.get('generated'),host=HOST)

def position(channel):
    lat,lon=channel['latitude'],channel['longitude']
    if lat is None or lon is None:raise HTTPException(409,'Bitte zuerst GPS-Koordinaten für diesen Kanal speichern.')
    if not -85.051129<=lat<=85.051129:raise HTTPException(422,'Dieser GPS-Punkt liegt außerhalb der darstellbaren Radarprojektion.')
    lat,lon=round(lat,6),round(lon,6)
    key=hashlib.sha256(f'{lat:.6f},{lon:.6f}'.encode()).hexdigest()[:16]
    return lat,lon,key

class RadarCache:
    def __init__(self,folder):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
        self.meta_lock=asyncio.Lock();self.image_lock=asyncio.Lock();self.request_lock=asyncio.Lock()
        self.state=None;self.stamp=0;self.attempt=0;self.calls=deque();self.last_request=0
        try:
            saved=json.loads((self.folder/'metadata.json').read_text())
            self.state=parse_metadata(saved['data']);self.stamp=saved['stamp']
        except (OSError,ValueError,KeyError,TypeError):pass

    async def download(self,url,limit):
        async with self.request_lock:
            now=time.monotonic()
            while self.calls and self.calls[0]<now-60:self.calls.popleft()
            if len(self.calls)>=75:raise HTTPException(503,'Radarquelle ausgelastet. Die Ansicht versucht es später erneut.')
            await asyncio.sleep(max(0,.9-(now-self.last_request)))
            self.last_request=time.monotonic();self.calls.append(self.last_request)
            try:
                async with httpx.AsyncClient(timeout=20,headers={'User-Agent':'WeatherChannelStudio/0.2 (+https://github.com/s3bb3lhu/meteonavo)'}) as client:
                    async with client.stream('GET',url) as response:
                        response.raise_for_status();body=bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body)>limit:raise ValueError('Radarantwort zu groß')
                return bytes(body)
            except (httpx.HTTPError,ValueError):raise HTTPException(503,'Radarquelle derzeit nicht erreichbar.')

    async def metadata(self):
        async with self.meta_lock:
            now=time.time();failed=False
            if not self.state or now-self.stamp>180:
                if now-self.attempt<60:failed=True
                else:
                    self.attempt=now
                    try:
                        data=json.loads(await self.download(METADATA,1024*1024));state=parse_metadata(data)
                        self.state=state;self.stamp=now
                        (self.folder/'metadata.json').write_text(json.dumps(dict(data=data,stamp=now)))
                    except (HTTPException,ValueError,TypeError,OSError):failed=True
            if not self.state or now-self.stamp>3600:raise HTTPException(503,'Aktuell sind keine verwendbaren Radarbilder verfügbar.')
            frames=[f for f in self.state['frames'] if now-10800<=f['time']<=now+300]
            if not frames:raise HTTPException(503,'Die verfügbaren Radarbilder sind zu alt.')
            stale=failed or now-frames[-1]['time']>1800
            return {**self.state,'frames':frames,'stale':stale}

    async def image(self,channel,zoom,frame=None,coverage=False):
        lat,lon,key=position(channel)
        if coverage:
            url=HOST+f'/v2/coverage/0/512/{zoom}/{lat:.6f}/{lon:.6f}/0/0_0.png'
        else:
            metadata=await self.metadata();found=next((f for f in metadata['frames'] if f['time']==frame),None)
            if not found:raise HTTPException(404,'Radarbild nicht mehr im verfügbaren Zeitfenster')
            url=HOST+found['path']+f'/512/{zoom}/{lat:.6f}/{lon:.6f}/2/0_0.png'
        digest=hashlib.sha256(url.encode()).hexdigest();path=self.folder/(digest+'.png')
        async with self.image_lock:
            ttl=86400 if coverage else 10800
            if not path.exists() or time.time()-path.stat().st_mtime>ttl:
                body=await self.download(url,2*1024*1024)
                if len(body)<24 or not body.startswith(b'\x89PNG\r\n\x1a\n') or struct.unpack('>II',body[16:24])!=(512,512):raise HTTPException(503,'Ungültiges Radarbild erhalten')
                path.write_bytes(body)
                files=sorted(self.folder.glob('*.png'),key=lambda f:f.stat().st_mtime)
                size=sum(f.stat().st_size for f in files)
                for f in files:
                    if f==path:continue
                    if time.time()-f.stat().st_mtime>86400 or size>128*1024*1024:
                        size-=f.stat().st_size;f.unlink(missing_ok=True)
        return path

def install(m):
    router=APIRouter();cache=RadarCache(m.DATA/'radar-cache')
    street_folder=m.DATA/'street-cache';street_folder.mkdir(exist_ok=True);street_lock=asyncio.Lock()

    @router.get('/api/radar/map/{style}/{z}/{x}/{y}.png')
    async def streets(request:Request,style:str,z:int,x:int,y:int):
        if style not in ('streets','satellite'):raise HTTPException(422,'Unbekannter Kartenstil')
        if not 0<=z<=18 or not 0<=x<2**z or not 0<=y<2**z:raise HTTPException(422,'Ungültige Kartenkachel')
        path=street_folder/f'{style}-{z}-{x}-{y}.tile'
        async with street_lock:
            if not path.exists() or time.time()-path.stat().st_mtime>7*86400:
                try:
                    async with httpx.AsyncClient(timeout=15,headers={'User-Agent':'WeatherChannelStudio/0.2 (+https://github.com/s3bb3lhu/meteonavo)','Referer':request.headers.get('referer',str(request.base_url))}) as client:
                        url=f'https://tile.openstreetmap.org/{z}/{x}/{y}.png' if style=='streets' else f'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
                        r=await client.get(url);r.raise_for_status()
                    if len(r.content)>1024*1024 or not (r.content.startswith(b'\x89PNG\r\n\x1a\n') or r.content.startswith(b'\xff\xd8\xff')):raise ValueError('Ungültige Kartenkachel')
                    files=list(street_folder.glob('*.tile'))
                    if sum(f.stat().st_size for f in files)>256*1024*1024:
                        for old in files:
                            if time.time()-old.stat().st_mtime>7*86400:old.unlink(missing_ok=True)
                        if sum(f.stat().st_size for f in street_folder.glob('*.tile'))>256*1024*1024:raise ValueError('Kartencache voll')
                    path.write_bytes(r.content)
                except (httpx.HTTPError,ValueError,OSError):
                    if not path.exists():raise HTTPException(503,'Straßenkarte derzeit nicht verfügbar')
        return FileResponse(path,media_type='image/jpeg' if path.read_bytes().startswith(b'\xff\xd8') else 'image/png',headers={'Cache-Control':'private, max-age=604800'})


    @router.get('/api/radar/geography')
    def geography():
        return FileResponse(m.STATIC/'maps'/'radar-geography.json.gz',media_type='application/json',headers={'Content-Encoding':'gzip','Cache-Control':'public, max-age=86400'})

    @router.get('/api/radar/{i}')
    async def metadata(i:int):
        ch=m.get_channel(i);lat,lon,key=position(ch);data=await cache.metadata()
        return dict(latitude=lat,longitude=lon,position=key,zoom=ch['radar_zoom'],radius_km=ch.get('radar_radius_km'),stale=data['stale'],frames=[dict(time=f['time']) for f in data['frames']],source='RainViewer',source_url='https://www.rainviewer.com/',forecast=False,message='Vergangene Radar-Komposite; Bildzeit ist die Kompositzeit. Einzelne Radare können zeitlich abweichen.')

    @router.get('/api/radar/{i}/image/{frame}')
    async def image(i:int,frame:int,zoom:int=Query(6,ge=1,le=7),position_key:str=Query('',alias='position')):
        ch=m.get_channel(i)
        if position_key!=position(ch)[2]:raise HTTPException(409,'Standort wurde geändert. Radaransicht neu laden.')
        path=await cache.image(ch,zoom,frame)
        return FileResponse(path,media_type='image/png',headers={'Cache-Control':'public, max-age=600'})

    @router.get('/api/radar/{i}/coverage')
    async def coverage(i:int,zoom:int=Query(6,ge=1,le=7),position_key:str=Query('',alias='position')):
        ch=m.get_channel(i)
        if position_key!=position(ch)[2]:raise HTTPException(409,'Standort wurde geändert. Radaransicht neu laden.')
        path=await cache.image(ch,zoom,coverage=True)
        return FileResponse(path,media_type='image/png',headers={'Cache-Control':'public, max-age=86400'})

    m.radar_cache=cache;m.app.include_router(router)
