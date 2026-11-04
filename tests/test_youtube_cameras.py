import json
import pytest
from app.cameras import Camera,youtube_video_id
from test_api import studio,AUTH,config
from app import cameras

VIDEO='M7lc1UVf-VE'

@pytest.mark.parametrize('url',[
 'https://www.youtube.com/watch?v='+VIDEO+'&list=anything',
 'https://youtu.be/'+VIDEO+'?si=sharing',
 'https://www.youtube.com/live/'+VIDEO+'?feature=share',
 'https://www.youtube-nocookie.com/embed/'+VIDEO,
 'https://m.youtube.com/shorts/'+VIDEO,
 'https://www.youtube.com/watch?v='+VIDEO+'#t=10'])
def test_youtube_links_normalize_without_tracking(url):
    assert youtube_video_id(url)==VIDEO
    camera=Camera(name='Kamera',kind='iframe',media_url=url,latitude=51.34,longitude=12.37)
    assert camera.kind=='youtube' and camera.media_url=='https://www.youtube.com/watch?v='+VIDEO

@pytest.mark.parametrize('url',[
 'https://youtube.com.evil.example/watch?v='+VIDEO,
 'https://youtube.com/@channel/live',
 'https://youtube.com/playlist?list=anything',
 'https://youtube.com/watch?v=too-short',
 'https://user:secret@youtube.com/watch?v='+VIDEO,
 'http://127.0.0.1/watch?v='+VIDEO])
def test_invalid_or_non_video_youtube_links_are_rejected(url):
    with pytest.raises(ValueError):Camera(name='Kamera',kind='youtube',media_url=url,latitude=51.34,longitude=12.37)


def test_youtube_save_list_and_delete_use_player_not_proxy(studio,monkeypatch):
    client,m=studio
    def never_fetch(url):raise AssertionError('YouTube must not be scraped or proxied')
    monkeypatch.setattr(cameras,'open_public',never_fetch)
    client.put('/api/channels/1',headers=AUTH,json=config())
    body=dict(name='YouTube Test',kind='youtube',media_url='https://youtu.be/'+VIDEO,latitude=51.34,longitude=12.37)
    assert client.post('/api/cameras/1/settings',json=body).status_code==401
    assert client.post('/api/cameras/1/settings',headers=AUTH,json={**body,'latitude':40}).status_code==422
    saved=client.post('/api/cameras/1/settings',headers=AUTH,json=body)
    assert saved.status_code==200 and saved.json()['kind']=='youtube'
    cid=saved.json()['id'];items=client.get('/api/cameras/1').json()['items'];assert len(items)==1
    assert items[0]['youtube_id']==VIDEO and items[0]['media']=='https://www.youtube-nocookie.com/embed/'+VIDEO
    assert items[0]['playback_checked'] is False
    assert client.get('/api/cameras/1/'+cid+'/media').status_code==404
    assert client.delete('/api/cameras/1/settings/'+cid,headers=AUTH).status_code==200
    assert client.get('/api/cameras/1').json()['items']==[]


def test_legacy_youtube_iframe_is_upgraded_without_rewriting_the_row(studio,monkeypatch):
    client,m=studio
    client.put('/api/channels/1',headers=AUTH,json=config())
    client.get('/api/cameras/1/settings',headers=AUTH)
    payload=json.dumps(dict(name='Alt',kind='iframe',media_url='https://www.youtube.com/watch?v='+VIDEO,latitude=51.34,longitude=12.37,enabled=True,source=''))
    with m.db() as c:c.execute('INSERT INTO webcam_sources VALUES (?,?,?)',('legacy',1,payload))
    result=client.get('/api/cameras/1').json()['items'][0]
    assert result['kind']=='youtube' and result['youtube_id']==VIDEO
    with m.db() as c:assert c.execute('SELECT payload FROM webcam_sources WHERE id="legacy"').fetchone()[0]==payload
