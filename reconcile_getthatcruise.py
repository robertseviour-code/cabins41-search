"""Reconcile a newly extracted solo-fare catalogue against saved Cabins41 leads.

Review-only: no automatic publication, no supplement-based exclusion.
A ship/date key may contain distinct itineraries or fare products, so matches
are provisional, not proof of the same offer.
"""
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
import argparse


def key(row):
    return (str(row.get("ship", "")).strip().casefold(),
            str(row.get("departure_date", "")).strip())


def reconcile(old_rows, new_rows, today=None):
    today = today or date.today()
    old = defaultdict(list)
    new = defaultdict(list)
    for row in old_rows:
        if row.get("ship") and row.get("departure_date"):
            old[key(row)].append(row)
    for row in new_rows:
        if row.get("ship") and row.get("departure_date"):
            new[key(row)].append(row)
    results = []
    for k in sorted(set(old) | set(new)):
        old_group, new_group = old[k], new[k]
        try:
            expired = date.fromisoformat(k[1]) < today
        except ValueError:
            expired = False
        old_prices = sorted({str(x.get("advertised_solo_from")) for x in old_group if x.get("advertised_solo_from") is not None})
        new_prices = sorted({str(x.get("advertised_solo_from")) for x in new_group if x.get("advertised_solo_from") is not None})
        if expired:
            status = "expired_review"
        elif not old_group:
            status = "new_candidate_review"
        elif not new_group:
            status = "missing_from_new_snapshot_review"
        elif len(old_group) != 1 or len(new_group) != 1:
            status = "ambiguous_multiple_sailings_review"
        elif old_prices != new_prices:
            status = "price_changed_review"
        else:
            status = "matched_review"
        results.append(dict(ship=k[0], departure_date=k[1],
                            old_count=len(old_group), new_count=len(new_group),
                            old_solo_prices=";".join(old_prices),
                            new_solo_prices=";".join(new_prices),
                            status=status))
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("old_holding_json", type=Path)
    p.add_argument("new_catalogue_json", type=Path,
                   help="JSON array with ship, departure_date, advertised_solo_from")
    p.add_argument("output_csv", type=Path)
    args = p.parse_args()
    holding = json.loads(args.old_holding_json.read_text(encoding="utf-8"))
    old = holding["results"]["30"]["possible_offers"]
    new = json.loads(args.new_catalogue_json.read_text(encoding="utf-8"))
    if not isinstance(new, list) or not new:
        raise ValueError("New catalogue must be a nonempty JSON array; refusing empty-snapshot reconciliation")
    if any(not isinstance(row, dict) or not row.get("ship") or not row.get("departure_date") for row in new):
        raise ValueError("New catalogue contains incomplete records; refusing misleading reconciliation")
    rows = reconcile(old, new)
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else
                                ["ship", "departure_date", "old_count", "new_count",
                                 "old_solo_prices", "new_solo_prices", "status"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} ship/date groups reconciled; all require review")


if __name__ == "__main__":
    main()
