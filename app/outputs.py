"""HTTP live-only Xtream-compatible output and individual channel playlists."""
import asyncio
import re
import json
import os
import secrets
import time
from urllib.parse import urlsplit, quote
from pathlib import Path
from fastapi import Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse, Response
from pydantic import BaseModel, Field
from .accounts import hash_password, verify_password, password_errors, validate_username


class OutputCredentials(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    enabled: bool = True


def ts_segments(folder):
    """Read only complete, locally generated HLS transport stream segments."""
    text=(folder/'index.m3u8').read_text()
    if not text.startswith('#EXTM3U'):raise ValueError('Ungültige HLS-Playlist')
    result=[]
    for line in text.splitlines():
        match=re.fullmatch(r'seg_(\d+)\.ts',line.strip())
        if match:result.append((int(match[1]),folder/line.strip()))
    return sorted(result)


def ts_data(path):
    data=path.read_bytes()
    if not data or len(data)%188 or any(data[i]!=0x47 for i in range(0,len(data),188)):
        raise ValueError('Ungültiges MPEG-TS-Segment')
    return data


async def continuous_ts(request,folder,initial,ready,enabled):
    # Reuse encoder output. No per-viewer browser, FFmpeg, or video encoding.
    last=-1;last_new=time.monotonic()
    for number,data in initial:
        if await request.is_disconnected():return
        last=number
        yield data
    while not await request.is_disconnected():
        if not ready() or not enabled() or time.monotonic()-last_new>20:return
        try:
            segments=ts_segments(folder)
            if segments and segments[-1][0]<last:return  # encoder sequence reset
            pending=[(n,path) for n,path in segments if n>last]
            for number,path in pending:
                if number!=last+1:return  # reconnect cleanly after dropped segments/restart
                data=await asyncio.to_thread(ts_data,path)
                last=number;last_new=time.monotonic()
                yield data
        except (OSError,ValueError):return
        await asyncio.sleep(.25)


def install(m):
    @m.app.middleware('http')
    async def output_headers(request,call_next):
        response=await call_next(request)
        if request.url.path in ('/get.php','/player_api.php','/xmltv.php') or request.url.path.startswith('/live/'):
            response.headers['Cache-Control']='no-store'
            response.headers['Referrer-Policy']='no-referrer'
        return response
    def init():
        with m.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS output_access (id INTEGER PRIMARY KEY, username TEXT, password_hash TEXT, enabled INTEGER)')
            c.execute('CREATE TABLE IF NOT EXISTS output_attempts (ip TEXT PRIMARY KEY, stamp REAL, count INTEGER)')

    def base(request):
        p = urlsplit(os.getenv('OUTPUT_BASE_URL') or os.getenv('PUBLIC_BASE_URL') or str(request.base_url))
        return 'http://' + p.netloc

    def check(request, username, password):
        init()
        ip = request.client.host if request.client else 'unknown'
        now = time.time()
        with m.db() as c:
            attempt = c.execute('SELECT stamp,count FROM output_attempts WHERE ip=?', (ip,)).fetchone()
            if attempt and now-attempt[0]<60 and attempt[1]>=10:
                raise HTTPException(429, 'Zu viele Anmeldeversuche')
            row = c.execute('SELECT username,password_hash,enabled FROM output_access WHERE id=1').fetchone()
            valid = bool(row and row[2] and secrets.compare_digest(username.encode(), row[0].encode()) and verify_password(password, row[1]))
            if not valid:
                count = attempt[1]+1 if attempt and now-attempt[0]<60 else 1
                c.execute('INSERT OR REPLACE INTO output_attempts VALUES (?,?,?)', (ip, now if not attempt or now-attempt[0]>=60 else attempt[0], count))
                c.execute('DELETE FROM output_attempts WHERE stamp<?', (now-3600,))
            else:c.execute('DELETE FROM output_attempts WHERE ip=?', (ip,))
        if not valid:raise HTTPException(401, 'Xtream-Zugang ungültig oder deaktiviert')

    def entries(request, ids, username=None, password=None, output="m3u8"):
        lines = ['#EXTM3U']
        for i in ids:
            ch = m.get_channel(i)
            if not ch['enabled']:continue
            url = f'{base(request)}/live/{i}/index.m3u8'
            if username is not None:url = f'{base(request)}/live/{quote(username,safe="")}/{quote(password,safe="")}/{i}.{output}'
            lines += [f'#EXTINF:-1 tvg-id="weather-{i}" tvg-chno="{i}" group-title="Wetter",{ch["name"]}', url]
        return PlainTextResponse('\n'.join(lines)+'\n', media_type='audio/x-mpegurl', headers={'Cache-Control':'no-store'})

    @m.app.get('/playlist/{i}.m3u')
    def channel_playlist(i:int, request:Request):
        m.get_channel(i)
        return entries(request, [i])

    @m.app.get('/api/outputs', dependencies=[Depends(m.auth)])
    def output_status(request:Request):
        init()
        with m.db() as c:row=c.execute('SELECT username,enabled FROM output_access WHERE id=1').fetchone()
        return dict(username=row[0] if row else '', enabled=bool(row and row[1]), server=base(request), protocol='http', formats=['ts','m3u8'], live_only=True)

    @m.app.put('/api/outputs', dependencies=[Depends(m.auth)])
    def configure(body:OutputCredentials):
        init();name=validate_username(body.username)
        errors=password_errors(body.password)
        if errors:raise HTTPException(422, ', '.join(errors))
        if '/' in body.password or '\\' in body.password:raise HTTPException(422,'Xtream-Passwort ohne Schrägstriche wählen')
        with m.db() as c:c.execute('INSERT OR REPLACE INTO output_access VALUES (1,?,?,?)',(name,hash_password(body.password),int(body.enabled)))
        return dict(username=name,enabled=body.enabled)

    @m.app.get('/player_api.php')
    def player_api(request:Request, username:str='', password:str='', action:str='', stream_id:int=0):
        check(request,username,password)
        if action=='get_live_categories':return [dict(category_id='1',category_name='Wetter',parent_id=0)]
        if action=='get_live_streams':
            return [dict(num=i,name=m.get_channel(i)['name'],stream_type='live',stream_id=i,stream_icon='',epg_channel_id=f'weather-{i}',added='0',category_id='1',custom_sid='',tv_archive=0,direct_source='',tv_archive_duration=0,container_extension='ts') for i in range(1,6) if m.get_channel(i)['enabled']]
        if action in ('get_short_epg','get_simple_data_table'):return dict(epg_listings=[])
        if action in ('get_vod_streams','get_vod_categories','get_series','get_series_categories'):return []
        if action=='get_live_info':return dict(info={},movie_data={})
        if action:raise HTTPException(400,'Nur Live-Streams werden unterstützt')
        p=urlsplit(base(request))
        return dict(user_info=dict(username=username,password=password,message='Weather Channel Studio · Live MPEG-TS / HLS',auth=1,status='Active',exp_date=None,is_trial='0',active_cons='0',created_at='0',max_connections='5',allowed_output_formats=['ts','m3u8']),server_info=dict(url=p.hostname,port=str(p.port or 80),https_port='',server_protocol='http',rtmp_port='',timezone='UTC',timestamp_now=int(time.time()),time_now=time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime())))

    @m.app.get('/get.php')
    def xtream_playlist(request:Request, username:str='', password:str='', output:str='m3u8', type:str='m3u_plus'):
        check(request,username,password)
        if output not in ('m3u8','hls','ts','mpegts'):raise HTTPException(422,'Ausgabeformat ts oder m3u8 wählen')
        return entries(request,range(1,6),username,password,'ts' if output in ('ts','mpegts') else 'm3u8')

    @m.app.api_route('/live/{username}/{password}/{stream}',methods=['GET','HEAD'])
    async def xtream_live(request:Request, username:str, password:str, stream:str):
        await asyncio.to_thread(check,request,username,password)
        match=re.fullmatch(r'(\d+)(?:\.(m3u8|ts))?',stream)
        if not match:raise HTTPException(404,'Live-Adresse mit .ts oder .m3u8 verwenden')
        i=int(match[1]);fmt=match[2] or 'ts';ch=m.get_channel(i)
        if not ch['enabled']:raise HTTPException(404)
        if not m.stream_ready(i):raise HTTPException(503,'Stream startet oder offline')
        folder=m.HLS/str(i)
        if fmt=='ts':
            try:
                segments=ts_segments(folder)[-3:]
                initial=[(number,await asyncio.to_thread(ts_data,path)) for number,path in segments]
                if not initial:raise ValueError('Noch keine Segmente')
            except (OSError,ValueError):raise HTTPException(503,'Stream startet oder offline')
            headers={'Cache-Control':'no-store','X-Accel-Buffering':'no','X-Content-Type-Options':'nosniff'}
            if request.method=='HEAD':return Response(media_type='video/mp2t',headers=headers)
            return StreamingResponse(continuous_ts(request,folder,initial,lambda:m.stream_ready(i),lambda:m.get_channel(i)['enabled']),media_type='video/mp2t',headers=headers)
        try:text=(folder/'index.m3u8').read_text()
        except OSError:raise HTTPException(503,'Stream startet oder offline')
        lines=[line if not line or line.startswith('#') else f'{base(request)}/live/{i}/{Path(line).name}' for line in text.splitlines()]
        if request.method=='HEAD':return Response(media_type='application/vnd.apple.mpegurl',headers={'Cache-Control':'no-store'})
        return PlainTextResponse('\n'.join(lines)+'\n',media_type='application/vnd.apple.mpegurl',headers={'Cache-Control':'no-store'})

    @m.app.get('/xmltv.php')
    def epg(request:Request, username:str='', password:str=''):
        check(request,username,password)
        return PlainTextResponse('<?xml version="1.0" encoding="UTF-8"?><tv generator-info-name="Weather Channel Studio"/>',media_type='application/xml')
