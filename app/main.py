import asyncio
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import FileResponse, PlainTextResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .news import fetch_feed, validate_url

DATA = Path(os.getenv('DATA_DIR', '/data'))
HLS = Path(os.getenv('HLS_DIR', '/hls'))
STATIC = Path(__file__).parent / 'static'
locks = {i: asyncio.Lock() for i in range(1, 6)}
news_locks = {i: asyncio.Lock() for i in range(1, 6)}


class OverviewPlace(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1,max_length=80)
    latitude: float = Field(ge=-85,le=85)
    longitude: float = Field(ge=-180,le=180)
    country_code: str = Field(pattern=r'^[A-Z]{2}$')


class Channel(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(default='Wetter', min_length=1, max_length=60, pattern=r'^[^\r\n"<>]+$')
    enabled: bool = False
    location: str = Field(default='', max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    color: str = Field(default='#33c9f2', pattern=r'^#[0-9a-fA-F]{6}$')
    background: str = Field(default='#102338', pattern=r'^#[0-9a-fA-F]{6}$')
    pages: list[Literal['current', 'daily', 'hourly', 'wind', 'precipitation', 'radar', 'country', 'traffic', 'webcams']] = Field(default=['current', 'daily', 'hourly', 'wind', 'precipitation', 'radar'], min_length=1, max_length=12)
    seconds: int = Field(default=20, ge=5, le=120)
    rss_url: str = Field(default='', max_length=2048)
    theme: Literal['classic', 'aurora', 'noir', 'solar', 'arctic', 'sky', 'city', 'nature', 'cinematic', 'flow', 'cinema-glass', 'cinema-prime', 'cinema-panorama','metro-red','ocean-blue','forest-green','retro-terminal','retro-sunset','prism-gradient','city-photo','panorama-glass','editorial-light','ruby-broadcast','forest-terrain','retro-broadcast','retro-digital','aurora-gradient','alpine-luxe'] = 'classic'
    motion: bool = True
    frame_style: Literal['design','fine-line','broadcast-edge','contour','retro-chrome','soft-ribbon','corner-brackets'] = 'design'
    frame_custom: bool = False
    frame_color: str = Field(default='#d9ae69', pattern=r'^#[0-9a-fA-F]{6}$')
    frame_width: int = Field(default=2, ge=1, le=8)
    frame_radius: int = Field(default=16, ge=0, le=48)
    frame_opacity: int = Field(default=85, ge=20, le=100)
    frame_top_opacity: int | None = Field(default=None, ge=0, le=100)
    frame_middle_opacity: int | None = Field(default=None, ge=0, le=100)
    logo_mode: Literal['off','location','free'] = 'off'
    logo_version: str = Field(default='', pattern=r'^[a-f0-9]{16}$|^$')
    logo_x: float = Field(default=90, ge=0, le=100)
    logo_y: float = Field(default=5, ge=0, le=100)
    logo_width: int = Field(default=90, ge=30, le=250)
    logo_opacity: int = Field(default=100, ge=0, le=100)
    landscape_mood: Literal['off','auto','dawn','day','rain','dusk','night','snow'] = 'off'
    radar_map_style: Literal['streets','streets-dark','satellite','satellite-night','overview','google-roadmap','google-satellite','google-hybrid','google-terrain'] = 'streets'
    radar_zoom: int = Field(default=6,ge=1,le=7)
    radar_radius_km: int | None = Field(default=None,ge=1,le=5000)
    overview_places: list[OverviewPlace] = Field(default_factory=list,max_length=8)
    traffic_radius_km: int = Field(default=100,ge=1,le=100)
    icon_set: Literal['photographic', 'illustrated'] = 'photographic'
    address: str = Field(default='', max_length=500)
    country_code: str = Field(default='', pattern=r'^[A-Z]{2}$|^$')
    state: str = Field(default='', max_length=100)
    county: str = Field(default='', max_length=150)
    warning_region: str = Field(default='', max_length=150)
    warnings_enabled: bool = True
    audio_mode: Literal['off', 'playlist', 'radio'] = 'off'
    playlist_id: str = Field(default='', pattern=r'^[a-f0-9]{32}$|^$')
    radio_station: str = Field(default='', pattern=r'^[a-fA-F0-9-]{36}$|^$')
    volume: float = Field(default=0.35, ge=0, le=1)

    @field_validator('rss_url')
    @classmethod
    def rss_address(cls, value):
        return validate_url(value.strip())

    @model_validator(mode='after')
    def coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('Beide Koordinaten erforderlich')
        if self.enabled and (self.latitude is None or not self.location.strip()):
            raise ValueError('Aktive Kanäle benötigen Ort und Koordinaten')
        if any(p.country_code != self.country_code for p in self.overview_places):
            raise ValueError('Übersichtsorte müssen zum ausgewählten Land gehören')
        return self


def db():
    return sqlite3.connect(DATA / 'studio.sqlite')


def init_db():
    DATA.mkdir(parents=True, exist_ok=True)
    HLS.mkdir(parents=True, exist_ok=True)
    from .accounts import init_accounts
    init_accounts(db)
    from .catalog import init_catalog
    init_catalog(db)
    with db() as con:
        con.execute('CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY, config TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS weather (id INTEGER PRIMARY KEY, coords TEXT, stamp REAL, payload TEXT)')
        con.execute('CREATE TABLE IF NOT EXISTS news (id INTEGER PRIMARY KEY, url TEXT, stamp REAL, attempt REAL, payload TEXT, failed INTEGER)')
        # Old cache entries predate the astronomical fields needed by scenery.
        for channel_id, payload in con.execute('SELECT id,payload FROM weather').fetchall():
            cached = json.loads(payload)
            if 'is_day' not in cached.get('current', {}) or 'sunrise' not in cached.get('daily', {}):
                con.execute('DELETE FROM weather WHERE id=?', (channel_id,))
        for i in range(1, 6):
            con.execute('INSERT OR IGNORE INTO channels VALUES (?, ?)', (i, Channel(name=f'Wetter {i}').model_dump_json()))


def get_channel(i):
    if i not in range(1, 6):
        raise HTTPException(404, 'Kanal nicht vorhanden')
    with db() as con:
        row = con.execute('SELECT config FROM channels WHERE id=?', (i,)).fetchone()
    return Channel.model_validate_json(row[0]).model_dump()


def auth(request: Request):
    from .accounts import authenticate
    return authenticate(db,request)


async def weather(i):
    async with locks[i]:
        c = get_channel(i)
        if c['latitude'] is None:
            raise HTTPException(409, 'Noch kein Ort konfiguriert')
        coords = json.dumps([c['latitude'], c['longitude']])
        with db() as con:
            cached = con.execute('SELECT stamp,payload FROM weather WHERE id=? AND coords=?', (i, coords)).fetchone()
        now = time.time()
        if cached and now - cached[0] < 600:
            return dict(data=json.loads(cached[1]), fetched_at=cached[0], stale=False)
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get('https://api.open-meteo.com/v1/forecast', params={
                    'latitude': c['latitude'], 'longitude': c['longitude'], 'timezone': 'auto',
                    'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,is_day',
                    'hourly': 'temperature_2m,precipitation_probability,rain,snowfall,wind_speed_10m',
                    'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset',
                    'forecast_days': 7})
                r.raise_for_status()
                payload = r.json()
                for key in ('current', 'daily', 'hourly'):
                    if key not in payload:
                        raise ValueError('Unvollständige Wetterantwort')
            with db() as con:
                con.execute('INSERT OR REPLACE INTO weather VALUES (?,?,?,?)', (i, coords, now, json.dumps(payload)))
            return dict(data=payload, fetched_at=now, stale=False)
        except (httpx.HTTPError, ValueError):
            if cached:
                return dict(data=json.loads(cached[1]), fetched_at=cached[0], stale=True)
            raise HTTPException(503, 'Wetterdaten derzeit nicht verfügbar')


async def news(i):
    async with news_locks[i]:
        c = get_channel(i)
        url = c['rss_url']
        if not url:
            return dict(enabled=False, source='', headlines=[], stale=False, fetched_at=None, message='')
        with db() as con:
            cached = con.execute('SELECT stamp,attempt,payload,failed FROM news WHERE id=? AND url=?', (i, url)).fetchone()
        now = time.time()
        if cached and now - cached[1] < 300:
            stamp, _, payload, failed = cached
        else:
            try:
                payload = json.dumps(await asyncio.to_thread(fetch_feed, url))
                stamp, failed = now, 0
            except Exception:
                # Do not expose URLs, network details or parser errors on television.
                stamp, payload, failed = (cached[0], cached[2], 1) if cached else (None, '{}', 1)
            with db() as con:
                con.execute('INSERT OR REPLACE INTO news VALUES (?,?,?,?,?,?)', (i, url, stamp, now, payload, failed))
        data = json.loads(payload)
        headlines = data.get('headlines', []) if stamp and now - stamp < 86400 else []
        return dict(enabled=True, source=data.get('source', 'Nachrichten'), headlines=headlines,
                    stale=bool(failed or not stamp or now - stamp > 900), fetched_at=stamp,
                    message='RSS-Quelle derzeit nicht erreichbar oder ungültig' if failed else '')


async def refresh():
    while True:
        for i in range(1, 6):
            if get_channel(i)['enabled']:
                try:
                    await weather(i)
                except HTTPException:
                    pass
                await news(i)
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app):
    init_db()
    from .catalog import catalogue_loop
    task = asyncio.create_task(refresh())
    radio_task = asyncio.create_task(catalogue_loop(db))
    regional_task = asyncio.create_task(regional_loop())
    camera_task = asyncio.create_task(cameras_loop())
    yield
    camera_task.cancel()
    await asyncio.gather(camera_task,return_exceptions=True)
    regional_task.cancel()
    await asyncio.gather(regional_task,return_exceptions=True)
    await regional_shutdown()
    radio_task.cancel()
    await asyncio.gather(radio_task, return_exceptions=True)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title='METEONOVA v0.3', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=STATIC), name='static')


