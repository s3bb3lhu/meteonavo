import socket
import time
import pytest
from app import news
from test_api import studio, AUTH, config

RSS = b'''<rss version="2.0"><channel><title>Testnachrichten</title><item><title>Erste Meldung &amp; Wetter</title></item><item><title><![CDATA[<b>Zweite Meldung</b>]]></title></item><item><title>Erste Meldung &amp; Wetter</title></item></channel></rss>'''


def test_rss_atom_and_untrusted_xml():
    data = news.parse_feed(RSS)
    assert data == {'source': 'Testnachrichten', 'headlines': ['Erste Meldung & Wetter', 'Zweite Meldung']}
    atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom</title><entry><title>Neuigkeiten</title></entry></feed>'
    assert news.parse_feed(atom)['headlines'] == ['Neuigkeiten']
    for body in (b'<html><title>Keine Nachrichten</title></html>', b'<rss><channel/></rss>', b'<!DOCTYPE rss [<!ENTITY x "boom">]><rss><channel><item><title>&x;</title></item></channel></rss>'):
        with pytest.raises(Exception):
            news.parse_feed(body)
    with pytest.raises(ValueError):
        news.parse_feed(b'x' * (news.MAX_BYTES + 1))


@pytest.mark.parametrize('url', ['file:///etc/passwd','http://localhost/feed','http://127.0.0.1/feed','http://[::1]/feed','http://169.254.169.254/latest','http://192.168.1.1/rss','https://user:secret@example.org/rss','https://example.org:7373/rss','https://example.org/\nHost:evil'])
def test_invalid_and_private_urls(url):
    with pytest.raises(ValueError):
        news.validate_url(url)


def test_dns_and_redirect_protection(monkeypatch):
    monkeypatch.setattr(news.socket, 'getaddrinfo', lambda *a, **kw: [(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',80))])
    with pytest.raises(ValueError):
        news.download_feed('https://looks-public.example/rss')
    monkeypatch.setattr(news.socket, 'getaddrinfo', lambda *a, **kw: [(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))])
    calls = []
    class Redirect:
        status = 302
        def getheader(self, name, default=''):
            return 'https://127.0.0.1/private' if name == 'Location' else default
    class FakeConnection:
        def __init__(self, host, port, address, tls, timeout): calls.append((host,address,tls))
        def request(self, *args, **kwargs): pass
        def getresponse(self): return Redirect()
        def close(self): pass
    monkeypatch.setattr(news, 'FeedConnection', FakeConnection)
    with pytest.raises(ValueError):
        news.download_feed('https://news.example/rss')
    assert calls == [('news.example','8.8.8.8',True)]


def test_feed_cache_failure_and_removal(studio, monkeypatch):
    client, main = studio
    assert client.get('/api/news/1').json()['enabled'] is False
    calls = []
    def fetched(url):
        calls.append(url)
        return news.parse_feed(RSS)
    monkeypatch.setattr(main, 'fetch_feed', fetched)
    channel = config(rss_url='https://news.example/rss')
    assert client.put('/api/channels/1', headers=AUTH, json=channel).status_code == 200
    first = client.get('/api/news/1').json()
    assert first['headlines'][0] == 'Erste Meldung & Wetter'
    assert first['stale'] is False
    client.get('/api/news/1')
    assert len(calls) == 1
    with main.db() as con:
        con.execute('UPDATE news SET attempt=?', (time.time()-301,))
    def offline(url): raise OSError('offline')
    monkeypatch.setattr(main, 'fetch_feed', offline)
    stale = client.get('/api/news/1').json()
    assert stale['stale'] and stale['headlines'] == first['headlines']
    assert stale['fetched_at'] == first['fetched_at']
    assert 'offline' not in stale['message']
    with main.db() as con:
        con.execute('UPDATE news SET stamp=?,attempt=?', (time.time()-90000,time.time()-301))
    assert client.get('/api/news/1').json()['headlines'] == []
    changed={**channel,'rss_url':'https://new.example/rss'}
    client.put('/api/channels/1', headers=AUTH, json=changed)
    assert client.get('/api/news/1').json()['headlines'] == []
    client.put('/api/channels/1', headers=AUTH, json={**channel,'rss_url':''})
    assert not client.get('/api/news/1').json()['enabled']
    assert client.get('/api/news/6').status_code == 404


def test_legacy_config_and_rss_authorization(studio):
    client, main = studio
    assert client.get('/api/channels').json()[0]['rss_url'] == ''
    assert client.put('/api/channels/1', json=config(rss_url='https://news.example/rss')).status_code == 401
    assert client.put('/api/channels/1', headers=AUTH, json=config(rss_url='http://127.0.0.1/rss')).status_code == 422
    with main.db() as con:
        con.execute('UPDATE channels SET config=? WHERE id=1', ('{"name":"Alt","enabled":false}',))
    assert client.get('/api/channels').json()[0]['rss_url'] == ''
