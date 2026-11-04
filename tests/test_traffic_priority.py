import asyncio
from app.regional import road_priority,tomtom_fetch


def test_major_road_numbers_are_prioritized():
    assert road_priority(['A 3'])==0
    assert road_priority(['B45'])==0
    assert road_priority(['AP-7'])==0
    assert road_priority(['N332'])==0
    assert road_priority(['K123'])==1
    assert road_priority([])==1


def test_tomtom_requests_road_numbers_and_sorts_before_distance(monkeypatch):
    from app import regional
    class Result:
        status_code=200
        def json(self):
            return {'incidents':[{'geometry':{'type':'Point','coordinates':[8.001,50]},'properties':{'id':'local','from':'Lokal','to':'Ort','roadNumbers':[]}}, {'geometry':{'type':'Point','coordinates':[8.05,50]},'properties':{'id':'major','from':'Ausfahrt','to':'Kreuz','roadNumbers':['A 3','E42']}}]}
    class Client:
        def __init__(self,*a,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def get(self,url,params):assert 'roadNumbers' in params['fields'];return Result()
    monkeypatch.setattr(regional.httpx,'AsyncClient',Client)
    data=asyncio.run(tomtom_fetch('test',50,8,10))
    assert [x['id'] for x in data['items']]==['major','local']
    assert data['items'][0]['road']=='A3 / E42'