@app.get('/health')
def health():
    with db() as con:
        con.execute('SELECT 1')
    return {'ok': True}


@app.get('/')
def admin(request:Request):
    from .accounts import configured
    if not configured(db):return RedirectResponse('/setup',status_code=303)
    return FileResponse(STATIC / 'dashboard.html',headers={'Cache-Control':'no-store'})


@app.get('/view/{i}')
def view(i: int):
    get_channel(i)
    return FileResponse(STATIC / 'view.html', headers={'Cache-Control': 'no-store'})


@app.get('/api/channels')
def channels(request: Request):
    try:
        auth(request);privileged=True
    except HTTPException:privileged=False
    result=[dict(id=i, **get_channel(i)) for i in range(1,6)]
    if not privileged:
        for channel in result:
            for field in ['address','county','warning_region']:channel[field]=''
    return result


@app.put('/api/channels/{i}', dependencies=[Depends(auth)])
async def save(i: int, channel: Channel):
    old = get_channel(i)
    from .regions import COUNTRIES
    if channel.country_code and channel.country_code not in COUNTRIES:raise HTTPException(422,'Unbekanntes europäisches Land')
    if 'validate_audio_config' in globals():validate_audio_config(channel)
    async with locks[i]:
        with db() as con:
            con.execute('UPDATE channels SET config=? WHERE id=?', (channel.model_dump_json(), i))
            if (old['latitude'], old['longitude']) != (channel.latitude, channel.longitude):
                con.execute('DELETE FROM weather WHERE id=?', (i,))
    async with news_locks[i]:
        with db() as con:
            if old['rss_url'] != channel.rss_url:
                con.execute('DELETE FROM news WHERE id=?', (i,))
    return dict(id=i, **channel.model_dump())


