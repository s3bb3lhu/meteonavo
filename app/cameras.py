"""Direct camera presentation with bounded public-only media fetching."""
import asyncio
import hashlib
import json
import re
import time
import uuid
from email.utils import parsedate_to_datetime,formatdate
from urllib.parse import urlsplit,urljoin,parse_qs
from fastapi import Depends,HTTPException
from fastapi.responses import Response
from pydantic import BaseModel,Field,field_validator,model_validator
from typing import Literal
from .radio_proxy import radio_url,open_public
from .regional import km

PRESETS=[
 dict(id='frankfurt-goetheturm',name='Frankfurt · Goetheturm',latitude=50.0838,longitude=8.7285,kind='iframe',media_url='https://goetheturm.panocloud.webcam/',source='Stadt Frankfurt / PanoCloud',url='https://frankfurt.de/aktuelle-meldung/meldungen/goetheturm-mit-webcam/'),
 dict(id='frankfurt-mainhattan',name='Frankfurt · Skyline am Main',latitude=50.105,longitude=8.696,kind='image',media_url='https://www.mainhattan-webcam.de/query?job=dzi&id=live&minsize=100',snapshot_adapter='mainhattan',source='Mainhattan-Webcam / Hi.Res.Cam',url='https://www.mainhattan-webcam.de/'),
 dict(id='bad-nauheim-bahnhof',name='Bad Nauheim · Bahnhof und Bahnhofsallee',latitude=50.3678,longitude=8.7478,kind='image',media_url='https://bahnhof.bad-nauheim-cam.de/bad-nauheim_bahnhof_west.jpg',source='Eisenbahnfreunde Wetterau / Bad Nauheim',url='https://www.bad-nauheim.de/de/erlebnisreich/blog-und-webcam/webcams-live-bilder'),
 dict(id='aschaffenburg-citygalerie',name='Aschaffenburg · Stadtpanorama',latitude=49.977,longitude=9.152,kind='image',media_url='https://webcam-aschaffenburg.de/images-webcams/webcam-citygalerie/panorama-stadt-aschaffenburg.jpg',source='Webcam Aschaffenburg · City Galerie',url='https://webcam-aschaffenburg.de/'),
 dict(id='calp-arenal-bol',name='Calp · Arenal-Bol',latitude=38.641,longitude=.049,kind='iframe',media_url='https://ibericam.com/player/modern/player.html?a=live&i=image-4&l=ibericam&ls=calpe&primaryColor=%230044aaff&s=4&v=calpe-playa-del-arenal-bol',source='Ibericam / Ayuntamiento de Calp',url='https://calp.es/en/webcams')]

YOUTUBE_HOSTS={'youtube.com','www.youtube.com','m.youtube.com','music.youtube.com','youtu.be','www.youtu.be','youtube-nocookie.com','www.youtube-nocookie.com'}


def youtube_video_id(url):
    try:parsed=urlsplit(url)
    except ValueError:raise ValueError('Gültigen YouTube-Video- oder Livestream-Link angeben')
    host=(parsed.hostname or '').lower().rstrip('.')
    if parsed.scheme not in ('http','https') or host not in YOUTUBE_HOSTS or parsed.username or parsed.password:raise ValueError('Nur echte öffentliche YouTube-Video-Links zulässig')
    parts=parsed.path.strip('/').split('/')
    if host in ('youtu.be','www.youtu.be') and len(parts)==1:video=parts[0]
    elif parts==['watch']:video=parse_qs(parsed.query).get('v',[''])[0]
    elif len(parts)==2 and parts[0] in ('embed','live','shorts'):video=parts[1]
    else:video=''
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}',video):raise ValueError('YouTube-Link benötigt eine Video-ID: watch?v=…, youtu.be/… oder /live/…. Kanal- und Playlist-Links sind nicht unterstützt.')
    return video


def is_youtube_url(url):
    try:return (urlsplit(url).hostname or '').lower().rstrip('.') in YOUTUBE_HOSTS
    except ValueError:return False


