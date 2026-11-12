"""Extract fare pairs from the 60-card Get That Cruise solo-fares landing page.

This is a review-only parser, not a crawler for the full 439-sailing finder.
"""
import re
from solo_fare_math import classify

CARD = re.compile(
    r"(?P<ship>[A-Z][A-Za-z .'-]{1,35})\s*·\s*\d+\s+nights?"
    r"\s+(?P<date>\d{1,2}\s+[A-Za-z]+\s+20\d{2})\b"
    r"(?P<body>.*?)(?=\b[A-Z][A-Za-z .'-]{1,35}\s*·\s*\d+\s+nights?\s+\d{1,2}\s+[A-Za-z]+\s+20\d{2}\b|\Z)",
    re.S
)
# The solo price is displayed on the line *before* 'per person travelling alone'.
SOLO = re.compile(r"£\s*([\d,]+)\s+per person travelling alone", re.I)
SHARE = re.compile(r"£\s*([\d,]+)\s+per person sharing", re.I)


def visible_cards(text, max_supplement=None):
    results = []
    for m in CARD.finditer(text):
        body = m.group("body")
        solo, share = SOLO.search(body), SHARE.search(body)
        if not solo:
            continue
        solo_price = int(solo.group(1).replace(",", ""))
        share_price = int(share.group(1).replace(",", "")) if share else None
        verdict = classify(solo_price, share_price, max_supplement)
        results.append({
            "ship": m.group("ship").strip(), "date_displayed": m.group("date"),
            "solo_gbp": solo_price, "sharing_pp_gbp": share_price,
            "calculated_supplement": verdict["supplement_percent"],
            "preliminary_status": verdict["status"],
            "verification": "needs_manual_check",
        })
    return results
