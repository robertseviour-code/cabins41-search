"""Review-only parser for Get That Cruise's visible solo-fare catalogue cards.

Card boundaries are defined by the displayed ship/nights/date sequence.
Never infer a sharing fare from another card. No supplement-based exclusion.
"""
import re
from solo_fare_math import classify

# Ship/nights/date on the catalogue are separated by line breaks in HTML text.
SHIP_DATE = re.compile(
    r"(?m)^\s*(?P<ship>[A-Z][A-Za-z .'-]{1,35}?)\s*·\s*"
    r"(?P<nights>\d+)\s+nights?\s+"
    r"(?P<date>\d{1,2}\s+[A-Za-z]+\s+20\d{2})\b"
)
SOLO = re.compile(r"£\s*([\d,]+)\s+per person travelling alone", re.I)
SHARE = re.compile(r"£\s*([\d,]+)\s+per person sharing", re.I)


def visible_cards(text, max_supplement=None):
    matches = list(SHIP_DATE.finditer(text))
    results = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end():end]
        solo, share = SOLO.search(body), SHARE.search(body)
        if not solo:
            continue
        solo_price = int(solo.group(1).replace(",", ""))
        share_price = int(share.group(1).replace(",", "")) if share else None
        verdict = classify(solo_price, share_price, max_supplement)
        results.append({
            "ship": match.group("ship").strip(),
            "date_displayed": match.group("date"),
            "nights": int(match.group("nights")),
            "solo_gbp": solo_price, "sharing_pp_gbp": share_price,
            "calculated_supplement": verdict["supplement_percent"],
            "preliminary_status": verdict["status"],
            "verification": "needs_manual_check",
        })
    return results
