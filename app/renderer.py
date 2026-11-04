"""One supervised Chromium page and FFmpeg encoder per enabled channel."""
import asyncio
import base64
import logging
import os
import signal
import re
import time
from urllib.parse import urlsplit
from pathlib import Path

from .audio_worker import AudioPipe
import httpx
from playwright.async_api import async_playwright

API = os.getenv('API_URL', 'http://api:8080').rstrip('/')
ROOT = Path(os.getenv('HLS_DIR', '/hls'))
FPS = max(1, min(30, int(os.getenv('FPS', '15'))))
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('renderer')


def command(folder, audio_fd=None):
    # Epoch-based sequence prevents collisions with old segments after a restart.
    return ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y',
            '-thread_queue_size', '64', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-framerate', str(FPS), '-i', 'pipe:0',
            *(['-thread_queue_size','64','-f','s16le','-ar','48000','-ac','2','-i',f'pipe:{audio_fd}'] if audio_fd is not None else ['-thread_queue_size','64','-re','-f','lavfi','-i','anullsrc=r=48000:cl=stereo']),
            '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'ultrafast',
            '-tune', 'zerolatency', '-threads', '2', '-pix_fmt', 'yuv420p',
            '-b:v', '1600k', '-maxrate', '2000k', '-bufsize', '4000k',
            '-g', str(FPS * 2), '-keyint_min', str(FPS * 2), '-sc_threshold', '0',
            '-c:a', 'aac', '-b:a', '64k', '-ar', '48000',
            '-f', 'hls', '-hls_time', '2', '-hls_list_size', '6',
            '-hls_start_number_source', 'epoch', '-hls_flags', 'delete_segments+temp_file+independent_segments',
            '-hls_segment_filename', str(folder / 'seg_%d.ts'), str(folder / 'index.m3u8')]


class BrowserFrames:
    """Receive compositor frames without screenshot round trips; retain only newest."""
    def __init__(self, page):
        self.page, self.client = page, None
        self.latest, self.error = None, None
        self.updated = 0
        self.ready = asyncio.Event()
        self.closed = False

    async def frame(self, event):
        try:
            if not self.closed:
                self.latest = base64.b64decode(event['data'], validate=True)
                self.updated = time.monotonic()
                self.ready.set()
            await self.client.send('Page.screencastFrameAck', {'sessionId': event['sessionId']})
        except Exception as error:
            if not self.closed:
                self.error = error
                self.ready.set()

    async def start(self):
        self.client = await self.page.context.new_cdp_session(self.page)
        self.client.on('Page.screencastFrame', self.frame)
        await self.client.send('Page.startScreencast', {
            'format': 'jpeg', 'quality': 85, 'maxWidth': 1280,
            'maxHeight': 720, 'everyNthFrame': max(1, 30 // FPS)})
        await asyncio.wait_for(self.ready.wait(), 15)
        self.check()

    def check(self):
        if self.error:
            raise RuntimeError('Browser-Bildaufnahme fehlgeschlagen') from self.error
        if self.latest is None or time.monotonic() - self.updated > 15:
            raise RuntimeError('Keine aktuellen Browserbilder')

    async def close(self):
        self.closed = True
        if self.client:
            try:
                await self.client.send('Page.stopScreencast')
                await self.client.detach()
            except Exception:
                log.debug('Browser-Bildaufnahme bereits beendet', exc_info=True)


async def prepare_camera_players(page):
    """Use only essential cookies in the known provider player; retain its branding."""
    while True:
        for frame in page.frames[1:]:
            host=urlsplit(frame.url).hostname or ''
            if host.endswith('.panocloud.webcam') or host=='ibericam.com':
                try:
                    button=frame.get_by_text(re.compile(r'^(Nur technisch erforderliche|Technically required only|Only necessary)$', re.I)).first
                    if await button.is_visible():await button.click(timeout=1000)
                    await frame.evaluate("document.querySelectorAll('video').forEach(v=>{v.muted=true;if(v.paused)v.play().catch(()=>{});})")
                except Exception:
                    pass
        await asyncio.sleep(3)


async def encode(browser, i):
    folder = ROOT / str(i)
    folder.mkdir(parents=True, exist_ok=True)
    for path in folder.iterdir():
        if path.is_file():
            path.unlink()
    page = await browser.new_page(viewport={'width': 1280, 'height': 720}, device_scale_factor=1)
    process = None
    capture = None
    camera_task = None
    audio = AudioPipe(API,i)
    try:
        # Live players can keep network requests open indefinitely.
        await page.goto(f'{API}/view/{i}?render=1', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_function('typeof channel !== "undefined" && channel !== null',timeout=30000)
        camera_task = asyncio.create_task(prepare_camera_players(page))
        capture = BrowserFrames(page)
        await capture.start()
        process = await asyncio.create_subprocess_exec(*command(folder,audio.read_fd), stdin=asyncio.subprocess.PIPE,pass_fds=(audio.read_fd,))
        audio.start()
        log.info('Kanal %s gestartet', i)
        deadline=time.monotonic()
        while process.returncode is None:
            capture.check()
            # Keep video time aligned with wall/audio time. A slow browser capture
            # repeats the newest complete JPEG instead of slowing the HLS clock.
            process.stdin.write(capture.latest)
            await asyncio.wait_for(process.stdin.drain(),15)
            deadline+=1/FPS
            await asyncio.sleep(max(0,deadline-time.monotonic()))
            if deadline<time.monotonic()-.5:deadline=time.monotonic()
        raise RuntimeError(f'FFmpeg exit {process.returncode}')
    finally:
        if camera_task:
            camera_task.cancel()
            await asyncio.gather(camera_task, return_exceptions=True)
        if capture:
            await capture.close()
        # Both input pipes need EOF before FFmpeg can exit gracefully. Keeping
        # the live PCM writer open made shutdown wait and require a hard kill.
        await audio.close()
        if process and process.returncode is None:
            try:
                process.stdin.close()
                await asyncio.wait_for(process.wait(), 5)
            except (TimeoutError, BrokenPipeError, ConnectionResetError):
                process.kill()
                await process.wait()
        await page.close()
        (folder / 'index.m3u8').unlink(missing_ok=True)


async def main():
    tasks = {}
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    async with async_playwright() as p, httpx.AsyncClient(timeout=10) as client:
        browser = await p.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE','/usr/bin/chromium'), headless=True, args=['--no-sandbox', '--disable-dev-shm-usage', '--autoplay-policy=no-user-gesture-required'])
        try:
            while not stop.is_set():
                try:
                    r = await client.get(f'{API}/api/channels')
                    r.raise_for_status()
                    active = {c['id'] for c in r.json() if c['enabled']}
                    for i in list(tasks):
                        if i not in active or tasks[i].done():
                            tasks[i].cancel()
                            result = await asyncio.gather(tasks.pop(i), return_exceptions=True)
                            log.info('Kanal %s beendet: %s', i, result)
                    for i in active - tasks.keys():
                        tasks[i] = asyncio.create_task(encode(browser, i))
                    if not browser.is_connected():
                        raise RuntimeError('Chromium getrennt; Container-Neustart erforderlich')
                except httpx.HTTPError:
                    log.warning('Backend nicht erreichbar; erneuter Versuch in 5 Sekunden')
                try:
                    await asyncio.wait_for(stop.wait(), 5)
                except TimeoutError:
                    pass
        finally:
            for task in tasks.values():
                task.cancel()
            await asyncio.gather(*tasks.values(), return_exceptions=True)
            await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
