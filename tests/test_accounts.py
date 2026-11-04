import concurrent.futures
import json
import time
import pytest
from test_api import studio,AUTH
from app.accounts import COOKIE,password_errors,verify_password,service_token,init_accounts

VALID=dict(username='StudioAdmin',password='Abcdef1!',password_confirm='Abcdef1!')

@pytest.mark.parametrize('password',['abc1!','abcdefgh!','Abcdefgh!','Abcdefg1','Abcdef1 '])
def test_password_requirements_rejected_server_side(studio,password):
    client,m=studio
    r=client.post('/api/auth/setup',json={**VALID,'password':password,'password_confirm':password})
    assert r.status_code==422 and not client.get('/api/auth/status').json()['configured']

def test_first_run_one_time_setup_session_and_existing_data(studio):
    client,m=studio
    with m.db() as c:
        original=c.execute('SELECT config FROM channels ORDER BY id').fetchall()
    assert client.get('/',follow_redirects=False).headers['location']=='/setup'
    assert client.get('/settings/audio',follow_redirects=False).headers['location']=='/setup'
    assert client.get('/setup').status_code==200
    assert client.get('/api/music').status_code==401
    mismatch=client.post('/api/auth/setup',json={**VALID,'password_confirm':'Different1!'})
    assert mismatch.status_code==422
    response=client.post('/api/auth/setup',json=VALID)
    assert response.status_code==200
    cookie=response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie and 'max-age=43200' in cookie
    status=client.get('/api/auth/status').json()
    assert status['authenticated'] and status['username']=='StudioAdmin'
    assert client.get('/api/music').status_code==200
    m.init_db()
    assert client.get('/api/auth/status').json()['authenticated']
    assert client.get('/settings/audio',follow_redirects=False).status_code==200
    assert client.get('/setup',follow_redirects=False).headers['location']=='/settings'
    assert client.post('/api/auth/setup',json={**VALID,'username':'Replacement'}).status_code==409
    with m.db() as c:
        assert c.execute('SELECT count(*) FROM owner').fetchone()[0]==1
        stored=c.execute('SELECT password_hash FROM owner').fetchone()[0]
        assert 'Abcdef1!' not in stored and verify_password(VALID['password'],stored)
        assert c.execute('SELECT config FROM channels ORDER BY id').fetchall()==original
        assert client.cookies.get(COOKIE) not in str(c.execute('SELECT * FROM sessions').fetchall())

def test_session_csrf_origin_logout_and_login(studio):
    client,m=studio
    csrf=client.post('/api/auth/setup',json=VALID).json()['csrf']
    assert client.patch('/api/channels/1',json={'name':'A'}).status_code==403
    assert client.patch('/api/channels/1',headers={'X-CSRF-Token':csrf,'Origin':'https://evil.example'},json={'name':'A'}).status_code==403
    assert client.patch('/api/channels/1',headers={'X-CSRF-Token':csrf,'Origin':'http://testserver'},json={'name':'A'}).status_code==200
    assert client.post('/api/auth/logout',headers={'X-CSRF-Token':csrf}).status_code==200
    assert not client.get('/api/auth/status').json()['authenticated']
    assert client.get('/api/music').status_code==401
    assert client.get('/settings',follow_redirects=False).headers['location'].startswith('/login')
    assert client.post('/api/auth/login',json=dict(username='StudioAdmin',password='Wrong1!!')).status_code==401
    assert client.post('/api/auth/login',headers={'Origin':'https://evil.example'},json=VALID|{}).status_code in (403,422)
    result=client.post('/api/auth/login',json=dict(username='studioadmin',password=VALID['password']))
    assert result.status_code==200 and result.json()['csrf']!=csrf
    with m.db() as c:c.execute('UPDATE sessions SET expires=?',(time.time()-1,))
    assert client.get('/api/music').status_code==401

