"""Run INSIDE the API container after enabling one channel. Real HLS + ffprobe."""
import json
import os
import subprocess
import time
import urllib.request

base = 'http://localhost:8080'
def read(path):
    return urllib.request.urlopen(base + path, timeout=10).read()

channels = json.loads(read('/api/channels'))
active = [c for c in channels if c['enabled']]
assert active, 'Mindestens einen Kanal über die Weboberfläche aktivieren'
playlist = read('/playlist.m3u').decode()
for c in active:
    i = c['id']
    assert f'/live/{i}/index.m3u8' in playlist
    deadline = time.time() + 120
    while True:
        try:
            manifest = read(f'/live/{i}/index.m3u8').decode()
            segments = [line for line in manifest.splitlines() if line.endswith('.ts')]
            assert len(segments) >= 2
            assert len(read(f'/live/{i}/{segments[-2]}')) > 1000
            break
        except Exception:
            if time.time() > deadline:
                raise
            time.sleep(3)
    result = subprocess.check_output(['ffprobe', '-v', 'error', '-read_intervals', '%+3', '-show_streams', '-of', 'json', f'{base}/live/{i}/index.m3u8'], timeout=30)
    streams = json.loads(result)['streams']
    assert any(s['codec_name'] == 'h264' and s['width'] == 1280 and s['height'] == 720 for s in streams)
    assert any(s['codec_name'] == 'aac' for s in streams)
    print(f'Kanal {i}: HLS, Segmente, H.264 720p und AAC OK')
print('Alle aktivierten Kanäle geprüft')
