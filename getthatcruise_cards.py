"""Extract displayed Get That Cruise fare pairs for manual review.

This deliberately processes only visible catalogue cards and does not assume
that a published solo fare is a low-supplement offer. A card with no sharing
price is not classifiable. Text must be fetched separately by the researcher.
"""
import re
from solo_fare_math import classify

CARD = re.compile(
    r"(?P<ship>[A-Za-z][A-Za-z .'-]{1,45})\s*·\s*\d+\s+nights?"
    r"\s+(?P<date>\d{1,2}\s+[A-Za-z]+\s+20\d{2})\b"
    r"(?P<body>.*?)(?=\b[A-Za-z][A-Za-z .'-]{1,45}\s*·\s*\d+\s+nights?\s+\d{1,2}\s+[A-Za-z]+\s+20\d{2}\b|\Z)",
    re.S
)
SOLO = re.compile(r"£\s*([\d,]+)\s+per person travelling alone", re.I)
SHARE = re.compile(r"£\s*([\d,]+)\s+per person sharing", re.I)


def visible_cards(text, max_supplement=20):
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
