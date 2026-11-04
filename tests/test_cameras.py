import io
import time
import pytest
from test_api import studio,AUTH,config
from app import cameras


class Connection:
    def close(self):pass

class CameraResponse:
    def __init__(self,data=b'\xff\xd8\xffcamera',headers=None):self.data=io.BytesIO(data);self.headers=headers or [('Content-Type','image/jpeg')]
    def read(self,n):return self.data.read(n)
    def getheaders(self):return self.headers


def fake_public(url):return Connection(),CameraResponse(),url


def body(**extra):return dict(name='Regionalkamera',kind='image',media_url='https://camera.example/image.jpg',source='Testkamera',latitude=51.34,longitude=12.37,**extra)


def test_camera_sources_require_auth_and_stay_in_radius(studio,monkeypatch):
    client,m=studio;monkeypatch.setattr(cameras,'open_public',fake_public)
    client.put('/api/channels/1',headers=AUTH,json=config())
    assert client.post('/api/cameras/1/settings',json=body()).status_code==401
    assert client.post('/api/cameras/1/settings',headers=AUTH,json={**body(),'latitude':48}).status_code==422
    for url in ['http://127.0.0.1/image.jpg','file:///tmp/private','http://user:pass@camera.example/image.jpg']:
        assert client.post('/api/cameras/1/settings',headers=AUTH,json={**body(),'media_url':url}).status_code==422
    r=client.post('/api/cameras/1/settings',headers=AUTH,json=body());assert r.status_code==200
    cid=r.json()['id'];data=client.get('/api/cameras/1').json();assert len(data['items'])==1 and data['items'][0]['kind']=='image'
    assert data['items'][0]['media']==f'/api/cameras/1/{cid}/media'
    assert client.delete(f'/api/cameras/2/settings/{cid}',headers=AUTH).status_code==200
    assert len(client.get('/api/cameras/1/settings',headers=AUTH).json()['items'])==1
    client.patch('/api/channels/1',headers=AUTH,json=dict(latitude=40))
    assert client.get('/api/cameras/1').json()['items']==[]


def test_image_cache_and_failure_do_not_return_an_old_frame(studio,monkeypatch):
    client,m=studio;calls=[]
    def upstream(url):calls.append(url);return fake_public(url)
    monkeypatch.setattr(cameras,'open_public',upstream)
    client.put('/api/channels/1',headers=AUTH,json=config())
    cid=client.post('/api/cameras/1/settings',headers=AUTH,json=body()).json()['id']
    url=f'/api/cameras/1/{cid}/media';a=client.get(url);b=client.get(url)
    assert a.status_code==200 and a.content==b.content and a.headers['cache-control']=='no-store'
    assert len(calls)==2,'One validation and one shared image fetch'
    real_time=time.time
    monkeypatch.setattr(cameras.time,'time',lambda:real_time()+31)
    def offline(url):raise ValueError('offline')
    monkeypatch.setattr(cameras,'open_public',offline)
    failed=client.get(url)
    assert failed.status_code==502 and b'\xff\xd8\xffcamera' not in failed.content
    assert client.get(url+'?asset=arbitrary').status_code==404
    client.delete('/api/cameras/1/settings/'+cid,headers=AUTH)
    assert client.get(url).status_code==404


def test_frame_restrictions_are_respected(studio,monkeypatch):
    client,m=studio
    def blocked(url):return Connection(),CameraResponse(headers=[('X-Frame-Options','SAMEORIGIN')]),url
    monkeypatch.setattr(cameras,'open_public',blocked)
    client.put('/api/channels/1',headers=AUTH,json={**config(),'latitude':50.13,'longitude':8.92})
    data=client.get('/api/cameras/1').json();assert data['items'] and not any(x['available'] for x in data['items'] if x['kind']=='iframe')
    assert 'blockiert' in data['items'][0]['message']


def test_camera_rotation_and_regional_preset_selection_persist(studio,monkeypatch):
    client,m=studio;monkeypatch.setattr(cameras,'open_public',fake_public)
    client.put('/api/channels/1',headers=AUTH,json={**config(),'latitude':50.13,'longitude':8.92})
    assert 'frankfurt-goetheturm' in [x['id'] for x in client.get('/api/cameras/1').json()['items']]
    assert client.put('/api/cameras/1/settings',headers=AUTH,json=dict(rotation_seconds=10)).status_code==422
    assert client.put('/api/cameras/1/settings',headers=AUTH,json=dict(rotation_seconds=120,disabled_presets=[x['id'] for x in client.get('/api/cameras/1').json()['items']])).status_code==200
    assert client.get('/api/cameras/1').json()['items']==[]
    assert client.get('/api/cameras/1/settings',headers=AUTH).json()['rotation_seconds']==120


def test_hls_manifest_rewrites_segments_and_rejects_unissued_assets(studio,monkeypatch):
    client,m=studio
    def upstream(url):
        content=b'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key.bin"\nseg.ts\n' if url.endswith('.m3u8') else b'media'
        return Connection(),CameraResponse(content),url
    monkeypatch.setattr(cameras,'open_public',upstream)
    client.put('/api/channels/1',headers=AUTH,json=config())
    cid=client.post('/api/cameras/1/settings',headers=AUTH,json={**body(),'kind':'hls','media_url':'https://camera.example/index.m3u8'}).json()['id']
    r=client.get(f'/api/cameras/1/{cid}/media');assert r.status_code==200 and 'https://' not in r.text
    segment=r.text.splitlines()[-1];assert client.get(segment).content==b'media'
    assert client.get(f'/api/cameras/1/{cid}/media?asset=not-issued').status_code==404


def test_oversized_media_response_is_bounded(monkeypatch):
    monkeypatch.setattr(cameras,'open_public',lambda url:(Connection(),CameraResponse(b'x'*101),url))
    with pytest.raises(ValueError):cameras.fetch('https://camera.example/image',100)
