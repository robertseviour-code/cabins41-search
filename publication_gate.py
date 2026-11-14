#!/usr/bin/env python3
"""Fail-closed Cabins41 publication gate. No network calls or deployment."""
import argparse
import datetime as dt
import json
import pathlib
import re
from urllib.parse import urlsplit

REQUIRED = ("ship", "departure_date", "seller_url", "verified_solo_fare",
            "verification_date", "verification_evidence", "verification_method")
METHODS = {"seller_checkout", "seller_written_confirmation", "same_grade_fare_comparison"}

def normal_ship(value):
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

def check(records, today=None):
    today = today or dt.date.today()
    if not isinstance(records, list):
        raise ValueError("Approved offers must be a JSON array")
    kept, rejected, seen = [], [], set()
    for i, item in enumerate(records):
        if not isinstance(item, dict) or any(not item.get(k) for k in REQUIRED):
            rejected.append((i, "Missing independent verification fields"))
            continue
        try:
            sailing = dt.date.fromisoformat(item["departure_date"])
            verified = dt.date.fromisoformat(item["verification_date"])
        except (TypeError, ValueError):
            rejected.append((i, "Invalid ISO date"))
            continue
        if sailing <= today:
            rejected.append((i, "Departed or departing today"))
            continue
        if verified > today or (today - verified).days > 7:
            rejected.append((i, "Verification too old or in future"))
            continue
        if item["verification_method"] not in METHODS:
            rejected.append((i, "Unrecognised verification method"))
            continue
        u = urlsplit(item["seller_url"])
        if u.scheme != "https" or not u.hostname or u.hostname.endswith("cabins41.com"):
            rejected.append((i, "Invalid independent seller URL"))
            continue
        if not isinstance(item["verified_solo_fare"], (int, float)) or isinstance(item["verified_solo_fare"], bool) or item["verified_solo_fare"] <= 0:
            rejected.append((i, "Invalid solo fare"))
            continue
        if not isinstance(item["verification_evidence"], str) or len(item["verification_evidence"].strip()) < 20:
            rejected.append((i, "Insufficient verification evidence"))
            continue
        key = (normal_ship(item["ship"]), sailing.isoformat())
        if key in seen:
            rejected.append((i, "Duplicate ship/departure"))
            continue
        seen.add(key)
        kept.append(item)
    return kept, rejected

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--approved", required=True, type=pathlib.Path)
    p.add_argument("--output", required=True, type=pathlib.Path)
    p.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    a = p.parse_args()
    approved = json.loads(a.approved.read_text(encoding="utf-8"))
    kept, rejected = check(approved, a.today)
    result = {"status": "REVIEW_ONLY_NO_DEPLOY", "date": a.today.isoformat(),
              "approved_count": len(kept), "rejected_count": len(rejected),
              "rejections": [{"row": i, "reason": reason} for i, reason in rejected],
              "offers": kept}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Approved: {len(kept)}; rejected: {len(rejected)}. No deployment performed.")

if __name__ == "__main__":
    main()