@app.get('/api/locations', dependencies=[Depends(auth)])
async def locations(q: str = ''):
    if not 2 <= len(q.strip()) <= 100:
        raise HTTPException(422, 'Suchtext: 2–100 Zeichen')
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get('https://geocoding-api.open-meteo.com/v1/search', params={'name': q, 'count': 8, 'language': 'de'})
            r.raise_for_status()
            return r.json().get('results', [])
    except httpx.HTTPError:
        raise HTTPException(503, 'Ortssuche nicht verfügbar; Koordinaten manuell eingeben')


@app.get('/api/weather/{i}')
async def get_weather(i: int):
    get_channel(i)
    return await weather(i)


@app.get('/api/warnings/{i}')
async def get_warnings(i:int):
    from .warnings import channel_warnings
    return await channel_warnings(db,get_channel(i))


@app.get('/api/news/{i}')
async def get_news(i: int):
    get_channel(i)
    return await news(i)


@app.get('/playlist.m3u')
def playlist(request:Request):
    base = (os.getenv('OUTPUT_BASE_URL', '') or os.getenv('PUBLIC_BASE_URL', '') or str(request.base_url)).rstrip('/')
    lines = ['#EXTM3U']
    for i in range(1, 6):
        c = get_channel(i)
        if c['enabled']:
            lines += [f'#EXTINF:-1 tvg-id="weather-{i}" tvg-chno="{i}" group-title="Wetter",{c["name"]}', f'{base}/live/{i}/index.m3u8']
    return PlainTextResponse('\n'.join(lines) + '\n', media_type='audio/x-mpegurl', headers={'Cache-Control': 'no-store'})


