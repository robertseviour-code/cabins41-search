"""Calculate a solo supplement without imposing an unapproved Cabins41 ceiling.

The two fares must be for the same sailing, cabin grade, currency and
inclusions; the sharing fare is per person based on two sharing.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def supplement_percent(solo_fare, sharing_per_person):
    try:
        solo = Decimal(str(solo_fare))
        sharing = Decimal(str(sharing_per_person))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not (solo.is_finite() and sharing.is_finite()) or solo <= 0 or sharing <= 0:
        return None
    return ((solo / sharing - 1) * 100).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )


def classify(solo_fare, sharing_per_person, max_supplement=None):
    """Never reject a fare unless an explicitly approved ceiling is supplied."""
    pct = supplement_percent(solo_fare, sharing_per_person)
    if pct is None:
        return {"status": "needs_manual_check", "supplement_percent": None}
    if max_supplement is None:
        status = "review_for_cabins41"
    else:
        try:
            ceiling = Decimal(str(max_supplement))
            if not ceiling.is_finite() or ceiling < 0:
                raise ValueError("Invalid supplement ceiling")
        except (InvalidOperation, TypeError):
            raise ValueError("Invalid supplement ceiling")
        status = "qualifies" if pct <= ceiling else "above_threshold"
    return {"status": status, "supplement_percent": str(pct)}
