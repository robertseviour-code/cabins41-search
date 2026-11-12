import unittest
from datetime import date
from reconcile_getthatcruise import reconcile


class ReconcileTests(unittest.TestCase):
    def test_changed_price_not_discarded(self):
        old = [{"ship": "MSC Preziosa", "departure_date": "2027-01-29", "advertised_solo_from": 521}]
        new = [{"ship": "MSC Preziosa", "departure_date": "2027-01-29", "advertised_solo_from": 499}]
        self.assertEqual(reconcile(old, new, date(2026, 11, 12))[0]["status"], "price_changed_review")

    def test_same_ship_date_multiple_products_not_merged(self):
        old = [{"ship": "Balmoral", "departure_date": "2027-01-29", "advertised_solo_from": 1000}]
        new = [{"ship": "Balmoral", "departure_date": "2027-01-29", "advertised_solo_from": 1000},
               {"ship": "Balmoral", "departure_date": "2027-01-29", "advertised_solo_from": 1200}]
        self.assertEqual(reconcile(old, new, date(2026, 11, 12))[0]["status"],
                         "ambiguous_multiple_sailings_review")

    def test_new_not_auto_published(self):
        new = [{"ship": "Ambition", "departure_date": "2027-02-01", "advertised_solo_from": 999}]
        self.assertEqual(reconcile([], new, date(2026, 11, 12))[0]["status"], "new_candidate_review")


if __name__ == "__main__":
    unittest.main()
