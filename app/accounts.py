"""One-time browser setup, password hashing and revocable server-side sessions."""
import hashlib
import os
import re
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import APIRouter,HTTPException,Request,Response,Depends
from fastapi.responses import FileResponse,RedirectResponse
from pydantic import BaseModel,Field,ConfigDict

COOKIE=os.getenv('SESSION_COOKIE_NAME','wcs_session')
SESSION_SECONDS=12*3600

def service_token():
    # Legacy installations may keep their existing renderer credential. New ones
    # generate it automatically in a private volume, without a setup prerequisite.
    return os.getenv('ADMIN_TOKEN','') or Path(os.getenv('SERVICE_KEY_FILE','/run/studio/renderer.key')).read_text().strip()

def init_accounts(db):
    if not os.getenv('ADMIN_TOKEN',''):
        path=Path(os.getenv('SERVICE_KEY_FILE','/run/studio/renderer.key'))
        path.parent.mkdir(parents=True,exist_ok=True)
        try:
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except FileExistsError:pass
        else:
            with os.fdopen(fd,'w') as f:f.write(secrets.token_urlsafe(48))
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS owner (id INTEGER PRIMARY KEY CHECK(id=1),username TEXT NOT NULL,password_hash TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY,expires REAL NOT NULL,csrf TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS auth_attempts (key TEXT PRIMARY KEY,stamp REAL,count INTEGER)')

def password_errors(value):
    errors=[]
    if len(value)<8:errors.append('Mindestens 8 Zeichen')
    if len(value)>128:errors.append('Höchstens 128 Zeichen')
    if not any(c.isupper() for c in value):errors.append('Mindestens 1 Großbuchstabe')
    if not any(c.isdigit() for c in value):errors.append('Mindestens 1 Zahl')
    if not any(not c.isalnum() and not c.isspace() for c in value):errors.append('Mindestens 1 Sonderzeichen')
    return errors

def hash_password(password,salt=None):
    salt=salt or secrets.token_bytes(16)
    digest=hashlib.scrypt(password.encode('utf-8'),salt=salt,n=32768,r=8,p=3,dklen=32,maxmem=128*1024*1024)
    return 'scrypt$'+salt.hex()+'$'+digest.hex()

def verify_password(password,stored):
    try:
        algorithm,salt,_=stored.split('$')
        if algorithm!='scrypt':return False
        return secrets.compare_digest(hash_password(password,bytes.fromhex(salt)),stored)
    except (ValueError,TypeError):return False

def configured(db):
    with db() as c:return bool(c.execute('SELECT 1 FROM owner WHERE id=1').fetchone())

def session(db,request):
    token=request.cookies.get(COOKIE,'')
    if not token or len(token)>128:return None
    digest=hashlib.sha256(token.encode()).hexdigest()
    with db() as c:
        row=c.execute('SELECT s.expires,s.csrf,o.username FROM sessions s CROSS JOIN owner o WHERE s.digest=? AND o.id=1 AND s.expires>?',(digest,time.time())).fetchone()
    return dict(digest=digest,expires=row[0],csrf=row[1],username=row[2]) if row else None

def check_origin(request):
    origin=request.headers.get('origin')
    if not origin:return
    allowed={str(request.base_url).rstrip('/')}
    public=os.getenv('PUBLIC_BASE_URL','')
    if public:
        p=urlsplit(public);allowed.add(p.scheme+'://'+p.netloc)
    if origin not in allowed:raise HTTPException(403,'Anfrage von einer anderen Website abgewiesen')

def authenticate(db,request):
    supplied=request.headers.get('authorization','')
    if supplied:
        try:token=service_token()
        except (FileNotFoundError,OSError):token=''
        if token and secrets.compare_digest(supplied.encode(),('Bearer '+token).encode()):return dict(internal=True)
    current=session(db,request)
    if not current:raise HTTPException(401,'Bitte anmelden')
    if request.method not in ('GET','HEAD','OPTIONS'):
        check_origin(request)
        if not secrets.compare_digest(request.headers.get('x-csrf-token','').encode(),current['csrf'].encode()):raise HTTPException(403,'Sitzung bestätigen: Seite neu laden und erneut versuchen')
    return current

class Credentials(BaseModel):
    model_config=ConfigDict(extra='forbid')
    username:str=Field(min_length=1,max_length=64)
    password:str=Field(min_length=1,max_length=128)

class Setup(Credentials):
    password_confirm:str=Field(max_length=128)

class AccountChange(BaseModel):
    model_config=ConfigDict(extra='forbid')
    username:str=Field(min_length=1,max_length=64)
    current_password:str=Field(min_length=1,max_length=128)
    password:str=Field(default='',max_length=128)
    password_confirm:str=Field(default='',max_length=128)

def validate_username(name):
    name=name.strip()
    if not re.fullmatch(r'[\w.@-]{3,64}',name):raise HTTPException(422,'Benutzername: 3–64 Zeichen; Buchstaben, Zahlen, Punkt, Bindestrich, Unterstrich oder @')
    return name

def validate_password(password,confirmation):
    errors=password_errors(password)
    if errors:raise HTTPException(422,'Passwort: '+', '.join(errors))
    if password!=confirmation:raise HTTPException(422,'Die Passwörter stimmen nicht überein')

def install(m):
    router=APIRouter();db=m.db
    def issue(request,response):
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
        with db() as c:
            c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
            c.execute('INSERT INTO sessions VALUES (?,?,?)',(digest,time.time()+SESSION_SECONDS,csrf))
        secure=request.url.scheme=='https' or os.getenv('PUBLIC_BASE_URL','').startswith('https://')
        response.set_cookie(COOKIE,token,max_age=SESSION_SECONDS,httponly=True,samesite='strict',secure=secure,path='/')
        if COOKIE!='wcs_session':response.delete_cookie('wcs_session',path='/',secure=secure,httponly=True,samesite='strict')
        response.headers['Cache-Control']='no-store'
        return csrf

    def page(request,mode):
        installed=configured(db);logged=session(db,request)
        if not installed and mode!='setup':return RedirectResponse('/setup',status_code=303)
        if installed and mode=='setup':return RedirectResponse('/settings' if logged else '/login',status_code=303)
        if mode=='login' and logged:return RedirectResponse('/settings',status_code=303)
        if mode=='account' and not logged:return RedirectResponse('/login?next=/account',status_code=303)
        return FileResponse(m.STATIC/'account.html',headers={'Cache-Control':'no-store','Referrer-Policy':'same-origin'})

    @router.get('/setup')
    def setup_page(request:Request):return page(request,'setup')

    @router.get('/login')
    def login_page(request:Request):return page(request,'login')

    @router.get('/account')
    def account_page(request:Request):return page(request,'account')

    @router.get('/api/auth/status')
    def status(request:Request,response:Response):
        response.headers['Cache-Control']='no-store'
        current=session(db,request)
        return dict(configured=configured(db),authenticated=bool(current),username=current['username'] if current else None,csrf=current['csrf'] if current else None)

    @router.post('/api/auth/setup')
    def setup(data:Setup,request:Request,response:Response):
        check_origin(request)
        if configured(db):raise HTTPException(409,'Die Einrichtung wurde bereits abgeschlossen. Bitte anmelden.')
        username=validate_username(data.username);validate_password(data.password,data.password_confirm)
        hashed=hash_password(data.password)
        # The singleton constraint and write transaction make concurrent setup
        # submissions mutually exclusive, even across API processes.
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM owner WHERE id=1').fetchone():raise HTTPException(409,'Die Einrichtung wurde bereits abgeschlossen. Bitte anmelden.')
            c.execute('INSERT INTO owner VALUES (1,?,?)',(username,hashed))
        return dict(ok=True,username=username,csrf=issue(request,response))

    def limit_key(request):return request.client.host if request.client else 'unknown'
    def check_limit(request):
        with db() as c:row=c.execute('SELECT stamp,count FROM auth_attempts WHERE key=?',(limit_key(request),)).fetchone()
        if row and time.time()-row[0]<900 and row[1]>=10:raise HTTPException(429,'Zu viele Fehlversuche. Bitte in 15 Minuten erneut versuchen.',headers={'Retry-After':'900'})
    def failed(request):
        with db() as c:
            c.execute('DELETE FROM auth_attempts WHERE stamp<?',(time.time()-900,))
            c.execute('INSERT INTO auth_attempts VALUES (?,?,1) ON CONFLICT(key) DO UPDATE SET count=count+1',(limit_key(request),time.time()))

    @router.post('/api/auth/login')
    def login(data:Credentials,request:Request,response:Response):
        check_origin(request);check_limit(request)
        with db() as c:row=c.execute('SELECT username,password_hash FROM owner WHERE id=1').fetchone()
        # Still perform the password derivation when the name is unknown.
        stored=row[1] if row else hash_password('Unconfigured!8',bytes(16))
        correct=verify_password(data.password,stored)
        if not row or not secrets.compare_digest(data.username.strip().casefold().encode(),row[0].casefold().encode()) or not correct:
            failed(request);raise HTTPException(401,'Benutzername oder Passwort ist falsch')
        with db() as c:c.execute('DELETE FROM auth_attempts WHERE key=?',(limit_key(request),))
        return dict(ok=True,username=row[0],csrf=issue(request,response))

    @router.post('/api/auth/logout',dependencies=[Depends(m.auth)])
    def logout(request:Request,response:Response):
        current=session(db,request)
        if current:
            with db() as c:c.execute('DELETE FROM sessions WHERE digest=?',(current['digest'],))
        response.delete_cookie(COOKIE,path='/',samesite='strict',httponly=True,secure=request.url.scheme=='https' or os.getenv('PUBLIC_BASE_URL','').startswith('https://'))
        response.headers['Cache-Control']='no-store'
        return dict(ok=True)

    @router.put('/api/auth/account',dependencies=[Depends(m.auth)])
    def change(data:AccountChange,request:Request,response:Response):
        check_limit(request)
        with db() as c:row=c.execute('SELECT password_hash FROM owner WHERE id=1').fetchone()
        if not row or not verify_password(data.current_password,row[0]):
            failed(request);raise HTTPException(401,'Aktuelles Passwort ist falsch')
        username=validate_username(data.username)
        if data.password:validate_password(data.password,data.password_confirm)
        elif data.password_confirm:raise HTTPException(422,'Neues Passwort fehlt')
        hashed=hash_password(data.password) if data.password else row[0]
        with db() as c:
            c.execute('UPDATE owner SET username=?,password_hash=? WHERE id=1',(username,hashed))
            c.execute('DELETE FROM sessions')
        return dict(ok=True,username=username,csrf=issue(request,response))

    m.app.include_router(router)
