from test_api import studio, AUTH


def test_optional_key_auth_preservation_removal_and_browser_visibility(studio):
    client, m = studio
    url = '/api/maps/google/settings'
    assert client.get(url).status_code == 401
    assert client.put(url, json={'key': 'test-google-browser-key'}).status_code == 401
    assert client.get(url, headers=AUTH).json() == dict(configured=False, broadcast_enabled=False)
    response = client.put(url, headers=AUTH, json={'key': 'test-google-browser-key'})
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    assert 'test-google-browser-key' not in response.text
    assert client.get('/api/maps/google/client/1').json()['key'] == ''
    for style in ['google-roadmap', 'google-hybrid', 'google-satellite', 'google-terrain']:
        assert client.patch('/api/channels/1', headers=AUTH, json={'radar_map_style': style}).status_code == 200
        assert client.get('/api/maps/google/client/1').json()['key'] == 'test-google-browser-key'
        assert client.get('/api/maps/google/client/1?broadcast=true').json()['key'] == ''
    assert 'test-google-browser-key' not in client.get('/api/channels').text
    response = client.put(url, headers=AUTH, json={'broadcast_enabled': True})
    assert response.json()['configured'], 'An omitted key must preserve the stored key'
    assert client.get('/api/maps/google/client/1?broadcast=true').json()['key'] == 'test-google-browser-key'
    assert client.get('/api/maps/google/client/1').headers['cache-control'] == 'no-store'
    assert client.get('/api/maps/google/client/6').status_code == 404
    assert client.put(url, headers=AUTH, json={'key': '', 'broadcast_enabled': False}).json()['configured'] is False
    assert client.get('/api/maps/google/client/1').json()['key'] == ''


def test_small_radii_persist_and_existing_maps_remain(studio):
    client, m = studio
    for radius in [1, 2, 5, 10, 25, 50, 5000, None]:
        assert client.patch('/api/channels/1', headers=AUTH, json={'radar_radius_km': radius}).status_code == 200
        assert m.get_channel(1)['radar_radius_km'] == radius
    for radius in [0, -1, 5001]:
        assert client.patch('/api/channels/1', headers=AUTH, json={'radar_radius_km': radius}).status_code == 422
    for style in ['streets', 'streets-dark', 'satellite', 'satellite-night', 'overview']:
        assert client.patch('/api/channels/1', headers=AUTH, json={'radar_map_style': style}).status_code == 200
