"""Daily discovery of attributed Commons archive photos near the configured place."""
import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from fastapi import Depends, Request, Query
from typing import Literal
from fastapi.responses import FileResponse


def clean(value):return re.sub('<[^>]*>','',str(value or ''))[:600]


def install(m):
    lock=asyncio.Lock()
    upload_lock=asyncio.Lock()
    def slot_path(i,slot):
        m.get_channel(i)
        folder=m.DATA/'place-photos';folder.mkdir(exist_ok=True)
        return folder/f'channel-{i}-{slot}'
    async def photo(i,period='any',weather='any'):
        ch=m.get_channel(i)
        for slot in dict.fromkeys([period+'-'+weather,period+'-any','any-'+weather,'any-any']):
            path=slot_path(i,slot)
            if path.with_suffix('.jpg').exists() and path.with_suffix('.json').exists():
                data=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
                data['image']=f'/api/place-photo/{i}/image?period={period}&weather={weather}&v={int(data["checked_at"])}'
                return data,path.with_suffix('.jpg')
        if ch['latitude'] is None:raise HTTPException(409,'Standort fehlt')
        key=hashlib.sha256(f'{ch["latitude"]:.5f},{ch["longitude"]:.5f}'.encode()).hexdigest()[:20]
        folder=m.DATA/'place-photos';folder.mkdir(exist_ok=True);meta=folder/(key+'.json');image=folder/(key+'.jpg')
        async with lock:
            data=json.loads(meta.read_text()) if meta.exists() else None
            if not data or time.time()-data['checked_at']>86400:
                try:
                    async with httpx.AsyncClient(timeout=25,headers={'User-Agent':'WeatherChannelStudio/0.3 (attributed place archive photography)'}) as c:
                        r=await c.get('https://commons.wikimedia.org/w/api.php',params=dict(action='query',format='json',generator='geosearch',ggscoord=f'{ch["latitude"]}|{ch["longitude"]}',ggsradius=10000,ggsnamespace=6,ggslimit=12,prop='imageinfo',iiprop='url|extmetadata|size',iiurlwidth=1600));r.raise_for_status()
                        candidates=[]
                        for page in r.json().get('query',{}).get('pages',{}).values():
                            info=page.get('imageinfo',[{}])[0];ext=info.get('extmetadata',{});license=clean(ext.get('LicenseShortName',{}).get('value',''));url=info.get('thumburl') or info.get('url','')
                            if not license.startswith(('CC BY','CC0','Public domain')) or urlsplit(url).hostname!='upload.wikimedia.org':continue
                            if info.get('width',0)<1000 or info.get('width',0)/max(1,info.get('height',1))<1.2:continue
                            candidates.append((page,info,license,url))
                        if not candidates:raise ValueError('Keine passende freie Ortsaufnahme')
                        page,info,license,url=candidates[0]
                        async with c.stream('GET',url) as r:
                            r.raise_for_status();content=bytearray()
                            async for chunk in r.aiter_bytes():
                                content.extend(chunk)
                                if len(content)>8*1024*1024:raise ValueError('Foto zu groß')
                        if not bytes(content).startswith((b'\xff\xd8\xff',b'\x89PNG')):raise ValueError('Kein unterstütztes Foto')
                        image.write_bytes(content)
                        ext=info.get('extmetadata',{});data=dict(available=True,title=page['title'].removeprefix('File:'),artist=clean(ext.get('Artist',{}).get('value')),license=license,license_url=ext.get('LicenseUrl',{}).get('value',''),source_url=info.get('descriptionurl',''),checked_at=time.time(),image=f'/api/place-photo/{i}/image?v={int(time.time())}',message='Archivfoto aus bis zu 10 km Umgebung; Licht- und Wettereffekte sind Gestaltung, keine Liveaufnahme.')
                except (httpx.HTTPError,ValueError,KeyError,TypeError):
                    data={**(data or dict(available=False,message='Keine passende frei nutzbare Ortsaufnahme verfügbar. Gestalteter Hintergrund bleibt sichtbar.')),'checked_at':time.time(),'failed':True}
                meta.write_text(json.dumps(data),encoding='utf-8')
        return data,image

    @m.app.get('/api/place-photo/{i}')
    async def metadata(i:int,period:Literal['any','dawn','day','dusk','night']='any',weather:Literal['any','clear','clouds','rain','snow','fog','storm','unknown']='any'):
        data,_=await photo(i,period,weather);return data

    @m.app.get('/api/place-photo/{i}/image')
    async def image(i:int,period:Literal['any','dawn','day','dusk','night']='any',weather:Literal['any','clear','clouds','rain','snow','fog','storm','unknown']='any'):
        data,path=await photo(i,period,weather)
        if not data.get('available') or not path.exists():raise HTTPException(404,'Kein Ortsfoto vorhanden')
        return FileResponse(path,headers={'Cache-Control':'public, max-age=3600'})

    @m.app.get('/api/place-photo/{i}/uploads',dependencies=[Depends(m.auth)])
    def uploads(i:int):
        m.get_channel(i);folder=m.DATA/'place-photos'
        return [dict(slot=p.stem.removeprefix(f'channel-{i}-'),**json.loads(p.read_text(encoding='utf-8'))) for p in folder.glob(f'channel-{i}-*.json')] if folder.exists() else []

    @m.app.post('/api/place-photo/{i}/upload',dependencies=[Depends(m.auth)])
    async def upload(i:int,request:Request,period:Literal['any','dawn','day','dusk','night']='any',weather:Literal['any','clear','clouds','rain','snow','fog','storm']='any',credit:str=Query('',max_length=200)):
        path=slot_path(i,period+'-'+weather);incoming=path.with_suffix('.upload')
        if request.headers.get('content-type','').split(';')[0] not in ('image/jpeg','image/png','image/webp'):raise HTTPException(422,'JPEG, PNG oder WebP wählen')
        await upload_lock.acquire()
        size=0
        try:
            with incoming.open('wb') as f:
                async for chunk in request.stream():
                    size+=len(chunk)
                    if size>8*1024*1024:raise HTTPException(413,'Höchstens 8 MB pro Ortsfoto')
                    f.write(chunk)
            with incoming.open('rb') as f:header=f.read(12)
            if not (header.startswith((b'\xff\xd8\xff',b'\x89PNG')) or header.startswith(b'RIFF') and header[8:12]==b'WEBP'):
                raise HTTPException(422,'Datei ist kein JPEG, PNG oder WebP')
            proc=await asyncio.create_subprocess_exec('ffprobe','-v','error','-show_entries','stream=width,height','-of','json',str(incoming),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
            try:out,_=await asyncio.wait_for(proc.communicate(),15)
            except TimeoutError:proc.kill();await proc.wait();raise HTTPException(422,'Bildprüfung überschritten')
            try:
                dim=json.loads(out)['streams'][0]
                if not 1<=dim['width']*dim['height']<=40000000:raise ValueError()
            except (KeyError,ValueError,IndexError):raise HTTPException(422,'Bild konnte nicht geprüft werden')
            target=path.with_suffix('.tmp.jpg')
            proc=await asyncio.create_subprocess_exec('ffmpeg','-nostdin','-v','error','-y','-i',str(incoming),'-frames:v','1','-vf','scale=1600:900:force_original_aspect_ratio=increase,crop=1600:900','-q:v','3',str(target),stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
            try:await asyncio.wait_for(proc.wait(),25)
            except TimeoutError:proc.kill();await proc.wait();raise HTTPException(422,'Bildumwandlung überschritten')
            if proc.returncode:raise HTTPException(422,'Bild konnte nicht verarbeitet werden')
            target.replace(path.with_suffix('.jpg'))
            data=dict(available=True,title='Eigenes Ortsfoto',artist=credit.strip(),license='Eigener Upload',source_url='',checked_at=time.time(),message='Eigener Upload / Archivfoto. Licht und Wettereffekte sind Gestaltung, keine Liveaufnahme.')
            path.with_suffix('.json').write_text(json.dumps(data),encoding='utf-8')
            return dict(slot=period+'-'+weather,**data)
        finally:
            incoming.unlink(missing_ok=True)
            path.with_suffix('.tmp.jpg').unlink(missing_ok=True)
            upload_lock.release()

    @m.app.delete('/api/place-photo/{i}/upload/{slot}',dependencies=[Depends(m.auth)])
    def delete(i:int,slot:str):
        if not re.fullmatch('(any|dawn|day|dusk|night)-(any|clear|clouds|rain|snow|fog|storm)',slot):raise HTTPException(422,'Ungültiger Fotoplatz')
        path=slot_path(i,slot)
        path.with_suffix('.json').unlink(missing_ok=True);path.with_suffix('.jpg').unlink(missing_ok=True)
        return dict(ok=True)
