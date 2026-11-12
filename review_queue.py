"""Generate a conservative review queue from a Cabins41 offers JSON file.

No fare is automatically verified or published. Supply the offers JSON from a
completed run; the script outputs a CSV suitable for manual review.
Usage: python review_queue.py data/offers-2026-11-12.json review.csv
"""
import argparse
import csv
import json
import re
from pathlib import Path

ZERO = re.compile(r"(?i)\b(?:no|zero|without|waived|free)\s+single\s+supplement\b|\b(?:ohne|kein)\s+einzelzuschlag\b|\b(?:zuschlag\s+nur|einzelzuschlag|single\s+supplement)\s*(?:of|is|:)?\s*0\s*%")
PERCENT = re.compile(r"(?i)\b(?:zuschlag\s+nur|einzelzuschlag|single\s+supplement)\s*(?:of|is|:)?\s*(\d{1,3})\s*%")
FIELDS = ["ship", "departure_date", "source_name", "seller_url", "solo_evidence",
          "advertised_supplement", "review_priority", "review_status", "warning"]


def row_for(lead):
    # Use only the short matched offer wording. The broader evidence field can
    # contain prices or percentages from unrelated sailings.
    wording = str(lead.get("solo_evidence") or "")
    if ZERO.search(wording):
        claimed, priority = "0%", "explicit_zero_claim"
    else:
        m = PERCENT.search(wording)
        claimed = f"{m.group(1)}%" if m and int(m.group(1)) <= 100 else ""
        priority = "explicit_percent_claim" if claimed else "solo_fare_only"
    return {
        "ship": lead.get("ship", ""), "departure_date": lead.get("departure_date", ""),
        "source_name": lead.get("source_name", ""),
        "seller_url": lead.get("seller_url", ""),
        "solo_evidence": wording,
        "advertised_supplement": claimed,
        "review_priority": priority,
        "review_status": "needs_manual_check",
        "warning": "Verify same ship, date, cabin, currency, fare basis and availability on seller site",
    }


def build_rows(data, source=None):
    leads = data.get("offers", [])
    rows = [row_for(x) for x in leads if not source or source.casefold() in
            str(x.get("source_name", "")).casefold()]
    priority = {"explicit_zero_claim": 0, "explicit_percent_claim": 1, "solo_fare_only": 2}
    return sorted(rows, key=lambda x: (priority[x["review_priority"]],
                                       x["departure_date"], x["ship"]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_json", type=Path)
    p.add_argument("output_csv", type=Path)
    p.add_argument("--source", default=None, help="Filter supplier, e.g. 'Get That Cruise'")
    args = p.parse_args()
    data = json.loads(args.input_json.read_text(encoding="utf-8"))
    rows = build_rows(data, args.source)
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} unverified leads exported; zero independently verified offers")


if __name__ == "__main__":
    main()
