"""Cabins41 source discovery: finds candidate pages, not verified cruise offers."""
import argparse
import datetime
import html
from html.parser import HTMLParser
import json
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).parent
SOURCES = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
VERSION = 2
KEYWORDS = re.compile(
    r'solo\s+cruis|single\s+supplement|single\s+cabins?|alleinreisend|'
    r'einzelkabine|ohne\s+einzelzuschlag|suplemento\s+individual|'
    r'cruceros?\s+para\s+(?:una|uno|solos?)|singles?\s+cruis', re.I)
LINK_WORDS = re.compile(
    r'solo|single|alleinreis|einzel|singles|supplement|zuschlag|'
    r'ofertas?|deals?|angebote|cruceros', re.I)

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.links = []
        self.hidden = 0
        self.href = None
        self.anchor = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style', 'noscript'):
            self.hidden += 1
        if tag == 'a' and not self.hidden:
            self.href = attrs.get('href')
            self.anchor = []

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)
            if self.href is not None:
                self.anchor.append(data)

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self.hidden:
            self.hidden -= 1
        if tag == 'a' and self.href is not None:
            self.links.append((self.href, ' '.join(self.anchor)))
            self.href = None
            self.anchor = []


def fetch(url):
    request = urllib.request.Request(url, headers={
        'User-Agent': 'Cabins41Research/2.0 (public-page research)',
        'Accept': 'text/html,application/xhtml+xml'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                kind = response.headers.get('Content-Type', '')
                if 'html' not in kind.lower():
                    raise ValueError('Not an HTML page')
                return response.geturl(), response.read(800000).decode('utf-8', 'replace')
        except urllib.error.HTTPError as error:
            if error.code in (401, 403, 404, 410):
                raise  # Do not retry denied or missing pages
            if error.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (TimeoutError, urllib.error.URLError):
            if attempt == 2:
                raise
        time.sleep(30)


def parse_page(url, raw):
    parser = PageParser()
    parser.feed(raw)
    text = re.sub(r'\s+', ' ', html.unescape(' '.join(parser.text))).strip()
    matches = list(KEYWORDS.finditer(text))
    snippets = list(dict.fromkeys(
        text[max(0, m.start()-90):m.end()+160].strip() for m in matches[:8]))
    return snippets, len(matches), parser.links


def check(source):
    try:
        home, raw = fetch(source['url'])
        snippets, count, links = parse_page(home, raw)
        domain = urllib.parse.urlsplit(home).hostname or ''
        candidates = []
        seen = {home.rstrip('/')}
        for href, label in links:
            absolute = urllib.parse.urljoin(home, href).split('#')[0]
            parts = urllib.parse.urlsplit(absolute)
            if parts.scheme not in ('http', 'https') or parts.hostname != domain:
                continue
            if not LINK_WORDS.search(label + ' ' + parts.path):
                continue
            if absolute.rstrip('/') in seen:
                continue
            seen.add(absolute.rstrip('/'))
            candidates.append({'url': absolute, 'label': label.strip()[:140]})
        pages = []
        for candidate in candidates[:3]:
            try:
                url, content = fetch(candidate['url'])
                page_snippets, page_count, _ = parse_page(url, content)
                pages.append({'url': url, 'label': candidate['label'],
                              'keyword_count': page_count, 'snippets': page_snippets})
            except Exception as error:
                pages.append({'url': candidate['url'], 'error': str(error)[:200]})
        return {'status': 'checked', 'url': home, 'lead_snippets': snippets,
                'lead_count': count, 'candidate_pages': pages,
                'candidate_links_found': len(candidates),
                'note': 'Candidate pages only; sailing dates, solo prices and availability NOT verified.'}
    except Exception as error:
        return {'status': 'failed', 'error': str(error)[:300],
                'lead_snippets': [], 'lead_count': 0, 'candidate_pages': []}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date')
    parser.add_argument('--no-wait', action='store_true')
    parser.add_argument('--one', type=int)
    args = parser.parse_args()
    date = args.date or datetime.datetime.now(ZoneInfo('Europe/London')).date().isoformat()
    output = ROOT / 'data' / f'holding-{date}.json'
    output.parent.mkdir(exist_ok=True)
    ledger = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {
        'date': date, 'results': {}, 'description': 'Candidate discovery; not verified offers'}
    for source in SOURCES:
        if args.one and source['id'] != args.one:
            continue
        key = str(source['id'])
        previous = ledger['results'].get(key, {})
        if previous.get('status') == 'checked' and previous.get('checker_version') == VERSION:
            continue
        result = check(source)
        result.update({'source_name': source['name'], 'checker_version': VERSION,
                       'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()})
        ledger['results'][key] = result
        output.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"{source['id']}/{len(SOURCES)} {source['name']}: {result['status']}, "
              f"{len(result['candidate_pages'])} candidate pages", flush=True)
        if not args.no_wait and not args.one:
            time.sleep(20)
    checked = sum(v.get('status') == 'checked' for v in ledger['results'].values())
    failed = sum(v.get('status') == 'failed' for v in ledger['results'].values())
    print(f'Finished: {checked} checked, {failed} failed. No offers verified.')

if __name__ == '__main__':
    main()
