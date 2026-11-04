import json
import time
import pytest
from app import cameras
from test_api import studio,AUTH,config


def test_public_snapshot_has_bounded_fixed_urls_and_capture_time(monkeypatch):
    stamp=int(time.time())-60;calls=[]
    def fetch(url,limit):
        calls.append((url,limit))
        if '/query?' in url:return f'([{{"timestamp":"{stamp}"}}])'.encode(),{},url
        return b'\xff\xd8\xffjpeg',{'Content-Type':'image/jpeg'},url
    monkeypatch.setattr(cameras,'fetch',fetch)
    body,headers,_=cameras.mainhattan_snapshot()
    assert body.startswith(b'\xff\xd8\xff') and headers['x-camera-captured-at']==str(stamp)
    assert calls==[
        ('https://www.mainhattan-webcam.de/query?job=dzi&id=live&minsize=100',65536),
        (f'https://www.mainhattan-webcam.de/thumbs/1280/{stamp}.JPG',2*1024*1024)]


@pytest.mark.parametrize('payload',[b'alert(1)',b'callback([{"timestamp":"1793817601"}])',b'{}',b'[]',b'[{"timestamp":true}]',b'[{"timestamp":"../private"}]'])
def test_snapshot_metadata_is_data_never_javascript_or_a_path(payload):
    with pytest.raises(ValueError):cameras.mainhattan_timestamp(payload)


def test_snapshot_rejects_future_or_expired_time():
    for stamp in [1800000000+301,1800000000-7*86400-1]:
        with pytest.raises(ValueError):cameras.mainhattan_timestamp(json.dumps([{'timestamp':stamp}]).encode(),now=1800000000)


def test_existing_mainhattan_selection_uses_image_without_loading_cmp(studio,monkeypatch):
    client,m=studio;stamp=int(time.time())-60
    monkeypatch.setattr(cameras,'open_public',lambda url:(_ for _ in ()).throw(ValueError('unused provider check')))
    client.put('/api/channels/1',headers=AUTH,json={**config(),'latitude':50.13,'longitude':8.92})
    client.put('/api/cameras/1/settings',headers=AUTH,json={'disabled_presets':[x['id'] for x in cameras.PRESETS if x['id']!='frankfurt-mainhattan']})
    monkeypatch.setattr(cameras,'mainhattan_snapshot',lambda:(b'\xff\xd8\xffimage',{'last-modified':'Wed, 04 Nov 2026 18:00:00 GMT','x-camera-captured-at':str(stamp)},''))
    response=client.get('/api/cameras/1/frankfurt-mainhattan/media')
    assert response.status_code==200 and response.headers['x-camera-captured-at']==str(stamp)
    assert response.headers['content-type']=='image/jpeg'
    assert next(x for x in cameras.PRESETS if x['id']=='frankfurt-mainhattan')['kind']=='image'
