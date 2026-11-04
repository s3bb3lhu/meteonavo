"""Settings, addresses, radio, music and ordered playlists."""
import asyncio
import json
import os
import re
import time
import uuid
from pathlib import Path
from urllib.parse import unquote,urlsplit
import httpx
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import FileResponse,PlainTextResponse,StreamingResponse,Response,RedirectResponse
from pydantic import BaseModel,Field,ConfigDict,ValidationError
from .catalog import sync_country
from .regions import COUNTRIES,STATES
from .radio_proxy import open_public,manifest

class Playlist(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=100)
    tracks:list[str]=Field(default_factory=list,max_length=500)

def install(m):
    router=APIRouter();db=m.db;media=Path(os.getenv('MEDIA_DIR',str(m.DATA/'music')))
    media.mkdir(parents=True,exist_ok=True)
    geolock=asyncio.Lock();uploadlock=asyncio.Semaphore(2);refreshlock=asyncio.Lock()
    last_geo=0
    def station(sid):
        with db() as c:row=c.execute('SELECT payload FROM stations WHERE id=?',(sid,)).fetchone()
        if not row:raise HTTPException(404,'Sender nicht im Verzeichnis')
        return json.loads(row[0])

    @router.get('/settings')
    @router.get('/settings/{section}')
    def settings(request:Request,section:str='channels'):
        from .accounts import configured,session
        if not configured(db):return RedirectResponse('/setup',status_code=303)
        if not session(db,request):return RedirectResponse('/login?next='+request.url.path,status_code=303)
        if section not in ['channels','design','audio','outputs','cameras']:raise HTTPException(404)
        return FileResponse(m.STATIC/'settings.html',headers={'Cache-Control':'no-store'})

    @router.get('/api/regions')
    def regions():
        return dict(countries=[dict(code=c,name=n) for c,n in COUNTRIES.items()],states=STATES)

    @router.patch('/api/channels/{i}',dependencies=[Depends(m.auth)])
    async def patch(i:int,request:Request):
        try:data=await request.json()
        except (ValueError,UnicodeError):raise HTTPException(422,'Ungültige JSON-Einstellungen')
        if not isinstance(data,dict):raise HTTPException(422,'Ungültige Einstellungen')
        try:channel=m.Channel.model_validate({**m.get_channel(i),**data})
        except ValidationError as e:raise HTTPException(422,str(e))
        validate_audio(channel)
        return await m.save(i,channel)

    def validate_audio(channel):
        if channel.audio_mode=='playlist':
            with db() as c:row=c.execute('SELECT tracks FROM playlists WHERE id=?',(channel.playlist_id,)).fetchone()
            if not row or not json.loads(row[0]):raise HTTPException(422,'Eine Playlist mit mindestens einem Titel auswählen')
        if channel.audio_mode=='radio':station(channel.radio_station)

    @router.get('/api/addresses',dependencies=[Depends(m.auth)])
    async def addresses(q:str='',country:str='DE'):
        nonlocal last_geo
        country=country.upper()
        if country not in COUNTRIES or not 3<=len(q.strip())<=300:raise HTTPException(422,'Land und vollständige Suchadresse prüfen')
        from .geocoding import search
        key='address-v2:'+country+':'+q.strip().casefold()
        with db() as c:cached=c.execute('SELECT stamp,payload FROM geocache WHERE key=?',(key,)).fetchone()
        if cached:
            value=json.loads(cached[1])
            if time.time()-cached[0]<(604800 if value else 300):return value
        async with geolock:
            async def throttle():
                nonlocal last_geo
                await asyncio.sleep(max(0,1.1-(time.monotonic()-last_geo)))
                last_geo=time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=25,headers={'User-Agent':'WeatherChannelStudio/0.2'}) as client:
                    results=await search(client,os.getenv('GEOCODER_URL','https://photon.komoot.io/api/'),q.strip(),country,throttle)
                with db() as c:c.execute('INSERT OR REPLACE INTO geocache VALUES (?,?,?)',(key,time.time(),json.dumps(results)))
                return results
            except (httpx.HTTPError,ValueError):raise HTTPException(503,'Adressdienst nicht erreichbar. Adresse und GPS-Koordinaten können manuell eingetragen werden.')

    @router.get('/api/warning-regions',dependencies=[Depends(m.auth)])
    async def warning_regions(country:str='DE'):
        from .warnings import country_feed
        data=await country_feed(db,country)
        return dict(regions=data.get('regions',[]),status=data['status'],message=data['message'])

    @router.get('/api/radio/countries',dependencies=[Depends(m.auth)])
    def radio_countries():
        with db() as c:
            counts=dict(c.execute('SELECT country,count(*) FROM stations GROUP BY country').fetchall())
            status={r[0]:dict(updated_at=r[1],error=r[2]) for r in c.execute('SELECT country,stamp,error FROM catalog_status')}
        return [dict(code=code,name=name,count=counts.get(code,0),**status.get(code,dict(updated_at=None,error='Erster Import läuft'))) for code,name in COUNTRIES.items()]

    @router.get('/api/radio/stations',dependencies=[Depends(m.auth)])
    def radio_stations(country:str='DE',state:str='',q:str='',offset:int=0,limit:int=60,working:bool=True):
        if country not in COUNTRIES:raise HTTPException(422,'Unbekanntes Land')
        query='SELECT id,payload,state FROM stations WHERE country=?';args=[country]
        if state:
            query+=' AND state=?';args.append('' if state=='unassigned' else state)
        if q:
            query+=' AND instr(lower(name),lower(?))>0';args.append(q[:100])
        if working:query+=" AND json_extract(payload,'$.lastcheckok')=1"
        with db() as c:
            total=c.execute('SELECT count(*) FROM ('+query+')',args).fetchone()[0]
            rows=c.execute(query+' ORDER BY name COLLATE NOCASE LIMIT ? OFFSET ?',args+[min(200,max(1,limit)),max(0,offset)]).fetchall()
        return dict(total=total,items=[dict(id=sid,name=(d:=json.loads(payload)).get('name',''),country=country,state=region,codec=d.get('codec',''),bitrate=d.get('bitrate',0),working=bool(d.get('lastcheckok')),tags=d.get('tags','')[:200]) for sid,payload,region in rows])

    @router.get('/api/radio/station/{sid}',dependencies=[Depends(m.auth)])
    def station_detail(sid:str):return station(sid)

    @router.post('/api/radio/refresh',dependencies=[Depends(m.auth)])
    async def radio_refresh(country:str='DE'):
        if country not in COUNTRIES:raise HTTPException(422)
        if refreshlock.locked():raise HTTPException(409,'Eine Aktualisierung läuft bereits')
        with db() as c:row=c.execute('SELECT attempt FROM catalog_status WHERE country=?',(country,)).fetchone()
        if row and time.time()-row[0]<600:raise HTTPException(429,'Frühestens nach zehn Minuten erneut aktualisieren')
        async with refreshlock:await sync_country(db,country)
        return dict(ok=True)

    @router.get('/api/radio/playlist/{country}.m3u',dependencies=[Depends(m.auth)])
    def radio_playlist(country:str,state:str=''):
        if country not in COUNTRIES:raise HTTPException(422)
        with db() as c:rows=c.execute('SELECT payload,state FROM stations WHERE country=? ORDER BY state,name',(country,)).fetchall()
        if state=='unassigned':state='__unassigned__'
        lines=['#EXTM3U']
        for payload,region in rows:
            d=json.loads(payload)
            if state and region!=('' if state=='__unassigned__' else state) or not d.get('lastcheckok'):continue
            url=d.get('url_resolved') or d.get('url','')
            if not url.startswith(('http://','https://')) or '\n' in url or '\r' in url:continue
            title=re.sub(r'[\r\n"<>]',' ',d.get('name','Radio'))[:200]
            lines.extend([f'#EXTINF:-1 group-title="{COUNTRIES[country]}",{title}',url])
        return PlainTextResponse('\n'.join(lines)+'\n',media_type='audio/x-mpegurl',headers={'Cache-Control':'no-store'})

    @router.get('/api/radio/stream/{sid}',dependencies=[Depends(m.auth)])
    async def radio_stream(sid:str,url:str=''):
        d=station(sid);url=url or d.get('url_resolved') or d.get('url','')
        try:
            for _ in range(4):
                conn,res,final=await asyncio.to_thread(open_public,url)
                kind=res.getheader('Content-Type','').split(';')[0]
                playlist=any(t in kind for t in ['mpegurl','scpls']) or urlsplit(final).path.lower().endswith(('.m3u','.m3u8','.pls'))
                if not playlist:break
                try:body=await asyncio.to_thread(res.read,1024*1024+1)
                finally:conn.close()
                if len(body)>1024*1024:raise ValueError('Radioplaylist zu groß')
                text=body.decode('utf-8-sig',errors='replace')
                if '#EXT-X-' in text:
                    prefix=f'/api/radio/stream/{sid}?url='
                    return Response(manifest(text,final,prefix),media_type='application/vnd.apple.mpegurl')
                targets=re.findall(r'^File\d+=(.+)$',text,re.M) if '[playlist]' in text.lower() else [l.strip() for l in text.splitlines() if l.strip() and not l.startswith('#')]
                if not targets:raise ValueError('Leere Radio-Playlist')
                from urllib.parse import urljoin
                url=urljoin(final,targets[0].strip())
            else:raise ValueError('Zu viele Radioplaylists')
        except Exception:raise HTTPException(502,'Radiostream derzeit nicht erreichbar')
        def chunks():
            try:
                while data:=res.read1(32768):yield data
            finally:conn.close()
        return StreamingResponse(chunks(),media_type=kind or 'application/octet-stream',headers={'Cache-Control':'no-store'})

    @router.get('/api/music',dependencies=[Depends(m.auth)])
    def music():
        with db() as c:return [dict(id=r[0],title=r[1],duration=r[2],bytes=r[3]) for r in c.execute('SELECT id,title,duration,bytes FROM music ORDER BY title')]

    @router.post('/api/music',dependencies=[Depends(m.auth)])
    async def upload(request:Request):
        if uploadlock.locked():raise HTTPException(429,'Zwei Uploads werden bereits verarbeitet')
        async with uploadlock:
            mid=uuid.uuid4().hex;temp=media/(mid+'.upload');target=media/(mid+'.m4a')
            title=Path(unquote(request.headers.get('x-filename','Musik')).replace('\\','/')).name
            title=re.sub(r'[\x00-\x1f]','',title)[:180] or 'Musik'
            process=None
            try:
                size=0
                with temp.open('wb') as f:
                    async for chunk in request.stream():
                        size+=len(chunk)
                        if size>100*1024*1024:raise HTTPException(413,'Maximal 100 MB pro Musikdatei')
                        f.write(chunk)
                if not size:raise HTTPException(422,'Leere Musikdatei')
                process=await asyncio.create_subprocess_exec('ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-protocol_whitelist','file,pipe','-i',str(temp),'-map','0:a:0','-vn','-t','7200','-c:a','aac','-b:a','160k','-ar','48000','-ac','2',str(target),stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
                await asyncio.wait_for(process.wait(),180)
                if process.returncode or not target.exists():raise HTTPException(422,'Keine unterstützte Audiodatei. Bitte MP3, WAV, FLAC, OGG oder M4A hochladen.')
                probe=await asyncio.create_subprocess_exec('ffprobe','-v','error','-show_entries','format=duration','-of','json',str(target),stdout=asyncio.subprocess.PIPE)
                out,_=await asyncio.wait_for(probe.communicate(),15);duration=float(json.loads(out)['format']['duration'])
                if duration<.1:raise HTTPException(422,'Audiodatei ist zu kurz')
                with db() as c:c.execute('INSERT INTO music VALUES (?,?,?,?,?)',(mid,title,target.name,duration,target.stat().st_size))
                return dict(id=mid,title=title,duration=duration)
            except BaseException:
                if process and process.returncode is None:process.kill();await process.wait()
                target.unlink(missing_ok=True);raise
            finally:temp.unlink(missing_ok=True)

    @router.get('/api/music/{mid}/file',dependencies=[Depends(m.auth)])
    def music_file(mid:str):
        with db() as c:row=c.execute('SELECT path FROM music WHERE id=?',(mid,)).fetchone()
        if not row:raise HTTPException(404)
        return FileResponse(media/row[0],media_type='audio/mp4')

    @router.delete('/api/music/{mid}',dependencies=[Depends(m.auth)])
    def delete_music(mid:str):
        with db() as c:
            if any(mid in json.loads(r[0]) for r in c.execute('SELECT tracks FROM playlists')):raise HTTPException(409,'Titel zuerst aus den Playlists entfernen')
            row=c.execute('SELECT path FROM music WHERE id=?',(mid,)).fetchone()
            if not row:raise HTTPException(404)
            c.execute('DELETE FROM music WHERE id=?',(mid,))
        (media/row[0]).unlink(missing_ok=True);return dict(ok=True)

    @router.get('/api/playlists',dependencies=[Depends(m.auth)])
    def playlists():
        with db() as c:return [dict(id=r[0],name=r[1],tracks=json.loads(r[2])) for r in c.execute('SELECT * FROM playlists ORDER BY name')]

    def write_playlist(pid,data):
        with db() as c:
            existing={r[0] for r in c.execute('SELECT id FROM music')}
            if any(t not in existing for t in data.tracks):raise HTTPException(422,'Playlist enthält einen unbekannten Titel')
            if not data.tracks and any(m.get_channel(i)['playlist_id']==pid and m.get_channel(i)['audio_mode']=='playlist' for i in range(1,6)):raise HTTPException(409,'Aktiv verwendete Playlist darf nicht leer sein')
            c.execute('INSERT OR REPLACE INTO playlists VALUES (?,?,?)',(pid,data.name,json.dumps(data.tracks)))
        return dict(id=pid,**data.model_dump())

    @router.post('/api/playlists',dependencies=[Depends(m.auth)])
    def create_playlist(data:Playlist):return write_playlist(uuid.uuid4().hex,data)

    @router.put('/api/playlists/{pid}',dependencies=[Depends(m.auth)])
    def update_playlist(pid:str,data:Playlist):
        with db() as c:
            if not c.execute('SELECT 1 FROM playlists WHERE id=?',(pid,)).fetchone():raise HTTPException(404)
        return write_playlist(pid,data)

    @router.delete('/api/playlists/{pid}',dependencies=[Depends(m.auth)])
    def delete_playlist(pid:str):
        if any(m.get_channel(i)['playlist_id']==pid for i in range(1,6)):raise HTTPException(409,'Playlist ist noch einem Kanal zugewiesen')
        with db() as c:c.execute('DELETE FROM playlists WHERE id=?',(pid,))
        return dict(ok=True)

    @router.get('/api/channels/{i}/audio',dependencies=[Depends(m.auth)])
    def audio(i:int):
        ch=m.get_channel(i);result=dict(mode=ch['audio_mode'],volume=ch['volume'],tracks=[],station=ch['radio_station'])
        with db() as c:
            if ch['audio_mode']=='playlist':
                row=c.execute('SELECT tracks FROM playlists WHERE id=?',(ch['playlist_id'],)).fetchone()
                for tid in json.loads(row[0]) if row else []:
                    track=c.execute('SELECT path FROM music WHERE id=?',(tid,)).fetchone()
                    if track:result['tracks'].append(str(media/track[0]))
            if ch['audio_mode']=='radio':
                try:
                    d=station(ch['radio_station']);result['url_revision']=d.get('url_resolved') or d.get('url')
                except HTTPException:result['mode']='off'
        return result

    m.validate_audio_config=validate_audio
    m.app.include_router(router)
