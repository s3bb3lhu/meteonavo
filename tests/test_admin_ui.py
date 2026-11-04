import json
from pathlib import Path
from test_api import studio


def test_admin_assets_and_four_language_guides(studio):
    client,m=studio
    assert client.get('/help').status_code==200
    catalogue=client.get('/static/ui-translations.json').json()
    assert len(catalogue)>=500
    assert all(len(values)==3 and all(values) for values in catalogue.values())
    for lang in ['de','en','fr','es']:
        response=client.get('/static/manual/meteonova-'+lang+'.html')
        assert response.status_code==200 and 'lang="'+lang+'"' in response.text and 'METEONOVA' in response.text
    for path in ['/','/watch/1']:
        response=client.get(path)
        assert response.text.count('/static/studio-ui.js?')==1 and response.text.count('/static/i18n.js?')==1
    assert client.get('/api/thumbnail/1').status_code==404
    assert client.get('/api/thumbnail/6').status_code==404


def test_project_and_third_party_license_texts_are_separate(studio):
    client,m=studio
    own=client.get('/license');third=client.get('/third-party-notices')
    assert own.status_code==third.status_code==200
    assert 's3bb3lhu' in own.text and 'vorherigen ausdrücklichen Zustimmung' in own.text
    assert 'FFmpeg' in third.text and 'Apache-2.0' in third.text
    assert own.headers['content-type'].startswith('text/plain')
