"""Public Steam Workshop browsing; all downloaded media comes through Steam."""
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen
from store import DATA

APP_ID = 3474900


def request(url, data=None, limit=8_000_000):
    req = Request(url, data=data, headers={'User-Agent': 'DesktopCast/1.0', 'Accept-Language': 'en'})
    with urlopen(req, timeout=25) as response:
        result = response.read(limit + 1)
        if len(result) > limit:
            raise ValueError('Steam response was larger than expected.')
        return result


class SteamPage(HTMLParser):
    def __init__(self):
        super().__init__(); self.inside = False; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('id') == 'valve-ssr-data': self.inside = True
    def handle_endtag(self, tag):
        if tag == 'script': self.inside = False
    def handle_data(self, data):
        if self.inside: self.parts.append(data)


def find_results(value):
    if isinstance(value, dict):
        if 'results' in value and 'total_count' in value and isinstance(value['results'], list):
            return value
        for child in value.values():
            found = find_results(child)
            if found is not None: return found
    elif isinstance(value, list):
        for child in value:
            found = find_results(child)
            if found is not None: return found
    elif isinstance(value, str) and value.startswith(('{', '[')):
        try: return find_results(json.loads(value))
        except (ValueError, RecursionError): pass
    return None


def parse_page(html):
    parser = SteamPage(); parser.feed(html)
    if not parser.parts: raise ValueError('Steam returned an unavailable page. Try again or open the Workshop in Steam.')
    result = find_results(json.loads(''.join(parser.parts)))
    if result is None: raise ValueError('Steam changed its Workshop page format. Open the item in Steam and import its download.')
    result['results'] = [normalize(item) for item in result['results'] if int(item.get('consumer_appid', 0)) == APP_ID]
    return result


def normalize(item):
    return {'id': str(item.get('publishedfileid', '')), 'title': item.get('title', 'Untitled'),
            'preview': item.get('preview_url', ''), 'bytes': int(item.get('file_size', 0)),
            'description': item.get('short_description', item.get('description', ''))}


def item_id(text):
    text = text.strip()
    if re.fullmatch(r'\d{1,20}', text): return text
    parsed = urlparse(text)
    if parsed.scheme == 'https' and parsed.hostname == 'steamcommunity.com':
        candidate = parse_qs(parsed.query).get('id', [''])[0]
        if re.fullmatch(r'\d{1,20}', candidate): return candidate
    return None


def details(identity):
    if not re.fullmatch(r'\d{1,20}', str(identity)): raise ValueError('Invalid Workshop item ID.')
    data = urlencode({'itemcount': 1, 'publishedfileids[0]': identity}).encode()
    result = json.loads(request('https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/', data))
    item = result['response']['publishedfiledetails'][0]
    if item.get('result') != 1: raise ValueError('This Workshop item is unavailable or private.')
    if int(item.get('consumer_app_id', 0)) != APP_ID: raise ValueError('Choose an animaEngine Workshop item.')
    return normalize(item)


def browse(search='', sort='trend', page=1):
    identity = item_id(search)
    if identity:
        return {'results': [details(identity)], 'current_page': 1, 'total_pages': 1, 'total_count': 1}
    query = urlencode({'appid': APP_ID, 'searchtext': search, 'browsesort': sort,
                       'section': 'readytouseitems', 'p': max(1, page), 'numperpage': 30, 'l': 'english'})
    return parse_page(request('https://steamcommunity.com/workshop/browse/?' + query).decode())


def thumbnail(url):
    host = urlparse(url).hostname or ''
    if not (host.endswith('.steamusercontent.com') or host.endswith('.steamstatic.com')): return None
    folder = DATA / 'workshop-thumbnails'; folder.mkdir(parents=True, exist_ok=True)
    path = folder / (hashlib.sha256(url.encode()).hexdigest() + '.jpg')
    if not path.exists():
        content = request(url, limit=4_000_000)
        temporary = path.with_suffix('.part'); temporary.write_bytes(content); temporary.replace(path)
    return str(path)
