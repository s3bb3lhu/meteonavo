"""Fail a release if a clean instance contains operator configuration."""
import json
from pathlib import Path
from app import main

main.init_db()
channels = [main.get_channel(i) for i in range(1, 6)]
with main.db() as con:
    assert con.execute('SELECT COUNT(*) FROM owner').fetchone()[0] == 0
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'map_settings' in tables:
        assert not any(json.loads(r[0]).get('key') for r in con.execute('SELECT value FROM map_settings'))
    if 'regional_settings' in tables:
        assert not any(r[0] for r in con.execute('SELECT value FROM regional_settings WHERE key="tomtom"'))
assert len(channels) == 5
assert all(not c['enabled'] and c['latitude'] is None and c['longitude'] is None and not c['rss_url'] and not c['radio_station'] and not c['playlist_id'] and not c['logo_version'] for c in channels)
assert not list(Path('/media').iterdir())
assert not Path('/studio/.env').exists()
print('CLEAN_FIRST_INSTALL_CONFIRMED')
