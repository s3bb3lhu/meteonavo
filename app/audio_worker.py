"""Continuous stereo PCM with silence fallback; an audio outage never stops video."""
import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
import httpx
from .accounts import service_token

CHUNK=19200  # 100 ms, 48 kHz, signed 16-bit stereo

def decoder_command(config,api,channel,token,concat_path):
    cmd=['ffmpeg','-nostdin','-hide_banner','-loglevel','error']
    if config['mode']=='playlist':
        cmd+=['-re','-stream_loop','-1','-protocol_whitelist','file,pipe','-f','concat','-safe','0','-i',str(concat_path)]
    else:
        cmd+=['-re','-rw_timeout','12000000','-protocol_whitelist','http,tcp,crypto','-headers',f'Authorization: Bearer {token}\r\n','-i',f'{api}/api/radio/stream/{config["station"]}']
    return cmd+['-vn','-map','0:a:0','-af',f'volume={config["volume"]}', '-ac','2','-ar','48000','-f','s16le','pipe:1']

class AudioPipe:
    def __init__(self,api,channel):
        self.api,self.channel=api,channel
        self.read_fd,self.write_fd=os.pipe()
        self.queue=asyncio.Queue(maxsize=5)
        self.tasks=[]

    def start(self):
        self.tasks=[asyncio.create_task(self.write()),asyncio.create_task(self.supervise())]

    async def write(self):
        def send(data):
            while data:
                count=os.write(self.write_fd,data);data=data[count:]
        target=time.monotonic()
        while True:
            try:data=self.queue.get_nowait()
            except asyncio.QueueEmpty:data=bytes(CHUNK)
            try:await asyncio.to_thread(send,data)
            except (BrokenPipeError,OSError):return
            target+=.1
            await asyncio.sleep(max(0,target-time.monotonic()))
            if target<time.monotonic()-.5:target=time.monotonic()

    async def decode(self,config):
        process=None;concat=None
        try:
            if config['mode']=='playlist':
                # Paths are server-generated UUID names, never original upload filenames.
                fd,name=tempfile.mkstemp(prefix='wcs-audio-',suffix='.txt');os.close(fd);concat=Path(name)
                concat.write_text(''.join("file '"+p.replace("'","'\\''")+"'\n" for p in config['tracks']),encoding='utf-8')
            process=await asyncio.create_subprocess_exec(*decoder_command(config,self.api,self.channel,service_token(),concat),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
            while True:
                try:data=await asyncio.wait_for(process.stdout.readexactly(CHUNK),20)
                except (asyncio.IncompleteReadError,TimeoutError):break
                await self.queue.put(data)
        finally:
            if process and process.returncode is None:
                process.kill();await process.wait()
            if concat:concat.unlink(missing_ok=True)

    async def supervise(self):
        signature=None;decoder=None;config=None;retry=0
        try:
            async with httpx.AsyncClient(timeout=10,headers={'Authorization':'Bearer '+service_token()}) as client:
                while True:
                    try:
                        r=await client.get(f'{self.api}/api/channels/{self.channel}/audio');r.raise_for_status();candidate=r.json()
                        key=json.dumps(candidate,sort_keys=True)
                        if key!=signature:
                            if decoder:decoder.cancel();await asyncio.gather(decoder,return_exceptions=True)
                            while not self.queue.empty():self.queue.get_nowait()
                            signature=key;config=candidate;decoder=None;retry=0
                        usable=config and (config['mode']=='radio' or config['mode']=='playlist' and config['tracks'])
                        if usable and (not decoder or decoder.done()) and time.monotonic()>=retry:
                            if decoder:await asyncio.gather(decoder,return_exceptions=True)
                            decoder=asyncio.create_task(self.decode(config));retry=time.monotonic()+15
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(5)
        finally:
            if decoder:decoder.cancel();await asyncio.gather(decoder,return_exceptions=True)

    async def close(self):
        for task in self.tasks:task.cancel()
        os.close(self.read_fd)
        os.close(self.write_fd)
        await asyncio.gather(*self.tasks,return_exceptions=True)
