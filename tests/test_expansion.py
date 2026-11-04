import asyncio
import json
import time
from pathlib import Path
from urllib.parse import quote
import pytest
from test_api import studio, AUTH, config
from app.regional import km, in_ring, country_for


def test_individual_playlists_are_http_and_only_include_one_channel(studio,monkeypatch):
    client,m=studio
    monkeypatch.setenv('PUBLIC_BASE_URL','https://example.org:7373')
    client.put('/api/channels/1',headers=AUTH,json=config())
    data=client.get('/playlist/1.m3u').text
    assert 'http://example.org:7373/live/1/index.m3u8' in data
    assert 'https://' not in data and '/live/2/' not in data
    assert client.get('/playlist/2.m3u').text=='#EXTM3U\n'
    assert client.get('/playlist/6.m3u').status_code==404


def test_xtream_authentication_hls_and_empty_epg(studio):
    client,m=studio
    assert client.put('/api/outputs',json=dict(username='viewer',password='Test!pass9')).status_code==401
    assert client.get('/player_api.php').status_code==401
    assert client.put('/api/outputs',headers=AUTH,json=dict(username='viewer',password='Test!pass9')).status_code==200
    client.put('/api/channels/1',headers=AUTH,json=config())
    params=dict(username='viewer',password='Test!pass9')
    data=client.get('/player_api.php',params=params).json()
    assert data['user_info']['auth']==1 and data['server_info']['server_protocol']=='http'
    assert data['user_info']['allowed_output_formats']==['ts','m3u8']
    streams=client.get('/player_api.php',params={**params,'action':'get_live_streams'}).json()
    assert len(streams)==1 and streams[0]['stream_id']==1
    assert '/1.ts' in client.get('/get.php',params={**params,'output':'ts'}).text
    assert streams[0]['container_extension']=='ts'
    assert '/live/viewer/Test%21pass9/1.m3u8' in client.get('/get.php',params=params).text
    folder=m.HLS/'1';folder.mkdir();(folder/'index.m3u8').write_text('#EXTM3U\nseg_1.ts\n')
    r=client.get('/live/viewer/Test!pass9/1.m3u8')
    assert r.status_code==200 and '/live/1/seg_1.ts' in r.text
    assert '<tv ' in client.get('/xmltv.php',params=params).text
    assert 'password' not in client.get('/api/outputs',headers=AUTH).json()
    client.put('/api/outputs',headers=AUTH,json={**params,'enabled':False})
    assert client.get('/player_api.php',params=params).status_code==401


def test_xtream_failed_attempts_are_limited(studio):
    client,m=studio
    for _ in range(10):assert client.get('/player_api.php').status_code==401
    assert client.get('/player_api.php').status_code==429


def test_new_channel_options_persist_and_validate(studio):
    client,m=studio
    data=dict(pages=['webcams','country','traffic','radar'],theme='metro-red',country_code='DE',traffic_radius_km=50,overview_places=[dict(name='Berlin',latitude=52.52,longitude=13.4,country_code='DE')])
    r=client.patch('/api/channels/1',headers=AUTH,json=data)
    assert r.status_code==200 and r.json()['pages']==data['pages']
    assert m.get_channel(1)['overview_places'][0]['name']=='Berlin'
    for invalid in [dict(traffic_radius_km=101),dict(overview_places=[dict(name='Paris',latitude=48.8,longitude=2.3,country_code='FR')])]:
        assert client.patch('/api/channels/1',headers=AUTH,json=invalid).status_code==422


def test_country_shape_and_radius():
    ring=[[0,0],[3,0],[3,3],[0,3],[0,0]]
    assert in_ring(1,1,ring) and not in_ring(4,1,ring)
    assert 110<km(50,8,51,8)<112
    assert country_for(dict(countries=[dict(name='Example',geometry=dict(type='Polygon',coordinates=[ring]))]),1,1)['name']=='Example'


def test_cached_traffic_only_returns_points_within_radius(studio):
    client,m=studio
    client.put('/api/channels/1',headers=AUTH,json=config(country_code='DE',traffic_radius_km=50))
    client.get('/api/regional/settings',headers=AUTH)
    items=[dict(id='near',latitude=51.33,longitude=12.37),dict(id='far',latitude=48.8,longitude=2.3)]
    with m.db() as c:c.execute('INSERT INTO regional_cache VALUES (?,?,?)',('traffic:DE',time.time(),json.dumps(dict(items=items,status='ok',observed_at=time.time()))))
    r=client.get('/api/traffic/1').json()
    assert [x['id'] for x in r['items']]==['near']
    assert 'Autobahn' in r['source']
    client.patch('/api/channels/1',headers=AUTH,json=dict(country_code='ES'))
    assert client.get('/api/traffic/1').json()['status']=='unsupported'


def test_traffic_key_is_private(studio):
    client,m=studio
    assert client.get('/api/regional/settings').status_code==401
    assert client.put('/api/regional/settings',headers=AUTH,json=dict(key='example-key')).status_code==200
    assert client.get('/api/regional/settings',headers=AUTH).json()==dict(tomtom_configured=True)
    assert client.put('/api/regional/settings',headers=AUTH,json=dict(key='')).status_code==200


def test_photo_upload_rejects_unauthorized_and_fake_images(studio):
    client,m=studio
    assert client.post('/api/place-photo/1/upload',content=b'fake',headers={'Content-Type':'image/jpeg'}).status_code==401
    assert client.post('/api/place-photo/1/upload',content=b'fake',headers={**AUTH,'Content-Type':'image/jpeg'}).status_code==422
    assert client.post('/api/place-photo/1/upload?period=invalid',content=b'fake',headers={**AUTH,'Content-Type':'image/jpeg'}).status_code==422
    assert client.get('/api/place-photo/1/uploads',headers=AUTH).json()==[]
    assert client.delete('/api/place-photo/1/upload/evil',headers=AUTH).status_code==422


def test_country_forecast_cached_and_stale_are_explicit(studio,monkeypatch):
    import httpx
    client,m=studio
    place=dict(name='Leipzig',latitude=51.34,longitude=12.37,country_code='DE')
    client.put('/api/channels/1',headers=AUTH,json=config(country_code='DE',overview_places=[place]))
    class Upstream:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,params):return httpx.Response(200,json={'current':{'temperature_2m':12,'weather_code':3,'is_day':1}},request=httpx.Request('GET',url))
    monkeypatch.setattr(m.httpx,'AsyncClient',Upstream)
    data=client.get('/api/country/1').json()
    assert data['places'][0]['current']['temperature_2m']==12 and not data['stale']
    with m.db() as c:c.execute('UPDATE regional_cache SET stamp=? WHERE key LIKE "country:%"',(time.time()-3600,))
    async def failed(*args,**kwargs):raise httpx.ConnectError('offline')
    monkeypatch.setattr(Upstream,'get',failed)
    assert client.get('/api/country/1').json()['stale']