def test_password_change_revokes_all_old_sessions(studio):
    client,m=studio
    first=client.post('/api/auth/setup',json=VALID)
    old_cookie=client.cookies.get(COOKIE)
    body=dict(username='NewName',current_password=VALID['password'],password='NewPass8!',password_confirm='NewPass8!')
    response=client.put('/api/auth/account',headers={'X-CSRF-Token':first.json()['csrf']},json=body)
    assert response.status_code==200 and client.cookies.get(COOKIE)!=old_cookie
    assert client.get('/api/auth/status').json()['username']=='NewName'
    assert client.get('/api/music',headers={'Cookie':COOKIE+'='+old_cookie}).status_code==401
    with m.db() as c:assert c.execute('SELECT count(*) FROM sessions').fetchone()[0]==1
    client.cookies.clear()
    assert client.post('/api/auth/login',json=dict(username='StudioAdmin',password=VALID['password'])).status_code==401
    assert client.post('/api/auth/login',json=dict(username='NewName',password='NewPass8!')).status_code==200

def test_parallel_setup_only_one_winner(studio):
    client,m=studio
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda name:client.post('/api/auth/setup',json={**VALID,'username':name}).status_code,['AdminOne','AdminTwo']))
    assert sorted(results)==[200,409]
    with m.db() as c:assert c.execute('SELECT count(*) FROM owner').fetchone()[0]==1

def test_login_throttled_and_foreign_setup_origin_blocked(studio):
    client,m=studio
    assert client.post('/api/auth/setup',headers={'Origin':'https://evil.example'},json=VALID).status_code==403
    client.post('/api/auth/setup',json=VALID);client.cookies.clear()
    for _ in range(10):assert client.post('/api/auth/login',json=dict(username='Unknown',password='Wrong1!!')).status_code==401
    assert client.post('/api/auth/login',json=dict(username='StudioAdmin',password=VALID['password'])).status_code==429

def test_no_manual_token_required_and_hashes_salted(studio,monkeypatch,tmp_path):
    client,m=studio
    monkeypatch.delenv('ADMIN_TOKEN',raising=False)
    path=tmp_path/'renderer.key';monkeypatch.setenv('SERVICE_KEY_FILE',str(path))
    init_accounts(m.db);token=service_token();assert len(token)>40
    init_accounts(m.db);assert service_token()==token
    assert client.get('/api/music',headers={'Authorization':'Bearer '+token}).status_code==200
    assert client.get('/api/music').status_code==401
    assert not password_errors('ABCDEF1!')
    monkeypatch.delenv('PUBLIC_BASE_URL',raising=False)
    assert client.put('/api/channels/1',headers={'Authorization':'Bearer '+token},json=dict(name='Test',location='Hanau',latitude=50.13,longitude=8.92,enabled=True)).status_code==200
    assert 'http://testserver/live/1/index.m3u8' in client.get('/playlist.m3u').text


def test_login_limit_resets_after_expired_window(studio):
    client,m=studio
    client.post('/api/auth/setup',json=VALID);client.cookies.clear()
    with m.db() as c:c.execute('INSERT INTO auth_attempts VALUES (?,?,?)',('testclient',time.time()-901,10))
    bad=dict(username='Unknown',password='Wrong1!!')
    for _ in range(10):assert client.post('/api/auth/login',json=bad).status_code==401
    assert client.post('/api/auth/login',json=bad).status_code==429
    with m.db() as c:
        stamp,count=c.execute('SELECT stamp,count FROM auth_attempts WHERE key=?',('testclient',)).fetchone()
    assert stamp>time.time()-60 and count==10


def test_https_host_cookie_and_origin(studio,monkeypatch):
    from app import accounts
    client,m=studio
    monkeypatch.setattr(accounts,'COOKIE','__Host-meteonavo-session')
    monkeypatch.setenv('PUBLIC_BASE_URL','https://testserver')
    client.base_url='https://testserver'
    response=client.post('/api/auth/setup',json=VALID)
    assert response.status_code==200
    cookie=response.headers['set-cookie'].lower()
    assert cookie.startswith('__host-meteonavo-session=')
    assert 'secure' in cookie and 'httponly' in cookie and 'path=/' in cookie and 'domain=' not in cookie
    csrf=response.json()['csrf']
    assert client.get('/api/auth/status').json()['authenticated']
    assert client.patch('/api/channels/1',json={'name':'HTTPS'},headers={'Origin':'https://testserver','X-CSRF-Token':csrf}).status_code==200
    assert client.patch('/api/channels/1',json={'name':'HTTP'},headers={'Origin':'http://testserver','X-CSRF-Token':csrf}).status_code==403
