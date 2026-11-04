"""Validated per-channel raster TV logos; preserve transparency, no active SVG."""
import asyncio
import hashlib
import json
import uuid
from fastapi import Depends,HTTPException,Request,Query
from fastapi.responses import FileResponse


def install(m):
    folder=m.DATA/'logos';folder.mkdir(parents=True,exist_ok=True);lock=asyncio.Lock()
    def save_version(i,version):
        with m.db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row=connection.execute('SELECT config FROM channels WHERE id=?',(i,)).fetchone()
            if not row:raise HTTPException(404)
            channel=m.Channel.model_validate_json(row[0]).model_dump();channel['logo_version']=version
            if version and channel['logo_mode']=='off':channel['logo_mode']='location'
            if not version:channel['logo_mode']='off'
            connection.execute('UPDATE channels SET config=? WHERE id=?',(json.dumps(channel),i))
        return channel

    @m.app.get('/api/logo/{i}/image')
    def image(i:int,v:str=Query('',pattern=r'^[a-f0-9]{16}$|^$')):
        channel=m.get_channel(i);version=v or channel['logo_version']
        if not version:raise HTTPException(404,'Kein Logo hochgeladen')
        path=folder/f'channel-{i}-{version}.png'
        if not path.is_file():raise HTTPException(404,'Logo nicht verfügbar')
        return FileResponse(path,media_type='image/png',headers={'Cache-Control':'public, max-age=31536000, immutable' if v else 'no-store','X-Content-Type-Options':'nosniff'})

    @m.app.post('/api/logo/{i}',dependencies=[Depends(m.auth)])
    async def upload(i:int,request:Request):
        m.get_channel(i)
        if request.headers.get('content-type','').split(';')[0] not in ('image/png','image/jpeg','image/webp'):raise HTTPException(422,'PNG, JPEG oder WebP wählen. Für Transparenz PNG oder WebP verwenden.')
        async with lock:
            token=uuid.uuid4().hex;incoming=folder/(token+'.upload');target=folder/(token+'.png');size=0
            async def process(*args,timeout=20):
                child=await asyncio.create_subprocess_exec(*args,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
                try:out,_=await asyncio.wait_for(child.communicate(),timeout)
                except TimeoutError:
                    child.kill();await child.wait();raise HTTPException(422,'Logo-Verarbeitung hat zu lange gedauert')
                if child.returncode:raise HTTPException(422,'Bild konnte nicht gelesen werden')
                return out
            try:
                with incoming.open('wb') as file:
                    async for chunk in request.stream():
                        size+=len(chunk)
                        if size>5*1024*1024:raise HTTPException(413,'Maximal 5 MB pro Logo')
                        file.write(chunk)
                header=incoming.read_bytes()[:12]
                if not (header.startswith((b'\x89PNG',b'\xff\xd8\xff')) or header.startswith(b'RIFF') and header[8:12]==b'WEBP'):raise HTTPException(422,'Kein gültiges Rasterbild')
                out=await process('ffprobe','-v','error','-show_entries','stream=width,height','-of','json',str(incoming))
                try:
                    dimensions=json.loads(out)['streams'][0]
                    if not 1<=dimensions['width']*dimensions['height']<=16000000:raise ValueError()
                except (ValueError,KeyError,IndexError,TypeError):raise HTTPException(422,'Logo ist zu groß oder ungültig (max. 16 Megapixel)')
                await process('ffmpeg','-nostdin','-v','error','-y','-i',str(incoming),'-frames:v','1','-vf',"scale=w='min(512,iw)':h='min(512,ih)':force_original_aspect_ratio=decrease",'-pix_fmt','rgba',str(target))
                version=hashlib.sha256(target.read_bytes()).hexdigest()[:16];target.replace(folder/f'channel-{i}-{version}.png');channel=save_version(i,version)
                for old in folder.glob(f'channel-{i}-*.png'):
                    if old.name!=f'channel-{i}-{version}.png':old.unlink(missing_ok=True)
                return dict(version=version,logo_mode=channel['logo_mode'],message='Logo gespeichert. Position und Größe unten einstellen und Design speichern.')
            finally:
                incoming.unlink(missing_ok=True);target.unlink(missing_ok=True)

    @m.app.delete('/api/logo/{i}',dependencies=[Depends(m.auth)])
    async def remove(i:int):
        m.get_channel(i)
        async with lock:
            save_version(i,'')
            for old in folder.glob(f'channel-{i}-*.png'):old.unlink(missing_ok=True)
        return dict(ok=True)
