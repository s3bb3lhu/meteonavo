import asyncio,math,json
import pytest
from test_api import studio,AUTH,config
from app.regional import tomtom_boxes,tomtom_fetch


def test_opacity_and_logo_preferences_are_channel_specific(studio):
    client,m=studio;before=m.get_channel(2)
    patch=dict(frame_top_opacity=0,frame_middle_opacity=100,logo_mode='free',logo_width=150,logo_x=35.5,logo_y=60,logo_opacity=80)
    response=client.patch('/api/channels/1',headers=AUTH,json=patch)
    assert response.status_code==200 and all(m.get_channel(1)[key]==value for key,value in patch.items())
    for invalid in [dict(frame_top_opacity=-1),dict(frame_middle_opacity=101),dict(logo_mode='bad'),dict(logo_width=251),dict(logo_x=101),dict(logo_version='../secret')]:
        assert client.patch('/api/channels/1',headers=AUTH,json=invalid).status_code==422
    assert m.get_channel(2)==before
    assert client.patch('/api/channels/1',headers=AUTH,json=dict(frame_top_opacity=None)).json()['frame_top_opacity'] is None


def test_logo_upload_auth_validation_and_delete(studio):
    client,m=studio
    assert client.post('/api/logo/1',content=b'hello',headers={'Content-Type':'image/png'}).status_code==401
    assert client.post('/api/logo/1',content=b'<svg/>',headers={**AUTH,'Content-Type':'image/svg+xml'}).status_code==422
    assert client.post('/api/logo/1',content=b'bad image',headers={**AUTH,'Content-Type':'image/png'}).status_code==422
    assert client.get('/api/logo/1/image').status_code==404
    folder=m.DATA/'logos';version='a'*16;(folder/f'channel-1-{version}.png').write_bytes(b'png')
    client.patch('/api/channels/1',headers=AUTH,json=dict(logo_version=version,logo_mode='location'))
    assert client.get('/api/logo/1/image?v='+version).headers['content-type']=='image/png'
    assert client.delete('/api/logo/1',headers=AUTH).status_code==200
    assert m.get_channel(1)['logo_version']=='' and m.get_channel(1)['logo_mode']=='off'
    assert not list(folder.glob('channel-1-*.png'))


def test_tomtom_splits_large_area_and_deduplicates(monkeypatch):
    from app import regional
    calls=[]
    class Result:
        status_code=200
        def json(self):return {'incidents':[{'geometry':{'type':'Point','coordinates':[8,50]},'properties':{'id':'same','from':'A','to':'B','events':[{'description':'Baustelle'}]}}]}
    class Client:
        def __init__(self,*a,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def get(self,url,params):
            calls.append(params);return Result()
    monkeypatch.setattr(regional.httpx,'AsyncClient',Client)
    data=asyncio.run(tomtom_fetch('test-key',50,8,100))
    assert data['status']=='ok' and len(data['items'])==1 and len(calls)==9
    for params in calls:
        west,south,east,north=map(float,params['bbox'].split(','))
        area=(east-west)*111.32*math.cos(math.radians(south))*(north-south)*111.32
        assert area<10000
    assert len(tomtom_boxes(38.64,.02,10))==1


def test_tomtom_test_uses_saved_or_unsaved_key_without_exposing_it(studio,monkeypatch):
    client,m=studio
    from app import regional
    client.put('/api/channels/1',headers=AUTH,json=config())
    client.put('/api/regional/settings',headers=AUTH,json={'key':'saved-key'})
    seen=[]
    async def fetch(key,*args):
        seen.append(key)
        return dict(items=[],status='ok')
    monkeypatch.setattr(regional,'tomtom_fetch',fetch)
    assert client.post('/api/regional/test',json={}).status_code==401
    r=client.post('/api/regional/test',headers=AUTH,json={'channel_id':1})
    assert r.status_code==200 and r.json()['ok'] and 'saved-key' not in r.text
    r=client.post('/api/regional/test',headers=AUTH,json={'channel_id':1,'key':'unsaved-key'})
    assert r.json()['ok'] and seen==['saved-key','unsaved-key']
    with m.db() as connection:assert connection.execute('SELECT value FROM regional_settings WHERE key="tomtom"').fetchone()[0]=='saved-key'
    async def failed(*args):raise regional.HTTPException(403,regional.traffic_error(403))
    monkeypatch.setattr(regional,'tomtom_fetch',failed)
    assert client.post('/api/regional/test',headers=AUTH,json={'channel_id':1}).json()['upstream_status']==403


def test_tomtom_empty_results_are_cached_and_failures_stale(studio,monkeypatch):
    client,m=studio
    from app import regional
    client.put('/api/channels/1',headers=AUTH,json=config())
    client.put('/api/regional/settings',headers=AUTH,json={'key':'valid-key'})
    calls=[]
    async def fetch(*args):calls.append(1);return dict(items=[],status='ok',message='Keine Ereignisse')
    monkeypatch.setattr(regional,'tomtom_fetch',fetch)
    assert client.get('/api/traffic/1').json()['status']=='ok'
    assert client.get('/api/traffic/1').json()['status']=='ok' and len(calls)==1
    with m.db() as connection:connection.execute('UPDATE regional_cache SET stamp=stamp-400 WHERE key LIKE "tomtom:v3:%"')
    async def failed(*args):raise regional.HTTPException(429,regional.traffic_error(429))
    monkeypatch.setattr(regional,'tomtom_fetch',failed)
    assert client.get('/api/traffic/1').json()['status']=='stale'