class Camera(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    kind:Literal['iframe','image','hls','youtube']='iframe'
    media_url:str=Field(min_length=8,max_length=4096)
    source:str=Field(default='',max_length=150)
    latitude:float=Field(ge=-85,le=85)
    longitude:float=Field(ge=-180,le=180)
    enabled:bool=True

    @field_validator('media_url')
    @classmethod
    def public_url(cls,value):
        if is_youtube_url(value):value='https://www.youtube.com/watch?v='+youtube_video_id(value)
        try:radio_url(value)
        except ValueError as e:raise ValueError('Öffentliche HTTP(S)-Kameraadresse ohne Zugangsdaten erforderlich') from e
        return value

    @model_validator(mode='after')
    def youtube_source(self):
        if is_youtube_url(self.media_url):self.kind='youtube'
        elif self.kind=='youtube':raise ValueError('Für YouTube einen YouTube-Video- oder Livestream-Link angeben')
        return self

class CameraPreferences(BaseModel):
    rotation_seconds:int=Field(default=60,ge=30,le=300)
    disabled_presets:list[str]=Field(default_factory=list,max_length=10)

def fetch(url,limit):
    conn=None
    try:
        conn,response,final=open_public(url)
        chunks=[];length=0;deadline=time.monotonic()+30
        while True:
            chunk=response.read(min(65536,limit-length+1))
            if not chunk:break
            length+=len(chunk)
            if length>limit or time.monotonic()>deadline:raise ValueError('Kameraantwort zu groß oder zu langsam')
            chunks.append(chunk)
        return b''.join(chunks),dict(response.getheaders()),final
    finally:
        if conn:conn.close()


def mainhattan_timestamp(body,now=None):
    """The published viewer returns JSON wrapped in parentheses, not executable JS."""
    if len(body)>65536:raise ValueError('Kamerametadaten zu groß')
    text=body.decode('utf-8').strip().removesuffix(';')
    if text.startswith('(') and text.endswith(')'):text=text[1:-1]
    data=json.loads(text)
    if not isinstance(data,list) or not data or not isinstance(data[0],dict):raise ValueError('Ungültige Kamerametadaten')
    value=data[0].get('timestamp')
    if isinstance(value,bool) or not re.fullmatch(r'\d{10}',str(value)):raise ValueError('Ungültige Kamera-Bildzeit')
    stamp=int(value);now=time.time() if now is None else now
    if not now-7*86400<=stamp<=now+300:raise ValueError('Keine verwendbare Kamera-Bildzeit')
    return stamp


def mainhattan_snapshot():
    # Public thumbnail route used by the provider's own archive viewer. No full
    # website/CMP scripts, tile scraping, original-size downloads, or access bypass.
    metadata,_,_=fetch('https://www.mainhattan-webcam.de/query?job=dzi&id=live&minsize=100',65536)
    stamp=mainhattan_timestamp(metadata)
    body,headers,final=fetch(f'https://www.mainhattan-webcam.de/thumbs/1280/{stamp}.JPG',2*1024*1024)
    if not body.startswith(b'\xff\xd8\xff'):raise ValueError('Anbieter liefert kein JPEG')
    headers={k.lower():v for k,v in headers.items()}
    headers['x-camera-captured-at']=str(stamp)
    headers['last-modified']=formatdate(stamp,usegmt=True)
    return body,headers,final

def install(m):
    checks={};images={};assets={};locks={};semaphore=asyncio.Semaphore(3)
    def init():
        with m.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS webcam_sources (id TEXT PRIMARY KEY,channel INTEGER,payload TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS webcam_preferences (channel INTEGER PRIMARY KEY,payload TEXT)')
    def preferences(i):
        init()
        with m.db() as c:row=c.execute('SELECT payload FROM webcam_preferences WHERE channel=?',(i,)).fetchone()
        return CameraPreferences.model_validate_json(row[0]).model_dump() if row else CameraPreferences().model_dump()
    def custom(i):
        init()
        with m.db() as c:rows=c.execute('SELECT id,payload FROM webcam_sources WHERE channel=? ORDER BY rowid',(i,)).fetchall()
        result=[]
        for cid,payload in rows:
            item=json.loads(payload)
            if item['kind']=='iframe' and item['media_url'].rstrip('/')=='https://www.mainhattan-webcam.de':
                preset=next(x for x in PRESETS if x['id']=='frankfurt-mainhattan')
                item={**item,'kind':'image','media_url':preset['media_url'],'snapshot_adapter':'mainhattan','url':'https://www.mainhattan-webcam.de/'}
            if item['kind']=='iframe' and is_youtube_url(item['media_url']):
                try:item={**item,'kind':'youtube','media_url':'https://www.youtube.com/watch?v='+youtube_video_id(item['media_url'])}
                except ValueError:pass
            result.append(dict(id=cid,**item))
        return result
    def sources(i):
        ch=m.get_channel(i)
        result=[x for x in custom(i) if x['enabled'] and (ch['latitude'] is None or km(ch['latitude'],ch['longitude'],x['latitude'],x['longitude'])<=100)]
        if ch['latitude'] is not None:
            disabled=preferences(i)['disabled_presets']
            result += [dict(**x,enabled=True) for x in PRESETS if x['id'] not in disabled and km(ch['latitude'],ch['longitude'],x['latitude'],x['longitude'])<=100]
        return result
    def find(i,cid):
        for item in sources(i):
            if item['id']==cid:return item
        raise HTTPException(404,'Kamera nicht ausgewählt oder deaktiviert')
    async def probe(item):
        if item['kind']=='youtube':return dict(checked_at=time.time(),available=True,playback_checked=False,message='YouTube-Wiedergabe wird beim Aufruf im offiziellen Player geprüft')
        url=item['media_url'];old=checks.get(url)
        if old and time.time()-old['checked_at']<60:return old
        key='probe:'+url
        async with locks.setdefault(key,asyncio.Lock()):
            old=checks.get(url)
            if old and time.time()-old['checked_at']<60:return old
            result=dict(checked_at=time.time(),available=False,message='Kameraquelle nicht erreichbar')
            def check():
                conn=None
                try:
                    conn,r,final=open_public(url)
                    headers={k.lower():v for k,v in r.getheaders()};r.read(512)
                    xfo=headers.get('x-frame-options','').lower();csp=headers.get('content-security-policy','').lower()
                    blocked=item['kind']=='iframe' and (xfo in ('deny','sameorigin') or 'frame-ancestors' in csp and "frame-ancestors *" not in csp)
                    return dict(checked_at=time.time(),available=not blocked,message='Anbieter blockiert die Einbettung' if blocked else 'Anbieter erreichbar · Aufnahmezeit im Kamerabild beachten')
                except Exception:return result
                finally:
                    if conn:conn.close()
            async with semaphore:result=await asyncio.to_thread(check)
            checks[url]=result;return result

    @m.app.get('/api/cameras/{i}')
    async def listing(i:int):
        ch=m.get_channel(i);items=sources(i)
        states=await asyncio.gather(*(probe(x) for x in items))
        data=[]
        for x,state in zip(items,states):
            media=('https://www.youtube-nocookie.com/embed/'+youtube_video_id(x['media_url'])) if x['kind']=='youtube' else x['media_url'] if x['kind']=='iframe' else f'/api/cameras/{i}/{x["id"]}/media'
            extra=dict(youtube_id=youtube_video_id(x['media_url']),url=x['media_url']) if x['kind']=='youtube' else {}
            data.append({k:v for k,v in x.items() if k!='media_url'}|dict(media=media,**state,**extra,distance_km=round(km(ch['latitude'],ch['longitude'],x['latitude'],x['longitude']),1) if ch['latitude'] is not None else None))
        return dict(items=data,rotation_seconds=preferences(i)['rotation_seconds'],message='Direkte Anbieteransicht. Quellenlogos und Aufnahmezeit bleiben sichtbar. Die Quellenprüfung bestätigt die Erreichbarkeit, nicht das Alter der Aufnahme.')

    @m.app.get('/api/cameras/{i}/settings',dependencies=[Depends(m.auth)])
    def settings(i:int):
        ch=m.get_channel(i);pref=preferences(i)
        return dict(items=custom(i),**pref,presets=[{k:v for k,v in x.items() if k!='media_url'}|dict(enabled=x['id'] not in pref['disabled_presets']) for x in PRESETS if ch['latitude'] is not None and km(ch['latitude'],ch['longitude'],x['latitude'],x['longitude'])<=100])

    @m.app.put('/api/cameras/{i}/settings',dependencies=[Depends(m.auth)])
    def save_preferences(i:int,body:CameraPreferences):
        m.get_channel(i);init()
        if not set(body.disabled_presets)<={x['id'] for x in PRESETS}:raise HTTPException(422,'Unbekannte Kameraauswahl')
        with m.db() as c:c.execute('INSERT OR REPLACE INTO webcam_preferences VALUES (?,?)',(i,body.model_dump_json()))
        return body.model_dump()

    @m.app.post('/api/cameras/{i}/settings',dependencies=[Depends(m.auth)])
    async def add(i:int,body:Camera):
        ch=m.get_channel(i)
        if ch['latitude'] is not None and km(ch['latitude'],ch['longitude'],body.latitude,body.longitude)>100:raise HTTPException(422,'Die Kamera liegt außerhalb des 100-km-Umkreises')
        if len(custom(i))>=8:raise HTTPException(422,'Höchstens acht eigene Kameras pro Kanal')
        # Resolve and validate redirects before accepting a URL; no internal proxy targets.
        if body.kind!='youtube':
            async with semaphore:
                try:
                    def verify():
                        conn,r,_=open_public(body.media_url)
                        try:r.read(128)
                        finally:conn.close()
                    await asyncio.to_thread(verify)
                except Exception:raise HTTPException(422,'Kameraadresse nicht öffentlich erreichbar oder durch Anbieter gesperrt')
        cid=uuid.uuid4().hex
        with m.db() as c:c.execute('INSERT INTO webcam_sources VALUES (?,?,?)',(cid,i,body.model_dump_json()))
        return dict(id=cid,**body.model_dump())

    @m.app.delete('/api/cameras/{i}/settings/{cid}',dependencies=[Depends(m.auth)])
    def delete(i:int,cid:str):
        m.get_channel(i);init()
        with m.db() as c:c.execute('DELETE FROM webcam_sources WHERE channel=? AND id=?',(i,cid))
        return dict(ok=True)

    @m.app.get('/api/cameras/{i}/{cid}/media')
    async def media(i:int,cid:str,asset:str='main'):
        item=find(i,cid)
        if item['kind'] in ('iframe','youtube'):raise HTTPException(404)
        now=time.time()
        # Only URLs emitted by a fetched manifest can become segment targets.
        if asset=='main':url=item['media_url']
        else:
            entry=assets.get((cid,asset))
            if not entry or now-entry[0]>1800:raise HTTPException(404,'Kamerasegment abgelaufen')
            url=entry[1]
        if item['kind']=='image' and url in images and now-images[url][0]<30:
            stamp,content,headers=images[url]
        else:
            async with locks.setdefault('media:'+cid,asyncio.Lock()):
                async with semaphore:
                    try:
                        content,headers,final=await asyncio.to_thread(mainhattan_snapshot) if item.get('snapshot_adapter')=='mainhattan' else await asyncio.to_thread(fetch,url,8*1024*1024)
                    except Exception:raise HTTPException(502,'Kein aktuelles Kamerabild verfügbar')
                headers={k.lower():v for k,v in headers.items()};stamp=time.time()
                if item['kind']=='image':
                    if not (content.startswith((b'\xff\xd8\xff',b'\x89PNG')) or content.startswith(b'RIFF') and content[8:12]==b'WEBP'):raise HTTPException(502,'Quelle liefert kein JPEG, PNG oder WebP')
                    images[url]=(stamp,content,headers)
                    if len(images)>40:images.pop(next(iter(images)))
        response_headers={'Cache-Control':'no-store','X-Camera-Fetched-At':str(stamp)}
        if headers.get('last-modified'):response_headers['X-Camera-File-Date']=headers['last-modified']
        if headers.get('x-camera-captured-at'):response_headers['X-Camera-Captured-At']=headers['x-camera-captured-at']
        if item['kind']=='image':
            content_type='image/png' if content.startswith(b'\x89PNG') else 'image/webp' if content.startswith(b'RIFF') else 'image/jpeg'
            return Response(content,media_type=content_type,headers=response_headers)
        if content.lstrip().startswith(b'#EXTM3U'):
            def rewrite(target):
                absolute=urljoin(final,target);radio_url(absolute)
                token=hashlib.sha256(absolute.encode()).hexdigest()[:24];assets[(cid,token)]=(now,absolute)
                return f'/api/cameras/{i}/{cid}/media?asset={token}'
            lines=[]
            try:
                for line in content.decode('utf-8-sig').splitlines():
                    if line and not line.startswith('#'):line=rewrite(line.strip())
                    elif 'URI="' in line:line=re.sub(r'URI="([^"]+)"',lambda x:'URI="'+rewrite(x[1])+'"',line)
                    lines.append(line)
            except (ValueError,UnicodeError):raise HTTPException(502,'Kameramanifest ungültig')
            for key in list(assets):
                if now-assets[key][0]>1800:assets.pop(key,None)
            if len(assets)>2000:
                for key in list(assets)[:len(assets)-2000]:assets.pop(key,None)
            return Response('\n'.join(lines)+'\n',media_type='application/vnd.apple.mpegurl',headers=response_headers)
        return Response(content,media_type=headers.get('content-type','application/octet-stream'),headers=response_headers)

    async def daily_checks():
        last={}
        while True:
            unique={x['media_url']:x for i in range(1,6) for x in sources(i)}
            for url,item in unique.items():
                if time.time()-last.get(url,0)>=86400:
                    await probe(item);last[url]=time.time()
            last={url:stamp for url,stamp in last.items() if url in unique}
            await asyncio.sleep(300)
    m.cameras_loop=daily_checks
