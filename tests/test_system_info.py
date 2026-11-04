from test_api import studio,AUTH
from app.system_info import recommend


def test_recommendations_follow_resources_and_channel_count():
    assert recommend(8,16,1)['fps']==15
    assert recommend(2,4,2)['fps']==10
    assert recommend(.5,1,1)['fps']==5
    assert recommend(8,16,5)['fps']==10
    assert recommend(8,None,1)['fps']==10
    assert 1<=recommend(64,128,1)['trial_channels']<=5


def test_recommendation_is_authenticated_and_read_only(studio):
    client,m=studio
    assert client.get('/api/system/recommendation').status_code==401
    before=[m.get_channel(i) for i in range(1,6)]
    r=client.get('/api/system/recommendation',headers=AUTH)
    assert r.status_code==200
    data=r.json();assert data['current_fps']==15
    assert data['active_channels']==0 and data['recommendation']['fps'] in (5,10,15)
    assert [m.get_channel(i) for i in range(1,6)]==before


def test_resource_reader_honors_container_limits(monkeypatch):
    import app.system_info as system
    files={'/sys/fs/cgroup/cpu.max':'150000 100000',
           '/proc/meminfo':'MemTotal: 8388608 kB\nMemAvailable: 4194304 kB',
           '/sys/fs/cgroup/memory.max':str(2*2**30),
           '/sys/fs/cgroup/memory.current':str(2**30)}
    monkeypatch.setattr(system,'read',lambda p:files.get(p,''))
    monkeypatch.setattr(system.os,'cpu_count',lambda:8)
    monkeypatch.setattr(system.os,'sched_getaffinity',lambda _:set(range(8)),raising=False)
    value=system.resources()
    assert value['cpu_cores']==1.5
    assert value['memory_gb']==2 and value['available_memory_gb']==1
