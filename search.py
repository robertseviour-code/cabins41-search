"""Cabins41 daily public-page research. Leads are NOT independently verified fares.

Keeps the original command-line options and per-source holding-file updates.
Produces data/offers-YYYY-MM-DD.json and data/offers-YYYY-MM-DD.md for review.
"""
import argparse
import datetime
import html
from html.parser import HTMLParser
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).parent
SOURCES = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
VERSION = 19  # Daily 31 October full-search trigger.  # Full-search trigger comment.
SOLO = re.compile(r'\b(?:solo\s+(?:cruis\w*|travel\w*|sail\w*|fare\w*|offer\w*|deal\w*|discount\w*|cabin\w*|price\w*|rate\w*)|single\s+(?:supplement|cabins?|occupancy|travell?ers?|cruis\w*)|singles?\s+cruis\w*|alleinreisend\w*|einzelkabine\w*|einzelzuschlag\w*|singlezuschlag\w*|suplemento\s+individual|cruceros?\s+para\s+(?:una|uno|solos?))\b', re.I)
CLEAR_SOLO_OFFER = re.compile(r'\b(?:zuschlag\s+nur\s+\d{1,3}\s*%|solo\s+(?:(?:cruise\s+)?(?:offer|deal|discount|fare|price|rate)s?|cruis\w*\s+(?:offer|deal|discount|fare|price|rate)s?)|(?:offer|deal|discount|fare|price|rate)s?\s+for\s+(?:solo|single)\s+(?:cruis\w*|travell?ers?|occupan\w*)|(?:no|without|waived|free|reduced)\s+single\s+supplement|single\s+supplement\s+(?:waived|free|reduced|from|of|\d{1,3}\s*%)|single\s+supplement.{0,35}(?:\d{1,3}\s*%|[£€$]\s*\d)|alleinreisenden[- ]angebot|einzelkabinenzuschlag.{0,35}\d|einzelzuschlag.{0,35}\d|singlezuschlag.{0,35}\d|suplemento\s+individual.{0,35}\d|oferta\s+para\s+(?:viajeros?\s+)?solos?)', re.I)
OFFER = re.compile(r'\b(?:from|starting\s+at|only|per\s+person|pp|p\s*/\s*p|ab|desde|solo\s+fare|single\s+fare|no\s+single\s+supplement|waived\s+single\s+supplement|ohne\s+einzelzuschlag|kein\s+einzelzuschlag|single\s+supplement\s+(?:waived|free|reduced))\b', re.I)
PRICE = re.compile(r'(?<!\w)(?:£|€|\$|GBP\s*|EUR\s*|USD\s*)\s*\d{2,5}(?:[.,]\d{2})?(?!\d)', re.I)
DATE = re.compile(r'\b(?:\d{1,2}[\s./-]+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2})[\s,./-]+20\d{2}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[\s]+\d{1,2}(?:,?\s+20\d{2})?|20\d{2}-\d{2}-\d{2})\b', re.I)
NIGHTS = re.compile(r'\b\d{1,2}\s*(?:nights?|n[aä]chte|d[íi]as|days?)\b', re.I)
LINK_WORDS = re.compile(r'solo|single|alleinreis|einzel|singles|supplement|zuschlag|ofertas?|deals?|angebote|cruceros|kreuzfahrt', re.I)
SHIP = re.compile(r'\b(?:(?i:MSC|Costa|Norwegian|NCL|Celebrity|Virgin|Explora|Azamara|Ambassador|Fred\.?\s+Olsen|P&O|Princess|Regent|Royal Caribbean|Holland America|Seabourn|Silversea|Cunard|AIDA|Mein Schiff|Carnival|Disney|Oceania|TUI)\s+(?-i:(?:[A-Z][a-z0-9-]+|[A-Z]{2,})(?:\s+(?:[A-Z][a-z0-9-]+|[A-Z]{2,}|[0-9]))?)|Queen\s+(?:Mary\s*2|Victoria|Anne|Elizabeth)|(?:AIDA(?:bella|blu|cosma|diva|luna|mar|nova|perla|prima|sol|stella|vita)|Ambience|Ambition|Balmoral|Bolette|Borealis|Armonia|Bellissima|Divina|Euribia|Fantasia|Fascinosa|Grandiosa|Lirica|Magnifica|Meraviglia|Musica|Opera|Orchestra|Poesia|Preziosa|Seascape|Seashore|Seaside|Sinfonia|Splendida|Toscana|Smeralda|Fascinosa|Diadema|Favolosa|Deliziosa|Pacifica|Serena|Breakaway|Bliss|Encore|Jade|Prima|Onward|Pursuit))\b', re.I)
SHIP_GENERIC = {'cruise', 'cruises', 'kreuzfahrt', 'kreuzfahrten', 'offer', 'offers', 'deal', 'deals', 'fare', 'fares', 'waived', 'solo', 'explore', 'journeys', 'voyages', 'multiple', 'from', 'hosts', 'experience', 'experiences', 'all-inclusive', 'date', 'dates', 'sailing', 'sailings', 'cruising', 'holidays', 'holiday', 'voyage', 'voyages', 'fjords', 'destinations', 'line', 'lines', 'departing', 'mediterranean', 'bahamas', 'caribbean', 'australasia', 'sanctuary', 'collection', 'premier', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec', 'dez', 'january', 'february', 'march', 'april', 'june', 'july', 'august', 'september', 'october', 'november', 'december'}
CABINS41_URL = 'https://lovely-paletas-545789.netlify.app/'


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.hidden = [], [], 0
        self.href, self.anchor = None, []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.hidden += 1
        if tag == 'a' and not self.hidden:
            self.href, self.anchor = attrs.get('href'), []

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)
            if self.href is not None:
                self.anchor.append(data)

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg') and self.hidden:
            self.hidden -= 1
        if tag == 'a' and self.href is not None:
            self.links.append((self.href, ' '.join(self.anchor)))
            self.href, self.anchor = None, []


