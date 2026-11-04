"""Administration help and bounded thumbnails from existing HLS output."""
import asyncio
import re
import time
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse


def install(m):
    folder=m.DATA/'thumbnails';folder.mkdir(parents=True,exist_ok=True);locks={i:asyncio.Lock() for i in range(1,6)}
    @m.app.get('/license')
    def project_license():return FileResponse(Path(__file__).resolve().parent.parent/'LICENSE',media_type='text/plain; charset=utf-8',headers={'Cache-Control':'no-store'})

    @m.app.get('/third-party-notices')
    def third_party_notices():return FileResponse(Path(__file__).resolve().parent.parent/'THIRD_PARTY_NOTICES.md',media_type='text/plain; charset=utf-8',headers={'Cache-Control':'no-store'})

    @m.app.get('/help')
    def help_page():return FileResponse(m.STATIC/'help.html',headers={'Cache-Control':'no-store'})

    @m.app.get('/api/thumbnail/{i}')
    async def thumbnail(i:int):
        channel=m.get_channel(i)
        if not channel['enabled'] or not m.stream_ready(i):raise HTTPException(404,'Kein Livebild verfügbar')
        path=folder/f'channel-{i}.jpg'
        async with locks[i]:
            if not path.exists() or time.time()-path.stat().st_mtime>30:
                try:
                    lines=(m.HLS/str(i)/'index.m3u8').read_text().splitlines();names=[line for line in lines if re.fullmatch(r'seg_\d+\.ts',line)]
                    source=m.HLS/str(i)/names[-1]
                except (OSError,IndexError):raise HTTPException(404,'Vorschaubild derzeit nicht verfügbar')
                target=path.with_suffix('.tmp.jpg')
                child=await asyncio.create_subprocess_exec('ffmpeg','-nostdin','-v','error','-threads','1','-y','-i',str(source),'-frames:v','1','-vf','scale=480:270','-q:v','5',str(target),stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
                try:
                    await asyncio.wait_for(child.wait(),10)
                    if child.returncode or not target.exists():raise HTTPException(404,'Vorschaubild derzeit nicht verfügbar')
                    target.replace(path)
                except TimeoutError:
                    child.kill();await child.wait();raise HTTPException(503,'Vorschaubild derzeit nicht verfügbar')
                finally:target.unlink(missing_ok=True)
        return FileResponse(path,media_type='image/jpeg',headers={'Cache-Control':'public, max-age=20'})
