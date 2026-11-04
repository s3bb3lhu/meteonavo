import asyncio
import json
import time
import pytest
from test_api import studio,config,AUTH
from app.regions import COUNTRIES,STATES,german_state
from app.radio_proxy import radio_url,manifest
from app.warnings import parse_feed,channel_warnings

def test_europe_settings_and_partial_channel_updates(studio):
    client,m=studio
    assert len(client.get('/api/regions').json()['countries'])>=50
    assert len(STATES)==16 and german_state('Bavaria')=='Bayern'
    for path in ['/','/settings','/settings/design','/settings/audio']:assert client.get(path).status_code==200
    client.put('/api/channels/1',headers=AUTH,json=config(theme='cinema-prime',rss_url='https://example.com/rss'))
    assert client.patch('/api/channels/1',json={'icon_set':'illustrated'}).status_code==401
    result=client.patch('/api/channels/1',headers=AUTH,json={'icon_set':'illustrated','address':'Markt 1, Leipzig','country_code':'DE'}).json()
    assert result['theme']=='cinema-prime' and result['rss_url']=='https://example.com/rss'
    assert client.get('/api/channels').json()[0]['address']==''
    assert client.get('/api/channels',headers=AUTH).json()[0]['address']=='Markt 1, Leipzig'
    assert result['icon_set']=='illustrated' and m.get_channel(2)['icon_set']=='photographic'
    assert client.patch('/api/channels/1',headers=AUTH,json={'icon_set':'evil'}).status_code==422
    assert client.patch('/api/channels/1',headers=AUTH,json={'country_code':'ZZ'}).status_code==422
    assert client.patch('/api/channels/1',headers=AUTH,json={'audio_mode':'radio','radio_station':'a'*36}).status_code==404

def test_playlist_order_references_and_auth(studio):
    client,m=studio
    assert client.get('/api/music').status_code==401
    assert client.post('/api/music',content=b'bad').status_code==401
    ids=['a'*32,'b'*32]
    with m.db() as c:
        for i in ids:c.execute('INSERT INTO music VALUES (?,?,?,?,?)',(i,i,i+'.m4a',20,100))
    p=client.post('/api/playlists',headers=AUTH,json={'name':'Abend','tracks':ids[::-1]+ids[:1]})
    assert p.status_code==200;p=p.json()
    assert p['tracks']==[ids[1],ids[0],ids[0]]
    assert client.patch('/api/channels/1',headers=AUTH,json={'audio_mode':'playlist','playlist_id':p['id'],'volume':.4}).status_code==200
    audio=client.get('/api/channels/1/audio',headers=AUTH).json()
    assert audio['tracks'][0].endswith(ids[1]+'.m4a') and audio['volume']==.4
    assert client.delete('/api/playlists/'+p['id'],headers=AUTH).status_code==409
    assert client.put('/api/playlists/'+p['id'],headers=AUTH,json={'name':'Abend','tracks':[]}).status_code==409
    assert client.delete('/api/music/'+ids[0],headers=AUTH).status_code==409
    assert client.post('/api/playlists',headers=AUTH,json={'name':'bad','tracks':['missing']}).status_code==422
    assert client.patch('/api/channels/1',headers=AUTH,json={'volume':2}).status_code==422

def test_radio_country_state_pagination_and_m3u(studio):
    client,m=studio
    with m.db() as c:
        for i,state in enumerate(['Hessen','Bayern','Hessen']):
            d=dict(name='Sender '+str(i),countrycode='DE',lastcheckok=1,url_resolved='https://example.com/live',codec='MP3',bitrate=128)
            c.execute('INSERT INTO stations VALUES (?,?,?,?,?)',(str(i),'DE',state,d['name'],json.dumps(d)))
    r=client.get('/api/radio/stations?country=DE&state=Hessen&limit=1&offset=1',headers=AUTH).json()
    assert r['total']==2 and len(r['items'])==1 and r['items'][0]['name']=='Sender 2'
    r=client.get('/api/radio/playlist/DE.m3u?state=Bayern',headers=AUTH)
    assert 'Sender 1' in r.text and 'Sender 0' not in r.text
    assert client.get('/api/radio/stream/0').status_code==401
    assert client.get('/api/radio/stations?country=ZZ',headers=AUTH).status_code==422

