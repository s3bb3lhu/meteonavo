import asyncio
import base64
import time
from unittest.mock import AsyncMock
import pytest
from app.renderer import BrowserFrames,command
from pathlib import Path


def test_compositor_keeps_latest_frame_and_acknowledges_all():
    async def run():
        frames=BrowserFrames(None);frames.client=AsyncMock()
        for i in range(5):
            await frames.frame(dict(data=base64.b64encode(bytes([i])).decode(),sessionId=i))
        assert frames.latest==bytes([4]) and frames.ready.is_set()
        assert frames.client.send.await_count==5
        frames.check()
        frames.updated=time.monotonic()-16
        with pytest.raises(RuntimeError,match='aktuellen'):frames.check()
        await frames.close()
        await frames.frame(dict(data=base64.b64encode(b'late').decode(),sessionId=9))
        assert frames.latest==bytes([4]),'Late frames must not revive a closed capture'
    asyncio.run(run())


def test_capture_error_reaches_supervisor():
    async def run():
        frames=BrowserFrames(None);frames.client=AsyncMock()
        frames.client.send.side_effect=RuntimeError('browser disconnected')
        await frames.frame(dict(data=base64.b64encode(b'image').decode(),sessionId=1))
        with pytest.raises(RuntimeError,match='fehlgeschlagen'):frames.check()
    asyncio.run(run())


def test_stream_uses_configured_frame_rate_and_two_second_gop(monkeypatch):
    import app.renderer as renderer
    monkeypatch.setattr(renderer,'FPS',25)
    args=command(Path('/hls/1'))
    assert args[args.index('-framerate')+1]=='25'
    assert args[args.index('-g')+1]=='50'