def fetch(url, max_bytes=800000):
    request = urllib.request.Request(url, headers={
        'User-Agent': 'Cabins41Research/3.0 (public-page research)',
        'Accept': 'text/html,application/xhtml+xml'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                if 'html' not in response.headers.get('Content-Type', '').lower():
                    raise ValueError('Not an HTML page')
                return response.geturl(), response.read(max_bytes).decode('utf-8', 'replace')
        except urllib.error.HTTPError as error:
            if error.code in (401, 403, 404, 410) or error.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (TimeoutError, urllib.error.URLError):
            if attempt == 2:
                raise
        time.sleep(30)


def page_data(raw):
    parser = PageParser()
    parser.feed(raw)
    text = re.sub(r'\s+', ' ', html.unescape(' '.join(parser.text))).strip()
    return text, parser.links


def snippets_from(text):
    matches = list(SOLO.finditer(text))
    snippets = list(dict.fromkeys(text[max(0, m.start()-90):m.end()+160].strip() for m in matches[:8]))
    return snippets, len(matches)


def normal_url(url):
    parts = urllib.parse.urlsplit(url)
    # Tracking parameters are not useful for deduplication.
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query = [(k, v) for k, v in query if not k.lower().startswith(('utm_', 'fbclid', 'gclid'))]
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/') or '/', urllib.parse.urlencode(query), ''))


def normalize_ship(value):
    value = re.sub(r'\s+', ' ', value).strip(' ,.;:-')
    value = re.sub(r'^AIDA(?=[a-z])', '', value)
    value = re.sub(r'^(?:MSC|Costa|Norwegian|NCL|Celebrity|Virgin|Explora|Azamara|Ambassador|Fred\.?\s+Olsen|P&O|Princess|Regent|Royal Caribbean|Holland America|Seabourn|Silversea|Cunard|AIDA|Carnival|Disney|Oceania|TUI)\s+', '', value, flags=re.I)
    return re.sub(r'[^a-z0-9]+', ' ', value.casefold()).strip()


def normalize_date(value):
    value = value.strip().replace(',', '')
    value = re.sub(r'(?<=[A-Za-z])\.', '', value)
    value = re.sub(r'^(\d{1,2})\.\s+', r'\1 ', value)
    value = re.sub(r'\bSept\b', 'Sep', value, flags=re.I)
    value = re.sub(r'\bOkt\b', 'Oct', value, flags=re.I)
    value = re.sub(r'\bMärz\b', 'Mar', value, flags=re.I)
    value = re.sub(r'\bMai\b', 'May', value, flags=re.I)
    value = re.sub(r'\bJuni\b', 'Jun', value, flags=re.I)
    value = re.sub(r'\bJuli\b', 'Jul', value, flags=re.I)
    value = re.sub(r'\bDez\b', 'Dec', value, flags=re.I)
    formats = ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y',
               '%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y')
    for fmt in formats:
        try:
            return datetime.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def named_sailings(text):
    """Find a named ship and a nearby departure date on one page."""
    ship_spans = []
    for match in SHIP.finditer(text):
        name = re.sub(r'\s+', ' ', match.group(0)).strip()
        words = name.split()
        while len(words) > 1 and words[-1].strip('.,').casefold() in SHIP_GENERIC:
            words.pop()
        name = ' '.join(words)
        if re.search(r'\b(?:cruise|cruises|line|lines)\b', name, re.I):
            continue
        if name.casefold() in {'msc', 'costa', 'norwegian', 'ncl', 'celebrity', 'virgin',
                               'virgin voyages', 'explora', 'explora journeys', 'azamara', 'ambassador', 'princess', 'regent', 'regent seven seas',
                               'royal caribbean', 'holland america', 'seabourn', 'silversea', 'silversea voyages',
                               'cunard', 'aida', 'carnival', 'disney', 'oceania', 'tui'}:
            continue
        if re.search(r'\bCosta\s+Rica\b', name, re.I):
            continue
        ship_spans.append((match.start(), match.start() + len(name), name))
    for match in re.finditer(r'\b(?:Ambience|Ambition|Balmoral|Bolette|Borealis|Sinfonia|Getaway)\b', text, re.I):
        ship_spans.append((match.start(), match.end(), match.group(0)))
    date_spans = []
    for match in DATE.finditer(text):
        iso_date = normalize_date(match.group(0))
        if iso_date:
            before_date = text[max(0, match.start()-45):match.start()].casefold()
            if any(marker in before_date for marker in
                   ('published', 'updated', 'posted', 'last modified', 'says', 'comments', 'commented',
                    'veröffentlicht', 'publicado', 'actualizado')):
                continue
            date_spans.append((match.start(), match.end(), iso_date, match.group(0)))
    results = {}
    for start, end, ship in ship_spans:
        nearby = [d for d in date_spans if min(abs(start - d[1]), abs(d[0] - end)) <= 500]
        if not nearby:
            continue
        date_start, date_end, iso_date, raw_date = min(
            nearby, key=lambda d: abs(((start + end) // 2) - ((d[0] + d[1]) // 2)))
        key = (normalize_ship(ship), iso_date)
        results.setdefault(key, {'ship': ship, 'departure_date': iso_date,
                                 'date_text': raw_date, 'ship_start': start,
                                 'date_start': date_start})
    return list(results.values())


def extract_leads(text, url, source, existing, dedupe_ready):
    """Find clear solo-offer wording and dated sailings on the same page."""
    solo_matches = list(CLEAR_SOLO_OFFER.finditer(text))[:100]
    solo_page = bool(re.search(r'solo|single|singles|alleinreis|einzel', url, re.I))
    if not solo_page:
        solo_matches = [m for m in solo_matches
                        if m.group(0).strip().casefold() not in ('solo cruise deal', 'solo cruise deals', 'solo cruises deal', 'solo cruises deals', 'reduced single supplement', 'reduced single supplement cruise', 'reduced single supplement cruises')]
    sailings = named_sailings(text)
    if not solo_matches or not sailings:
        return [], []
    leads, duplicates = [], []
    today = datetime.datetime.now(ZoneInfo('Europe/London')).date()
    for sailing in sailings:
        if datetime.date.fromisoformat(sailing['departure_date']) <= today:
            continue
        ship_at = sailing['ship_start']
        date_at = sailing['date_start']
        sailing_at = (ship_at + date_at) // 2
        match = min(solo_matches, key=lambda m: abs(m.start() - sailing_at))
        if abs(match.start() - sailing_at) > 500:
            continue
        evidence_start = max(0, min(ship_at, date_at) - 280)
        evidence_end = min(len(text), max(ship_at, date_at) + 500)
        context = text[evidence_start:evidence_end].strip()
        solo_context = text[max(0, match.start()-100):min(len(text), match.end()+220)].strip()
        key = (normalize_ship(sailing['ship']), sailing['departure_date'])
        lead = {
            'source_name': source['name'], 'source_id': source['id'],
            'seller_url': url, 'ship': sailing['ship'],
            'departure_date': sailing['departure_date'],
            'solo_evidence': match.group(0), 'evidence': (solo_context + ' | Sailing: ' + context)[:900],
            'prices_mentioned': list(dict.fromkeys(PRICE.findall(context + ' ' + solo_context)))[:4],
            'durations_mentioned': list(dict.fromkeys(NIGHTS.findall(context + ' ' + solo_context)))[:3],
            'classification': 'qualified_for_manual_review',
            'review_status': 'needs_manual_check',
            'warning': 'Check the seller page and solo price before publishing.'
        }
        if not dedupe_ready:
            lead['review_status'] = 'duplicate_check_needed'
            lead['warning'] = 'Cabins41 listings could not be checked. Compare this ship and date with current listings before use.'
            leads.append(lead)
        elif key in existing:
            duplicates.append({'ship': sailing['ship'],
                               'departure_date': sailing['departure_date'],
                               'seller_url': url})
        else:
            leads.append(lead)
    unique = {}
    for lead in leads:
        key = (normalize_ship(lead['ship']), lead['departure_date'])
        unique.setdefault(key, lead)
    duplicate_unique = {}
    for item in duplicates:
        key = (normalize_ship(item['ship']), item['departure_date'])
        duplicate_unique.setdefault(key, item)
    return list(unique.values()), list(duplicate_unique.values())


def load_existing_sailings(date):
    """Cache today's public Cabins41 listing keys; fail closed if none can be read."""
    run_id = os.environ.get('GITHUB_RUN_ID', 'local')
    cache = ROOT / 'data' / f'cabins41-listings-{date}-{run_id}.json'
    if cache.exists():
        try:
            data = json.loads(cache.read_text(encoding='utf-8'))
            keys = {(normalize_ship(x['ship']), x['departure_date']) for x in data.get('sailings', [])}
            if keys:
                return keys, {'status': 'loaded', 'url': data.get('url', CABINS41_URL),
                              'count': len(keys), 'error': ''}
        except Exception:
            pass
    try:
        url, raw = fetch(os.environ.get('CABINS41_LISTINGS_URL', CABINS41_URL), max_bytes=6000000)
        text, _ = page_data(raw)
        sailings = named_sailings(text)
        keys = {(normalize_ship(x['ship']), x['departure_date']) for x in sailings}
        if not keys:
            raise ValueError('No ship/departure-date pairs could be read from Cabins41 listings')
        atomic_json(cache, {'date': date, 'url': url, 'sailings': sailings,
                            'fetched_at': datetime.datetime.now(datetime.timezone.utc).isoformat()})
        return keys, {'status': 'loaded', 'url': url, 'count': len(keys), 'error': ''}
    except Exception as error:
        return set(), {'status': 'unavailable', 'url': CABINS41_URL,
                       'count': 0, 'error': str(error)[:250]}


def is_blocked(error):
    return isinstance(error, urllib.error.HTTPError) and error.code in (401, 403, 429)


def check(source, existing, dedupe_ready):
    try:
        home, raw = fetch(source['url'])
        text, links = page_data(raw)
        snippets, count = snippets_from(text)
        domain = urllib.parse.urlsplit(home).hostname or ''
        candidates, seen = [], {normal_url(home)}
        for href, label in links:
            absolute = urllib.parse.urljoin(home, href).split('#')[0]
            parts = urllib.parse.urlsplit(absolute)
            if parts.scheme not in ('http', 'https') or parts.hostname != domain:
                continue
            if not LINK_WORDS.search(label + ' ' + parts.path):
                continue
            key = normal_url(absolute)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({'url': absolute, 'label': label.strip()[:140]})
        # Rank solo-specific pages ahead of general deals; still cap requests.
        candidates.sort(key=lambda c: (0 if SOLO.search(c['label'] + ' ' + c['url']) else 1))
        pages, offers, duplicates, blocked_pages = [], [], [], []
        found, repeated = extract_leads(text, home, source, existing, dedupe_ready)
        offers.extend(found)
        duplicates.extend(repeated)
        for candidate in candidates[:3]:
            try:
                url, content = fetch(candidate['url'])
                candidate_text, _ = page_data(content)
                page_snippets, page_count = snippets_from(candidate_text)
                pages.append({'url': url, 'label': candidate['label'],
                              'keyword_count': page_count, 'snippets': page_snippets})
                found, repeated = extract_leads(candidate_text, url, source, existing, dedupe_ready)
                offers.extend(found)
                duplicates.extend(repeated)
            except Exception as error:
                page_error = {'url': candidate['url'], 'error': str(error)[:200]}
                if is_blocked(error):
                    page_error['status'] = 'blocked'
                    blocked_pages.append({'source_name': source['name'], 'url': candidate['url'],
                                          'reason': str(error)[:200]})
                pages.append(page_error)
        unique_offers = {}
        for offer in offers:
            key = (normalize_ship(offer['ship']), offer['departure_date'])
            unique_offers.setdefault(key, offer)
        return {'status': 'checked', 'url': home, 'lead_snippets': snippets,
                'lead_count': count, 'candidate_pages': pages,
                'candidate_links_found': len(candidates), 'possible_offers': list(unique_offers.values()),
                'duplicates_excluded': duplicates, 'blocked_candidate_pages': blocked_pages,
                'note': 'Candidates require explicit solo offer wording, ship and departure date; prices still need manual verification.'}
    except Exception as error:
        return {'status': 'blocked' if is_blocked(error) else 'failed',
                'error': str(error)[:300], 'lead_snippets': [], 'lead_count': 0,
                'candidate_pages': [], 'possible_offers': [], 'duplicates_excluded': [],
                'blocked_candidate_pages': []}


def atomic_json(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def save_review(ledger, date, dedupe_info):
    leads, seen, duplicate_map = [], set(), {}
    for result in ledger['results'].values():
        for lead in result.get('possible_offers', []):
            # Ignore legacy keyword-only leads from earlier checker versions.
            if not lead.get('ship') or not lead.get('departure_date'):
                continue
            key = (normalize_ship(lead['ship']), lead['departure_date'])
            if key not in seen:
                seen.add(key)
                leads.append(lead)
            else:
                duplicate_map.setdefault(key, {'ship': lead['ship'],
                                               'departure_date': lead['departure_date'],
                                               'seller_url': lead['seller_url']})
        for item in result.get('duplicates_excluded', []):
            key = (normalize_ship(item['ship']), item['departure_date'])
            duplicate_map.setdefault(key, item)
    leads.sort(key=lambda x: (x['departure_date'], normalize_ship(x['ship'])))
    checked = sum(v.get('status') == 'checked' for v in ledger['results'].values())
    blocked = [(v.get('source_name', 'Unknown source'), v.get('error', 'blocked'))
               for v in ledger['results'].values() if v.get('status') == 'blocked']
    failed = [(v.get('source_name', 'Unknown source'), v.get('error', 'failed'))
              for v in ledger['results'].values() if v.get('status') == 'failed']
    duplicate_keys = set(duplicate_map)
    duplicates = list(duplicate_map.values())
    blocked_pages = []
    page_seen = set()
    for result in ledger['results'].values():
        for page in result.get('blocked_candidate_pages', []):
            key = (page['source_name'], page['url'])
            if key not in page_seen:
                page_seen.add(key)
                blocked_pages.append(page)
    review = {
        'date': date, 'sources_attempted': len(ledger['results']),
        'sources_checked': checked, 'sources_blocked': len(blocked),
        'sources_failed': len(failed), 'qualified_candidates': len(leads) if dedupe_info.get('status') == 'loaded' else 0,
        'candidate_sailings': len(leads),
        'duplicate_check_required': dedupe_info.get('status') != 'loaded',
        'duplicate_sailings_excluded': len(duplicate_keys),
        'existing_listings_status': dedupe_info,
        'verified_offers': 0,
        'publication_status': 'REVIEW ONLY - DO NOT AUTO-PUBLISH',
        'offers': leads,
        'blocked_sources': [{'source': name, 'reason': reason} for name, reason in blocked],
        'blocked_candidate_pages': blocked_pages,
        'failed_sources': [{'source': name, 'reason': reason} for name, reason in failed]
    }
    atomic_json(ROOT / 'data' / f'offers-{date}.json', review)
    lines = [
        f'# Cabins41 leads — {date}', '',
        f'Sources checked: {checked}; blocked: {len(blocked)}; other failures: {len(failed)}.',
        f'Candidates for manual review: {len(leads)}; duplicates excluded: {len(duplicate_keys)}; verified offers: 0.',
        f"Cabins41 listing check: {dedupe_info.get('status')} ({dedupe_info.get('count', 0)} sailings).",
        (f"Listing check detail: {dedupe_info['error']}" if dedupe_info.get('error') else ''), '',
        '**A green workflow means the checks completed; it does not mean useful offers were found.**',
        '**Not verified. Do not publish without checking the seller page.**', ''
    ]
    lines += ['## Blocked sources', '']
    lines += [f'- {name}: {reason}' for name, reason in blocked] or ['- None']
    lines += ['', '## Candidate pages blocked', '']
    lines += [f"- {x['source_name']}: {x['url']} — {x['reason']}" for x in blocked_pages] or ['- None']
    lines += ['', '## Other failed sources', '']
    lines += [f'- {name}: {reason}' for name, reason in failed] or ['- None']
    lines += ['', '## Candidates for manual review', '']
    for i, lead in enumerate(leads, 1):
        lines += [
            f"### {i}. {lead['ship']} — {lead['departure_date']}",
            f"Source: {lead['source_name']} ({lead['seller_url']})",
            f"Solo-offer wording: {lead['solo_evidence']}",
            f"Review status: {lead['review_status']}",
            f"Prices mentioned (not verified as solo prices): {', '.join(lead['prices_mentioned']) or 'None'}",
            f"Evidence: {lead['evidence']}", ''
        ]
    lines += ['', '## Duplicate sailings excluded', '']
    lines += [f"- {x['ship']} — {x['departure_date']}" for x in duplicates] or ['- None']
    (ROOT / 'data' / f'offers-{date}.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return review


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date')
    parser.add_argument('--no-wait', action='store_true')
    parser.add_argument('--one', type=int)
    args = parser.parse_args()
    date = args.date or datetime.datetime.now(ZoneInfo('Europe/London')).date().isoformat()
    output = ROOT / 'data' / f'holding-{date}.json'
    output.parent.mkdir(exist_ok=True)
    existing, dedupe_info = load_existing_sailings(date)
    dedupe_ready = dedupe_info.get('status') == 'loaded'
    ledger = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {
        'date': date, 'results': {}, 'description': 'Qualified solo offer candidates; not verified offers'}
    active_ids = {str(source['id']) for source in SOURCES}
    ledger['results'] = {key: value for key, value in ledger['results'].items() if key in active_ids}
    for source in SOURCES:
        if args.one and source['id'] != args.one:
            continue
        key = str(source['id'])
        previous = ledger['results'].get(key, {})
        if os.environ.get('CABINS41_FORCE_RECHECK') != '1' and previous.get('status') in ('checked', 'blocked', 'failed') and previous.get('checker_version') == VERSION:
            continue
        result = check(source, existing, dedupe_ready)
        result.update({'source_name': source['name'], 'checker_version': VERSION,
                       'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()})
        ledger['results'][key] = result
        atomic_json(output, ledger)
        review = save_review(ledger, date, dedupe_info)
        print(f"{source['id']}/{len(SOURCES)} {source['name']}: {result['status']}, "
              f"{len(result['candidate_pages'])} candidate pages, "
              f"{len(result['possible_offers'])} possible leads; "
              f"{review['qualified_candidates']} unique review entries", flush=True)
        if not args.no_wait and not args.one:
            time.sleep(20)
    review = save_review(ledger, date, dedupe_info)
    print(f"Finished: {review['sources_checked']} checked, {review['sources_blocked']} blocked, "
          f"{review['sources_failed']} other failures, {review['qualified_candidates']} qualified candidates; "
          f"{review['duplicate_sailings_excluded']} duplicates excluded; 0 verified offers.")


if __name__ == '__main__':
    main()
