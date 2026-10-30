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
VERSION = 3
SOLO = re.compile(r'\b(?:solo\s+(?:cruis\w*|travel\w*|sail\w*|fare\w*)|single\s+(?:supplement|cabins?|occupancy|travell?ers?|cruis\w*)|singles?\s+cruis\w*|alleinreisend\w*|einzelkabine\w*|einzelzuschlag\w*|singlezuschlag\w*|suplemento\s+individual|cruceros?\s+para\s+(?:una|uno|solos?))\b', re.I)
OFFER = re.compile(r'\b(?:from|starting\s+at|only|per\s+person|pp|p\s*/\s*p|ab|desde|solo\s+fare|single\s+fare|no\s+single\s+supplement|waived\s+single\s+supplement|ohne\s+einzelzuschlag|kein\s+einzelzuschlag|single\s+supplement\s+(?:waived|free|reduced))\b', re.I)
PRICE = re.compile(r'(?<!\w)(?:£|€|\$|GBP\s*|EUR\s*|USD\s*)\s*\d{2,5}(?:[.,]\d{2})?(?!\d)', re.I)
DATE = re.compile(r'\b(?:\d{1,2}[\s./-]+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2})[\s,./-]+20\d{2}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[\s]+\d{1,2}(?:,?\s+20\d{2})?|20\d{2}-\d{2}-\d{2})\b', re.I)
NIGHTS = re.compile(r'\b\d{1,2}\s*(?:nights?|n[aä]chte|d[íi]as|days?)\b', re.I)
LINK_WORDS = re.compile(r'solo|single|alleinreis|einzel|singles|supplement|zuschlag|ofertas?|deals?|angebote|cruceros|kreuzfahrt', re.I)
SHIP = re.compile(r'\b(?:MSC|Costa|Norwegian|NCL|AIDA|Mein Schiff|Celebrity|Virgin|Ambience|Ambition|Queen Mary|Queen Victoria|Queen Anne|Explora|Ama[A-Z][a-z]+|MS\s+[A-Z][a-z]+)\s+[A-Z][\w-]+\b')


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