@pytest.mark.parametrize('url',['file:///etc/passwd','http://127.0.0.1:9000','http://[::1]/','http://169.254.169.254/','http://10.0.0.1/','http://a:password@example.com/','ftp://example.com/','http://localhost:8080/'])
def test_radio_proxy_blocks_unsafe_urls(url):
    with pytest.raises(ValueError):radio_url(url)

def test_radio_manifest_rewrites_segments_and_keys():
    assert radio_url('https://example.com:8443/radio')[1]==8443
    text=manifest('#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key.bin"\nchunk.ts\n','https://example.com/live/a.m3u8','/api/radio/stream/id?url=')
    assert text.count('/api/radio/stream/id?url=')==2 and 'https%3A%2F%2Fexample.com' in text
    with pytest.raises(ValueError):manifest('#EXTM3U\nhttp://127.0.0.1/seg.ts','https://example.com/','/proxy?url=')

def warning_xml(expires='2099-01-01T00:00:00Z',status='Actual',msg='Alert'):
    return f'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2"><entry><title>Amtliche Frostwarnung</title><cap:areaDesc>Main-Kinzig-Kreis</cap:areaDesc><cap:severity>Severe</cap:severity><cap:status>{status}</cap:status><cap:message_type>{msg}</cap:message_type><cap:expires>{expires}</cap:expires><cap:identifier>test</cap:identifier></entry></feed>'''.encode()

def test_official_warnings_expiry_tests_cancellations_and_exact_regions(studio,monkeypatch):
    client,m=studio
    assert parse_feed(warning_xml())['items'][0]['level']==3
    assert not parse_feed(warning_xml('2000-01-01T00:00:00Z'))['items']
    assert not parse_feed(warning_xml(status='Test'))['items']
    assert not parse_feed(warning_xml(msg='Cancel'))['items']
    from app import warnings
    async def feed(*a):return dict(**parse_feed(warning_xml()),status='ok',message='')
    monkeypatch.setattr(warnings,'country_feed',feed)
    ch={**m.get_channel(1),'country_code':'FR','warning_region':'Main-Kinzig-Kreis'}
    assert len(asyncio.run(channel_warnings(m.db,ch))['items'])==1
    ch.update(warning_region='',county='Main',location='Unrelated')
    result=asyncio.run(channel_warnings(m.db,ch))
    assert not result['items'] and result['status']=='needs_region'
    assert client.get('/api/warnings/6').status_code==404


def test_catalog_imports_beyond_first_thousand_and_keeps_old_data_on_failure(studio,monkeypatch):
    client,m=studio
    from app import catalog
    calls=[]
    async def pages(path,params):
        offset=params['offset'];calls.append(offset)
        return [dict(stationuuid=str(i),countrycode='DE',name='Radio '+str(i),state='Bayern') for i in range(offset,1000 if offset==0 else 1001)]
    monkeypatch.setattr(catalog,'radio_get',pages)
    asyncio.run(catalog.sync_country(m.db,'DE'))
    assert calls==[0,1000]
    with m.db() as c:assert c.execute('SELECT count(*) FROM stations').fetchone()[0]==1001
    async def broken(path,params):
        if params['offset']:raise ValueError('offline')
        return await pages(path,params)
    monkeypatch.setattr(catalog,'radio_get',broken)
    asyncio.run(catalog.sync_country(m.db,'DE'))
    with m.db() as c:
        assert c.execute('SELECT count(*) FROM stations').fetchone()[0]==1001
        assert c.execute('SELECT error FROM catalog_status').fetchone()[0]


def test_gps_only_channel_without_street_address(studio):
    client,m=studio
    response=client.patch('/api/channels/1',headers=AUTH,json=dict(location='Calp',country_code='ES',address='',latitude=38.64,longitude=.02,enabled=True))
    assert response.status_code==200
    saved=m.get_channel(1)
    assert saved['enabled'] and saved['address']=='' and saved['latitude']==38.64
    assert client.patch('/api/channels/1',headers=AUTH,json=dict(latitude=91)).status_code==422
