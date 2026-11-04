import asyncio
from pathlib import Path
import pytest
from test_api import studio,AUTH,config
from app.outputs import ts_segments,ts_data,continuous_ts


def packet(value):
    return bytes([0x47,value])+bytes(186)


def test_real_ts_routes_and_formats(studio,monkeypatch):
    client,m=studio
    client.put('/api/outputs',headers=AUTH,json=dict(username='viewer',password='Test!pass9'))
    client.put('/api/channels/1',headers=AUTH,json=config())
    folder=m.HLS/'1';folder.mkdir()
    for n in range(1,5):(folder/f'seg_{n}.ts').write_bytes(packet(n))
    (folder/'index.m3u8').write_text('#EXTM3U\n'+''.join(f'#EXTINF:2,\nseg_{n}.ts\n' for n in range(1,5)))
    for suffix in ['1.ts','1']:
        calls=[]
        def ready(i):
            calls.append(i)
            return len(calls)==1
        monkeypatch.setattr(m,'stream_ready',ready)
        r=client.get('/live/viewer/Test!pass9/'+suffix)
        assert r.status_code==200 and r.headers['content-type']=='video/mp2t'
        assert r.content==packet(2)+packet(3)+packet(4),'TS must contain video packets, never an HLS manifest'
        assert r.headers['x-accel-buffering']=='no'
    monkeypatch.setattr(m,'stream_ready',lambda i:True)
    assert client.head('/live/viewer/Test!pass9/1.ts').status_code==200
    assert client.head('/live/viewer/Test!pass9/1.m3u8').headers['content-type'].startswith('application/vnd.apple.mpegurl')
    assert client.get('/live/viewer/wrong/1.ts').status_code==401
    assert client.get('/live/viewer/Test!pass9/2.ts').status_code==404
    (folder/'seg_4.ts').write_text('#EXTM3U')
    assert client.get('/live/viewer/Test!pass9/1.ts').status_code==503
    monkeypatch.setattr(m,'stream_ready',lambda i:False)
    assert client.get('/live/viewer/Test!pass9/1.ts').status_code==503


def test_ts_follows_new_segments_once_and_stops_at_gap(tmp_path):
    class Connected:
        async def is_disconnected(self):return False
    async def check():
        (tmp_path/'index.m3u8').write_text('#EXTM3U\nseg_11.ts\n')
        (tmp_path/'seg_11.ts').write_bytes(packet(11))
        stream=continuous_ts(Connected(),tmp_path,[(10,packet(10))],lambda:True,lambda:True)
        assert await anext(stream)==packet(10)
        assert await anext(stream)==packet(11)
        (tmp_path/'seg_12.ts').write_bytes(packet(12))
        (tmp_path/'index.m3u8').write_text('#EXTM3U\nseg_11.ts\nseg_12.ts\n')
        assert await anext(stream)==packet(12)
        (tmp_path/'seg_14.ts').write_bytes(packet(14))
        (tmp_path/'index.m3u8').write_text('#EXTM3U\nseg_14.ts\n')
        with pytest.raises(StopAsyncIteration):await anext(stream)
    asyncio.run(check())


def test_ts_rejects_path_traversal_and_invalid_transport_data(tmp_path):
    (tmp_path/'index.m3u8').write_text('#EXTM3U\n../../private.ts\nseg_1.ts\n')
    assert ts_segments(tmp_path)==[(1,tmp_path/'seg_1.ts')]
    (tmp_path/'seg_1.ts').write_bytes(bytes(188))
    with pytest.raises(ValueError):ts_data(tmp_path/'seg_1.ts')
