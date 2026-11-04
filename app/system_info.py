"""Conservative resource recommendations, explicitly not a capacity benchmark."""
import os
from pathlib import Path
from fastapi import Depends


def read(path):
    try:return Path(path).read_text().strip()
    except (OSError,ValueError):return ''


def resources():
    cores=float(os.cpu_count() or 1)
    try:cores=min(cores,len(os.sched_getaffinity(0)))
    except (AttributeError,OSError):pass
    quota=read('/sys/fs/cgroup/cpu.max').split()
    try:
        if len(quota)==2 and quota[0]!='max':cores=min(cores,int(quota[0])/int(quota[1]))
        else:
            q=int(read('/sys/fs/cgroup/cpu/cpu.cfs_quota_us') or -1)
            period=int(read('/sys/fs/cgroup/cpu/cpu.cfs_period_us') or 100000)
            if q>0:cores=min(cores,q/period)
    except (ValueError,ZeroDivisionError):pass
    mem={}
    for line in read('/proc/meminfo').splitlines():
        parts=line.split()
        if len(parts)>=2:
            try:mem[parts[0].rstrip(':')]=int(parts[1])*1024
            except ValueError:pass
    total=mem.get('MemTotal',0);available=mem.get('MemAvailable',0)
    for root,limit_name,used_name in [('/sys/fs/cgroup','memory.max','memory.current'),('/sys/fs/cgroup/memory','memory.limit_in_bytes','memory.usage_in_bytes')]:
        try:
            limit=int(read(root+'/'+limit_name));used=int(read(root+'/'+used_name))
            if 0<limit<total:total=limit;available=min(available,max(0,limit-used))
        except ValueError:pass
    return dict(cpu_cores=round(cores,2),memory_gb=round(total/2**30,2) if total else None,available_memory_gb=round(available/2**30,2) if total else None)


def recommend(cpu,memory,active):
    count=max(1,active)
    # Reserve capacity for API, operating system, music and variable page complexity.
    if memory is None:return dict(fps=10,profile='Vorsichtiger Start',trial_channels=1)
    if cpu>=2*count and memory>=1+count*.75:fps,profile=15,'Flüssiger Lauftext'
    elif cpu>=count and memory>=.75+count*.5:fps,profile=10,'Sparsam'
    else:fps,profile=5,'Sehr sparsam'
    trial=max(1,min(5,int(cpu//2),int(max(0,memory-1)//.75)))
    return dict(fps=fps,profile=profile,trial_channels=trial)


def install(m):
    @m.app.get('/api/system/recommendation',dependencies=[Depends(m.auth)])
    def recommendation():
        hw=resources()
        active=sum(m.get_channel(i)['enabled'] for i in range(1,6))
        try:current=max(1,min(30,int(os.getenv('RENDER_FPS','15'))))
        except ValueError:current=15
        return dict(**hw,active_channels=active,current_fps=current,ticker_pixels_per_second=30,
                    recommendation=recommend(hw['cpu_cores'],hw['available_memory_gb'],active),
                    basis='Ressourcen-Richtwert, kein Leistungstest',
                    note='CPU-Limits und RAM werden berücksichtigt. Andere Anwendungen, CPU-Modell und aufwendige Designs können die Leistung reduzieren. Erst einen Kanal testen und schrittweise erweitern. Die Empfehlung ändert die laufende Ausgabe nicht.')
