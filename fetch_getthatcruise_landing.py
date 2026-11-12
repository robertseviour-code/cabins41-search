"""Fetch the public Get That Cruise solo-fares page and export review-only CSV.

The landing page shows 60 of the catalogue's sailings. This does not claim
to retrieve the full finder or verify cabin grade / current availability.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from export_getthatcruise import main as _unused
from getthatcruise_cards import visible_cards
import csv
import sys

URL = "https://www.getthatcruise.co.uk/cruises/solo-fares"
OUT = Path("getthatcruise_landing_review.csv")


def run():
    request = Request(URL, headers={"User-Agent": "Mozilla/5.0 (compatible; Cabins41Review/1.0)"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    # The public page contains HTML markup; strip tags while retaining spaces.
    # html.parser handles entity decoding, unlike naive regex stripping.
    from html.parser import HTMLParser
    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
        def handle_data(self, data):
            self.parts.append(data)
        def handle_starttag(self, tag, attrs):
            if tag in {"p", "h2", "h3", "div", "span", "li", "br"}:
                self.parts.append(" ")
    extractor = TextExtractor()
    extractor.feed(html)
    rows = visible_cards(" ".join(extractor.parts))
    fields = ["ship", "date_displayed", "solo_gbp", "sharing_pp_gbp",
              "calculated_supplement", "preliminary_status", "verification"]
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Extracted {len(rows)} visible cards; output {OUT}")
    if not rows:
        sys.exit("No cards parsed; inspect page structure before trusting results")


if __name__ == "__main__":
    run()
