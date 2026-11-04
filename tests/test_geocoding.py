import json
import time
import httpx
from test_api import studio,AUTH
from app.geocoding import queries,results,matching

QUERY='calpe urbanicazion Ejemplo 7b'
def feature(**properties):
    return dict(properties=dict(countrycode='ES',city='Calp',postcode='03710',**properties),geometry=dict(type='Point',coordinates=[0.0,40.0]))

def test_spanish_urbanisation_normalization_and_house_fallback():
    assert queries(QUERY,'ES')==['Urbanización Ejemplo 7b, calpe','Urbanización Ejemplo, calpe']
    assert queries('Urbanización Ejemplo 7B, 03710 Calp','ES')[-1]=='Urbanización Ejemplo, 03710 Calp'
    assert queries('Markt 1, Leipzig','DE')==['Markt 1, Leipzig']

def test_unrelated_number_only_matches_are_not_addresses():
    unrelated=dict(countrycode='ES',city='Castro Urdiales',housenumber='7B',street='Calle de Manuel Urquijo',locality='Urbanización La Ballena')
    assert not matching(unrelated,QUERY,'ES')
    wrong_number=dict(countrycode='ES',city='Calp',housenumber='9',street='Urbanización Ejemplo')
    assert not matching(wrong_number,QUERY,'ES')
    assert matching({**wrong_number,'housenumber':'7B'},QUERY,'ES')

def test_ejemplo_neighbourhood_is_explicitly_approximate_not_house_7b():
    rows=results([feature(name='Urbanització Ejemplo Alta',type='locality',district='Urbanització Distrito de Ejemplo'),feature(name='Barranco de las Ejemplos',osm_key='waterway',type='other')],QUERY,'ES')
    assert len(rows)==1
    assert rows[0]['precision']=='locality'
    assert 'Ejemplo Alta' in rows[0]['address'] and 'Calp' in rows[0]['address']
    assert 'Hausnummer ist nicht bestätigt' in rows[0]['precision_note']
    assert '7B' not in rows[0]['address']

def test_street_type_and_locality_are_preserved():
    rows=results([feature(name='Carrer de Mallorca',type='street',locality='Eixample')],'Mallorca','ES')
    assert rows[0]['precision']=='street' and 'Eixample' in rows[0]['address']

def test_api_fallback_and_versioned_cache_without_channel_changes(studio,monkeypatch):
    client,m=studio;calls=[];before=client.get('/api/channels',headers=AUTH).json()
    class FakeClient:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,params):
            calls.append(params)
            f=feature(type='locality',name='Urbanització Ejemplo Alta')
            if '7b' in params['q'].lower():f['properties'].update(city='Santander',name='Unrelated',housenumber='7B')
            return httpx.Response(200,json={'features':[f]},request=httpx.Request('GET',url))
    monkeypatch.setattr(m.httpx,'AsyncClient',FakeClient)
    with m.db() as c:c.execute('INSERT INTO geocache VALUES (?,?,?)',('ES:'+QUERY,time.time(),'[]'))
    response=client.get('/api/addresses',headers=AUTH,params={'q':QUERY,'country':'ES'})
    assert response.status_code==200 and len(response.json())==1 and len(calls)==2
    assert response.json()[0]['precision']=='locality'
    assert client.get('/api/addresses',headers=AUTH,params={'q':QUERY,'country':'ES'}).json()==response.json()
    assert len(calls)==2
    assert client.get('/api/channels',headers=AUTH).json()==before
