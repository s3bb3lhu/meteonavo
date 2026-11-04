"""Public-address-only radio proxy. Every redirect, manifest, segment and key is checked.
No external service ever receives the internal admin authorization header.
"""
import ipaddress
import re
from urllib.parse import urlsplit,urljoin,quote
from .news import FeedConnection,resolve_public

def radio_url(url):
    if not isinstance(url,str) or len(url)>4096 or any(ord(c)<=32 for c in url) or '\\' in url:raise ValueError('Ungültige Radioadresse')
    p=urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.fragment:raise ValueError('Nur öffentliche HTTP(S)-Radiostreams')
    port=p.port or (443 if p.scheme=='https' else 80)
    if not 1<=port<=65535 or p.hostname.lower().endswith(('.local','.internal','.localhost')) or p.hostname.lower()=='localhost':raise ValueError('Interne Adresse gesperrt')
    try:address=ipaddress.ip_address(p.hostname)
    except ValueError:pass
    else:
        if not address.is_global:raise ValueError('Interne Adresse gesperrt')
    return p,port

def open_public(url):
    for _ in range(5):
        p,port=radio_url(url);host=p.hostname.encode('idna').decode()
        address=resolve_public(host,port)[0]
        conn=FeedConnection(host,port,address,p.scheme=='https',12)
        try:
            conn.request('GET',(p.path or '/')+('?' + p.query if p.query else ''),headers={'User-Agent':'WeatherChannelStudio/0.2','Accept-Encoding':'identity','Icy-MetaData':'0'})
            response=conn.getresponse()
            if response.status in (301,302,303,307,308):
                url=urljoin(url,response.getheader('Location',''));conn.close();continue
            if response.status!=200:raise ValueError('Radioserver nicht erreichbar')
            return conn,response,url
        except BaseException:
            conn.close();raise
    raise ValueError('Zu viele Radio-Weiterleitungen')

def manifest(text,url,proxy_prefix):
    def proxy(target):
        absolute=urljoin(url,target);radio_url(absolute)
        return proxy_prefix+quote(absolute,safe='')
    out=[]
    for line in text.splitlines():
        if line and not line.startswith('#'):line=proxy(line.strip())
        elif 'URI="' in line:line=re.sub(r'URI="([^"]+)"',lambda m:'URI="'+proxy(m[1])+'"',line)
        out.append(line)
    return '\n'.join(out)+'\n'
