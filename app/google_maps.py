"""Optional Google browser key. Never proxy or cache Google map tiles."""
import json
from fastapi import Depends, Response
from pydantic import BaseModel, ConfigDict, Field


class GoogleSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    # None preserves the existing key; an explicit empty string removes it.
    key: str | None = Field(default=None, max_length=128, pattern=r'^[A-Za-z0-9_-]*$')
    broadcast_enabled: bool = False


def install(m):
    def read():
        with m.db() as con:
            con.execute('CREATE TABLE IF NOT EXISTS map_settings (id INTEGER PRIMARY KEY, value TEXT NOT NULL)')
            row = con.execute('SELECT value FROM map_settings WHERE id=1').fetchone()
        return json.loads(row[0]) if row else dict(key='', broadcast_enabled=False)

    def status(settings):
        return dict(configured=bool(settings['key']), broadcast_enabled=settings['broadcast_enabled'])

    @m.app.get('/api/maps/google/settings', dependencies=[Depends(m.auth)])
    def settings(response: Response):
        response.headers['Cache-Control'] = 'no-store'
        return status(read())

    @m.app.put('/api/maps/google/settings', dependencies=[Depends(m.auth)])
    def save(body: GoogleSettings, response: Response):
        current = read()
        if body.key is not None:
            current['key'] = body.key
        current['broadcast_enabled'] = body.broadcast_enabled
        with m.db() as con:
            con.execute('INSERT OR REPLACE INTO map_settings VALUES (1,?)', (json.dumps(current),))
        response.headers['Cache-Control'] = 'no-store'
        return status(current)

    @m.app.get('/api/maps/google/client/{i}')
    def browser_settings(i: int, response: Response, broadcast: bool = False):
        channel = m.get_channel(i)
        current = read()
        response.headers['Cache-Control'] = 'no-store'
        # A browser key is intentionally observable, unlike the server-only TomTom key.
        # Only deliver it when a channel actually selects Google.
        enabled = channel.get('radar_map_style', '').startswith('google-')
        enabled = enabled and (not broadcast or current['broadcast_enabled'])
        return dict(key=current['key'] if enabled else '', **status(current))
