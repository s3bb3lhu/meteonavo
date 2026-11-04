"""Isolated, synthetic end-to-end Chromium -> FFmpeg -> HLS release smoke test."""
import asyncio
from contextlib import suppress
import json
from pathlib import Path
import time
import httpx
import uvicorn
from playwright.async_api import async_playwright
from app import main, renderer


async def run():
    main.init_db()
    # This test must only run in a disposable container without production volumes.
    assert not any(main.get_channel(i)['enabled'] for i in range(1, 6))
    demo = main.Channel(name='Release Demo', location='Demo', enabled=True,
                        latitude=0, longitude=0, pages=['current'], warnings_enabled=False)
    with main.db() as con:
        con.execute('UPDATE channels SET config=? WHERE id=1', (demo.model_dump_json(),))
    async def synthetic_weather(i):
        return dict(stale=False, fetched_at=time.time(), data=dict(timezone='UTC',
            current=dict(time='2026-01-01T12:00',temperature_2m=12,apparent_temperature=11,
                         weather_code=2,wind_speed_10m=8,wind_direction_10m=90,
                         relative_humidity_2m=60,is_day=1),
            daily=dict(time=['2026-01-01'],weather_code=[2],temperature_2m_max=[14],
                       temperature_2m_min=[6],precipitation_probability_max=[10],
                       sunrise=['2026-01-01T06:00'],sunset=['2026-01-01T18:00']),
            hourly=dict(time=['2026-01-01T12:00'],temperature_2m=[12],rain=[0],snowfall=[0],
                        precipitation_probability=[10],wind_speed_10m=[8])))
    main.weather = synthetic_weather
    renderer.API = 'http://127.0.0.1:8080'
    server = uvicorn.Server(uvicorn.Config(main.app, host='127.0.0.1', port=8080, log_level='error'))
    server_task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:break
        await asyncio.sleep(.1)
    assert server.started
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-dev-shm-usage'])
            task = asyncio.create_task(renderer.encode(browser, 1))
            try:
                playlist = Path('/hls/1/index.m3u8')
                for _ in range(300):
                    if task.done():task.result()
                    if playlist.exists() and playlist.read_text().count('.ts') >= 2:break
                    await asyncio.sleep(.1)
                assert playlist.exists() and playlist.read_text().count('.ts') >= 2
                proc = await asyncio.create_subprocess_exec('ffmpeg','-nostdin','-v','error','-i',str(playlist),'-t','2','-f','null','-',stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.PIPE)
                _, errors = await asyncio.wait_for(proc.communicate(), 20)
                assert proc.returncode == 0, errors.decode(errors='replace')[-500:]
                print('REAL_CHROMIUM_FFMPEG_HLS_DECODE_SUCCESS', flush=True)
            finally:
                task.cancel()
                result = (await asyncio.gather(task, return_exceptions=True))[0]
                assert result is None or isinstance(result, asyncio.CancelledError), type(result).__name__
                await browser.close()
    finally:
        server.should_exit=True
        await asyncio.wait_for(server_task, 30)


if __name__ == '__main__':
    asyncio.run(run())
