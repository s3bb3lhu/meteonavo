from test_api import studio, config, AUTH


def test_designs_persist_and_reject_unknown(studio):
    client, main = studio
    for theme in ['classic', 'aurora', 'noir', 'solar', 'arctic', 'sky', 'city', 'nature', 'cinematic', 'flow', 'cinema-glass', 'cinema-prime', 'cinema-panorama']:
        response=client.put('/api/channels/1',headers=AUTH,json=config(theme=theme,motion=False))
        assert response.status_code==200
        main.init_db()
        channel=client.get('/api/channels').json()[0]
        assert channel['theme']==theme and channel['motion'] is False
    assert client.put('/api/channels/1',headers=AUTH,json=config(theme='<script>')).status_code==422
    assert client.get('/api/channels').json()[1]['theme']=='classic'
    assert client.get('/api/channels').json()[1]['motion'] is True
