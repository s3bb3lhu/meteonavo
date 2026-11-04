import asyncio
import struct
import time
import pytest
from fastapi import HTTPException
from test_api import studio,AUTH
from app.radar import parse_metadata,position,HOST

def metadata(now):
    return dict(host=HOST,generated=now,radar=dict(past=[dict(time=now-600,path='/v2/radar/older'),dict(time=now,path='/v2/radar/abcdef123456')],nowcast=[dict(time=now+600,path='/v2/radar/future')]))

def test_metadata_only_real_past_and_trusted_paths():
    now=int(time.time());data=metadata(now)
    assert len(parse_metadata(data)['frames'])==2
    assert all(f['time']<=now for f in parse_metadata(data)['frames'])
    with pytest.raises(ValueError):parse_metadata({**data,'host':'http://127.0.0.1'})
    with pytest.raises(ValueError):parse_metadata(dict(host=HOST,radar={'past':[dict(time=now,path='/../../x')]}))
    with pytest.raises(ValueError):parse_metadata(metadata(now-20000))

def test_coordinate_identity_and_projection_bounds():
    with pytest.raises(HTTPException):position(dict(latitude=None,longitude=None))
    with pytest.raises(HTTPException):position(dict(latitude=90,longitude=0))
    a=position(dict(latitude=38.64,longitude=.02));b=position(dict(latitude=50,longitude=8))
    assert a[2]!=b[2] and position(dict(latitude=0,longitude=0))[0]==0

def test_radar_api_images_and_old_position_rejection(studio,monkeypatch):
    client,m=studio;now=int(time.time())
    assert client.get('/api/radar/1').status_code==409
    assert client.patch('/api/channels/1',headers=AUTH,json=dict(location='Calp',latitude=38.64,longitude=.02,radar_zoom=7)).status_code==200
    cache=m.radar_cache
    cache.state=parse_metadata(metadata(now));cache.stamp=time.time()
    response=client.get('/api/radar/1');assert response.status_code==200
    meta=response.json();assert meta['forecast'] is False and meta['zoom']==7 and len(meta['frames'])==2
    assert 'path' not in meta['frames'][0]
    assert client.get('/api/radar/1/image/'+str(now)+'?zoom=8&position='+meta['position']).status_code==422
    assert client.get('/api/radar/1/image/'+str(now)+'?position=wrong').status_code==409
    calls=[]
    async def download(url,limit):
        calls.append(url)
        return b'\x89PNG\r\n\x1a\n'+bytes(8)+struct.pack('>II',512,512)
    monkeypatch.setattr(cache,'download',download)
    url='/api/radar/1/image/'+str(now)+'?zoom=7&position='+meta['position']
    assert client.get(url).status_code==200 and len(calls)==1
    assert '/512/7/38.640000/0.020000/2/0_0.png' in calls[0]
    assert client.get(url).status_code==200 and len(calls)==1,'Repeat views must use the cached image'
    assert client.get('/api/radar/1/image/1?position='+meta['position']).status_code==404
    client.patch('/api/channels/1',headers=AUTH,json=dict(latitude=50))
    assert client.get(url).status_code==409,'A changed GPS point must never show an old-position cached image'

def test_radar_stale_and_unavailable_are_explicit(studio):
    client,m=studio;now=int(time.time());cache=m.radar_cache
    cache.state=parse_metadata(metadata(now));cache.stamp=time.time()-600;cache.attempt=time.time()
    assert asyncio.run(cache.metadata())['stale']
    cache.stamp=time.time()-3601
    with pytest.raises(HTTPException):asyncio.run(cache.metadata())

def test_local_map_and_browser_player_assets(studio):
    client,m=studio
    response=client.get('/api/radar/geography');assert response.status_code==200 and response.headers['content-encoding']=='gzip'
    assert response.json()['countries'] and response.json()['cities']
    response=client.get('/assets/hls.js');assert response.status_code==200 and 'Hls' in response.text
    assert client.get('/watch/1').status_code==200 and client.get('/watch/6').status_code==404


def test_radar_distance_is_persistent_and_validated(studio):
    client,m=studio
    original=client.get('/api/channels',headers=AUTH).json()[0]
    for value in (1,5,25,50,200,5000):
        r=client.patch('/api/channels/1',headers=AUTH,json={'radar_radius_km':value})
        assert r.status_code==200 and r.json()['radar_radius_km']==value
        assert m.get_channel(1)['radar_radius_km']==value
        assert r.json()['radar_zoom']==original['radar_zoom']
    for value in (0,-1,5001):
        assert client.patch('/api/channels/1',headers=AUTH,json={'radar_radius_km':value}).status_code==422
    assert client.patch('/api/channels/1',headers=AUTH,json={'radar_radius_km':None}).json()['radar_radius_km'] is None


def test_radar_distance_is_persistent_and_validated(studio):
    client,m=studio
    original=client.get('/api/channels',headers=AUTH).json()[0]
    for value in (1,5,25,50,200,5000):
        r=client.patch('/api/channels/1',headers=AUTH,json={'radar_radius_km':value})
        assert r.status_code==200 and r.json()['radar_radius_km']==value
        assert m.get_channel(1)['radar_radius_km']==value
        assert r.json()['radar_zoom']==original['radar_zoom']
    for value in (0,-1,5001):
        assert client.patch('/api/channels/1',headers=AUTH,json={'radar_radius_km':value}).status_code==422
    assert client.patch('/api/channels/1',headers=AUTH,json={'radar_radius_km':None}).json()['radar_radius_km'] is None


def test_map_style_persistence_and_bounded_cached_tiles(studio):
    client,m=studio
    before=m.get_channel(2)
    for style in ['streets','streets-dark','satellite','satellite-night','overview']:
        assert client.patch('/api/channels/1',headers=AUTH,json={'radar_map_style':style}).json()['radar_map_style']==style
    assert client.patch('/api/channels/1',headers=AUTH,json={'radar_map_style':'unknown'}).status_code==422
    assert m.get_channel(2)==before
    folder=m.DATA/'street-cache'
    png=b'\x89PNG\r\n\x1a\n'+bytes(8)+struct.pack('>II',256,256)
    (folder/'streets-3-4-2.tile').write_bytes(png)
    response=client.get('/api/radar/map/streets/3/4/2.png')
    assert response.status_code==200 and response.content==png and '604800' in response.headers['cache-control']
    for path in ['streets/3/8/2','streets/19/1/1','unknown/3/4/2','streets/3/1/-1']:
        assert client.get('/api/radar/map/'+path+'.png').status_code==422