@app.get('/api/streams')
def streams():
    return [dict(id=i, enabled=get_channel(i)['enabled'], ready=get_channel(i)['enabled'] and stream_ready(i)) for i in range(1, 6)]


def stream_ready(i):
    try:
        return time.time() - (HLS / str(i) / 'index.m3u8').stat().st_mtime < 30
    except FileNotFoundError:
        return False


@app.get('/live/{i}/{filename}')
def live(i: int, filename: str):
    c = get_channel(i)
    if not c['enabled'] or not re.fullmatch(r'(index\.m3u8|seg_\d+\.ts)', filename):
        raise HTTPException(404)
    path = HLS / str(i) / filename
    if not path.is_file() or not stream_ready(i):
        raise HTTPException(503, 'Stream startet oder Renderer offline')
    return FileResponse(path, media_type='application/vnd.apple.mpegurl' if filename.endswith('m3u8') else 'video/mp2t', headers={'Cache-Control': 'no-store'})

# Settings routers share the existing database, authentication and channel locks.
import sys
from .management import install
install(sys.modules[__name__])

from .accounts import install as install_accounts
install_accounts(sys.modules[__name__])

from .radar import install as install_radar
install_radar(sys.modules[__name__])
from .google_maps import install as install_google_maps
install_google_maps(sys.modules[__name__])

@app.get('/watch/{i}')
def watch(i:int):
    get_channel(i)
    return FileResponse(STATIC/'watch.html',headers={'Cache-Control':'no-store'})

@app.get('/assets/hls.js')
def player_library():
    return FileResponse(STATIC/'vendor'/'hls-1.7.4.light.min.js.gz',media_type='application/javascript',headers={'Content-Encoding':'gzip','Cache-Control':'public, max-age=604800'})

from .system_info import install as install_system_info
install_system_info(sys.modules[__name__])

from .outputs import install as install_outputs
install_outputs(sys.modules[__name__])
from .regional import install as install_regional
install_regional(sys.modules[__name__])
from .place_photos import install as install_place_photos
install_place_photos(sys.modules[__name__])

from .cameras import install as install_cameras
install_cameras(sys.modules[__name__])

from .logos import install as install_logos
install_logos(sys.modules[__name__])

from .admin_ui import install as install_admin_ui
install_admin_ui(sys.modules[__name__])
