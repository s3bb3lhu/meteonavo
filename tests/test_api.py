import importlib
import time

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def studio(tmp_path, monkeypatch):
    monkeypatch.setenv('DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('HLS_DIR', str(tmp_path / 'hls'))
    monkeypatch.setenv('ADMIN_TOKEN', 'test-secret')
    monkeypatch.setenv('PUBLIC_BASE_URL', 'http://server:8080')
    from app import main
    importlib.reload(main)
    with TestClient(main.app) as client:
        yield client, main


def config(**kwargs):
    return dict(name='Leipzig Wetter', location='Leipzig', enabled=True,
                latitude=51.34, longitude=12.37, **kwargs)


AUTH = {'Authorization': 'Bearer test-secret'}


def test_invalid_patch_json_is_validation_error_and_preserves_channel(studio):
    client,main=studio
    before=main.get_channel(1)
    for body in [b'{broken',b'\xff']:
        response=client.patch('/api/channels/1',headers={**AUTH,'Content-Type':'application/json'},content=body)
        assert response.status_code==422
        assert main.get_channel(1)==before


def test_http_playlist_output_is_independent_of_https_administration(studio,monkeypatch):
    client,main=studio
    monkeypatch.setenv('PUBLIC_BASE_URL','https://studio.example:7373')
    monkeypatch.setenv('OUTPUT_BASE_URL','http://iptv.example:7373')
    assert client.put('/api/channels/1',headers=AUTH,json=config()).status_code==200
    assert 'http://iptv.example:7373/live/1/index.m3u8' in client.get('/playlist.m3u').text
    assert client.get('/api/outputs',headers=AUTH).json()['server']=='http://iptv.example:7373'


def test_slots_auth_validation_playlist_persistence(studio):
    client, main = studio
    assert len(client.get('/api/channels').json()) == 5
    assert client.get('/playlist.m3u').text == '#EXTM3U\n'
    assert client.put('/api/channels/1', json=config()).status_code == 401
    for invalid in [config(latitude_bad=12), dict(name='x', enabled=True), config(pages=['fake']), config(color='red'), {**config(), 'latitude': 91}, {**config(), 'name': 'x\n#EXTINF:evil'}]:
        if 'latitude_bad' in invalid:
            invalid = {**config(), 'longitude': None}
        assert client.put('/api/channels/1', headers=AUTH, json=invalid).status_code == 422
    assert client.put('/api/channels/6', headers=AUTH, json=config()).status_code == 404
    assert client.put('/api/channels/1', headers=AUTH, json=config()).status_code == 200
    main.init_db()
    assert main.get_channel(1)['latitude'] == 51.34
    playlist = client.get('/playlist.m3u').text
    assert 'http://server:8080/live/1/index.m3u8' in playlist
    assert 'Leipzig Wetter' in playlist
    assert '/live/2/' not in playlist
    assert client.get('/view/1').status_code == 200
    assert client.get('/view/6').status_code == 404


def test_weather_cache_stale_and_coordinate_invalidation(studio, monkeypatch):
    client, main = studio
    calls = []
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, params):
            calls.append(params)
            return httpx.Response(200, json={'current': {'temperature_2m': 12}, 'daily': {}, 'hourly': {}}, request=httpx.Request('GET', url))
    monkeypatch.setattr(main.httpx, 'AsyncClient', FakeClient)
    client.put('/api/channels/1', headers=AUTH, json=config())
    first = client.get('/api/weather/1')
    assert first.status_code == 200 and not first.json()['stale']
    assert client.get('/api/weather/1').json()['data']['current']['temperature_2m'] == 12
    assert len(calls) == 1
    with main.db() as con:
        con.execute('UPDATE weather SET stamp=?', (time.time()-3600,))
    async def failed(*args, **kwargs): raise httpx.ConnectError('offline')
    monkeypatch.setattr(FakeClient, 'get', failed)
    assert client.get('/api/weather/1').json()['stale']
    client.put('/api/channels/1', headers=AUTH, json={**config(), 'latitude': 50})
    assert client.get('/api/weather/1').status_code == 503
    assert client.get('/api/weather/2').status_code == 409


def test_hls_freshness_and_disable(studio):
    client, main = studio
    client.put('/api/channels/1', headers=AUTH, json=config())
    assert client.get('/live/1/index.m3u8').status_code == 503
    folder = main.HLS / '1'
    folder.mkdir()
    (folder / 'index.m3u8').write_text('#EXTM3U\n')
    (folder / 'seg_123.ts').write_bytes(b'test')
    assert client.get('/live/1/index.m3u8').status_code == 200
    assert client.get('/live/1/seg_123.ts').headers['cache-control'] == 'no-store'
    assert client.get('/api/streams').json()[0]['ready']
    assert client.get('/live/1/config.sqlite').status_code == 404
    client.put('/api/channels/1', headers=AUTH, json={**config(), 'enabled': False})
    assert client.get('/live/1/index.m3u8').status_code == 404
    assert not client.get('/api/streams').json()[0]['ready']