def fetch(url):
    request = urllib.request.Request(url, headers={
        'User-Agent': 'Cabins41Research/3.0 (public-page research)',
        'Accept': 'text/html,application/xhtml+xml'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                if 'html' not in response.headers.get('Content-Type', '').lower():
                    raise ValueError('Not an HTML page')
                return response.geturl(), response.read(800000).decode('utf-8', 'replace')
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


def extract_leads(text, url, source):
    """Conservative evidence windows, never infer that a generic pp price is a solo fare."""
    leads = []
    for match in list(SOLO.finditer(text))[:50]:
        # Tight windows reduce mixing an unrelated price with a solo claim.
        context = text[max(0, match.start()-180):min(len(text), match.end()+280)].strip()
        prices = list(dict.fromkeys(PRICE.findall(context)))[:4]
        dates = list(dict.fromkeys(DATE.findall(context)))[:4]
        durations = list(dict.fromkeys(NIGHTS.findall(context)))[:3]
        ships = list(dict.fromkeys(SHIP.findall(context)))[:3]
        # A solo offer can be worth investigating without a published price.
        has_offer = bool(OFFER.search(context) or prices or dates or durations)
        if not has_offer:
            continue
        evidence = context[:470]
        # No claim that price is solo: only a nearby advertised figure.
        lead = {
            'source_name': source['name'], 'source_id': source['id'],
            'seller_url': url, 'evidence': evidence,
            'prices_mentioned': prices, 'dates_mentioned': dates,
            'durations_mentioned': durations, 'ships_mentioned': ships,
            'solo_evidence': match.group(0),
            'classification': 'possible_solo_offer',
            'review_status': 'needs_manual_check',
            'warning': 'Prices and dates are nearby page text, NOT confirmed solo fares or sailings.'
        }
        leads.append(lead)
    # Avoid repeated site navigation text and overlapping snippets.
    unique = {}
    for lead in leads:
        key = (normal_url(lead['seller_url']), lead['solo_evidence'].lower(),
               tuple(lead['prices_mentioned']), tuple(lead['dates_mentioned']))
        unique.setdefault(key, lead)
    return list(unique.values())[:12]


def check(source):
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
        pages, offers = [], extract_leads(text, home, source)
        for candidate in candidates[:3]:
            try:
                url, content = fetch(candidate['url'])
                candidate_text, _ = page_data(content)
                page_snippets, page_count = snippets_from(candidate_text)
                pages.append({'url': url, 'label': candidate['label'],
                              'keyword_count': page_count, 'snippets': page_snippets})
                offers.extend(extract_leads(candidate_text, url, source))
            except Exception as error:
                pages.append({'url': candidate['url'], 'error': str(error)[:200]})
        return {'status': 'checked', 'url': home, 'lead_snippets': snippets,
                'lead_count': count, 'candidate_pages': pages,
                'candidate_links_found': len(candidates), 'possible_offers': offers,
                'note': 'Unverified leads only; no solo fare, date or availability confirmed.'}
    except Exception as error:
        return {'status': 'failed', 'error': str(error)[:300],
                'lead_snippets': [], 'lead_count': 0, 'candidate_pages': [],
                'possible_offers': []}


def atomic_json(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def save_review(ledger, date):
    """Rebuild the review output from the ledger after EVERY source."""
    leads, seen = [], set()
    for result in ledger['results'].values():
        for lead in result.get('possible_offers', []):
            # Deduplicate identical URL + supporting evidence; retain distinct sailings.
            key = (normal_url(lead['seller_url']),
                   tuple(lead['dates_mentioned']), tuple(lead['prices_mentioned']),
                   re.sub(r'\s+', ' ', lead['evidence'][:120]).lower())
            if key not in seen:
                seen.add(key)
                leads.append(lead)
    leads.sort(key=lambda x: (x['source_name'].lower(), x['seller_url']))
    checked = sum(v.get('status') == 'checked' for v in ledger['results'].values())
    failed = sum(v.get('status') == 'failed' for v in ledger['results'].values())
    review = {'date': date, 'sources_attempted': len(ledger['results']),
              'sources_checked': checked, 'sources_failed': failed,
              'possible_leads': len(leads), 'verified_offers': 0,
              'publication_status': 'REVIEW ONLY - DO NOT AUTO-PUBLISH', 'offers': leads}
    atomic_json(ROOT / 'data' / f'offers-{date}.json', review)
    lines = [f'# Cabins41 leads — {date}', '',
             f'{checked} sources checked; {failed} failed; {len(leads)} possible leads.',
             '', '**Not verified. Do not publish without checking the seller page.**', '']
    for i, lead in enumerate(leads, 1):
        lines += [f"## {i}. {lead['source_name']}",
                  f"Seller page: {lead['seller_url']}",
                  f"Solo wording: {lead['solo_evidence']}",
                  f"Prices mentioned (NOT verified solo prices): {', '.join(lead['prices_mentioned']) or 'None'}",
                  f"Dates mentioned: {', '.join(lead['dates_mentioned']) or 'None'}",
                  f"Duration mentioned: {', '.join(lead['durations_mentioned']) or 'None'}",
                  f"Ship mentioned: {', '.join(lead['ships_mentioned']) or 'None'}",
                  f"Evidence: {lead['evidence']}", '']
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
        atomic_json(output, ledger)
        review = save_review(ledger, date)
        print(f"{source['id']}/{len(SOURCES)} {source['name']}: {result['status']}, "
              f"{len(result['candidate_pages'])} candidate pages, "
              f"{len(result['possible_offers'])} possible leads; "
              f"{review['possible_leads']} unique review entries", flush=True)
        if not args.no_wait and not args.one:
            time.sleep(20)
    review = save_review(ledger, date)
    print(f"Finished: {review['sources_checked']} checked, {review['sources_failed']} failed, "
          f"{review['possible_leads']} leads for manual review. 0 verified offers.")


if __name__ == '__main__':
    main()
