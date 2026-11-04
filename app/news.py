"""RSS/Atom headlines. Only public HTTP(S), pinned DNS, bounded XML, no HTML."""
import http.client
import ipaddress
import re
import socket
import ssl
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from defusedxml import ElementTree

MAX_BYTES = 1024 * 1024


def validate_url(url):
    if not url:
        return url
    if len(url) > 2048 or any(ord(c) <= 32 for c in url) or '\\' in url:
        raise ValueError('RSS-Link enthält ungültige Zeichen')
    try:
        parts = urlsplit(url)
        port = parts.port
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username is not None or parts.password is not None or parts.fragment:
            raise ValueError()
        if port not in (None, 443 if parts.scheme == 'https' else 80):
            raise ValueError()
        host = parts.hostname.rstrip('.').lower()
        if '%' in host or host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
            raise ValueError()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            host.encode('idna')
        else:
            if not address.is_global:
                raise ValueError()
    except (ValueError, UnicodeError):
        raise ValueError('RSS benötigt eine öffentliche HTTP(S)-Adresse ohne Zugangsdaten und mit Standardport') from None
    return url


def resolve_public(host, port):
    addresses = list(dict.fromkeys(info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)))
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError('RSS-Adresse verweist auf ein internes oder reserviertes Netz')
    return addresses


class FeedConnection(http.client.HTTPConnection):
    def __init__(self, host, port, address, tls, timeout):
        super().__init__(host, port=port, timeout=timeout)
        self.address, self.tls = address, tls

    def connect(self):
        # Connect to the already checked numeric IP; do not resolve hostname again.
        raw = socket.create_connection((self.address, self.port), timeout=self.timeout)
        if self.tls:
            try:
                self.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=self.host)
            except BaseException:
                raw.close()
                raise
        else:
            self.sock = raw


def download_feed(url):
    deadline = time.monotonic() + 20
    for redirect in range(4):
        validate_url(url)
        parts = urlsplit(url)
        host = parts.hostname.encode('idna').decode()
        port = parts.port or (443 if parts.scheme == 'https' else 80)
        addresses = resolve_public(host, port)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('RSS-Zeitlimit')
        conn = FeedConnection(host, port, addresses[0], parts.scheme == 'https', min(8, remaining))
        try:
            path = parts.path or '/'
            if parts.query:
                path += '?' + parts.query
            conn.request('GET', path, headers={'User-Agent': 'WeatherChannelStudio/0.1 RSS', 'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml', 'Accept-Encoding': 'identity'})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                target = urljoin(url, response.getheader('Location', ''))
                if parts.scheme == 'https' and urlsplit(target).scheme != 'https':
                    raise ValueError('Unsichere RSS-Weiterleitung')
                url = target
                continue
            if response.status != 200:
                raise ValueError('RSS-Quelle antwortet nicht erfolgreich')
            if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                raise ValueError('Komprimierte RSS-Antwort nicht unterstützt')
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('RSS-Zeitlimit')
                if conn.sock:
                    conn.sock.settimeout(min(8, remaining))
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                if not chunk:
                    return b''.join(chunks)
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError('RSS-Antwort ist zu groß')
                chunks.append(chunk)
        finally:
            conn.close()
    raise ValueError('Zu viele RSS-Weiterleitungen')


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(text, limit=240):
    parser = TextOnly()
    parser.feed(text or '')
    return re.sub(r'\s+', ' ', ''.join(parser.parts)).strip()[:limit]


def parse_feed(body):
    if len(body) > MAX_BYTES:
        raise ValueError('RSS-Antwort ist zu groß')
    root = ElementTree.fromstring(body, forbid_dtd=True)
    local = lambda node: node.tag.rsplit('}', 1)[-1]
    if local(root) not in ('rss', 'feed', 'RDF'):
        raise ValueError('Kein RSS- oder Atom-Feed')
    container = next((child for child in root if local(child) == 'channel'), root)
    title = lambda node: plain_text(next((''.join(child.itertext()) for child in node if local(child) == 'title'), ''))
    source = title(container) or 'Nachrichten'
    headlines = []
    for node in root.iter():
        if local(node) in ('item', 'entry'):
            headline = title(node)
            if headline and headline not in headlines:
                headlines.append(headline)
            if len(headlines) == 20:
                break
    if not headlines:
        raise ValueError('Feed enthält keine Schlagzeilen')
    return {'source': source[:100], 'headlines': headlines}


def fetch_feed(url):
    return parse_feed(download_feed(url))
