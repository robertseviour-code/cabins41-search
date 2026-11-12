"""Convert saved Get That Cruise catalogue text into a review CSV.

Usage: python export_getthatcruise.py catalogue.txt review.csv
Only compare prices shown together on one sailing card. The resulting
supplement is informational and NEVER excludes a sailing.
"""
import argparse
import csv
from pathlib import Path
from getthatcruise_cards import visible_cards

FIELDS = ("ship", "date_displayed", "nights", "solo_gbp", "sharing_pp_gbp",
          "calculated_supplement", "preliminary_status", "verification")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("catalogue_text", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()
    text = args.catalogue_text.read_text(encoding="utf-8")
    rows = visible_cards(text)
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} fare cards exported for review; none automatically excluded")


if __name__ == "__main__":
    main()
