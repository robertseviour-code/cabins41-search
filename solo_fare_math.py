"""Conservative solo supplement calculator for manually verified fares.

Both fares must refer to the same sailing, cabin grade, currency and inclusions.
The sharing fare is the price PER PERSON when two people share.
This helper never treats a page's generic "solo fare" label as a bargain.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def supplement_percent(solo_fare, sharing_per_person):
    """Return percentage over one sharing fare, or None for invalid input."""
    try:
        solo = Decimal(str(solo_fare))
        sharing = Decimal(str(sharing_per_person))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not (solo.is_finite() and sharing.is_finite()):
        return None
    if solo <= 0 or sharing <= 0:
        return None
    return ((solo / sharing - 1) * 100).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )


def classify(solo_fare, sharing_per_person, max_supplement=20):
    """Only classify a fare after like-for-like prices have been confirmed."""
    pct = supplement_percent(solo_fare, sharing_per_person)
    if pct is None:
        return {"status": "needs_manual_check", "supplement_percent": None}
    threshold = Decimal(str(max_supplement))
    return {
        "status": "qualifies" if pct <= threshold else "above_threshold",
        "supplement_percent": str(pct),
    }
