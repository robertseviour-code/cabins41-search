import datetime as dt
import unittest
from publication_gate import check

TODAY = dt.date(2026, 12, 12)
BASE = dict(ship="Bolette", departure_date="2027-01-05",
            seller_url="https://www.fredolsencruises.com/cruise/t2701",
            verified_solo_fare=3049, verification_date="2026-12-10",
            verification_evidence="Seller checkout solo cabin BS, same-grade fare checked",
            verification_method="same_grade_fare_comparison")

class PublicationGateTests(unittest.TestCase):
    def test_independently_verified(self):
        kept, bad = check([BASE], TODAY)
        self.assertEqual((len(kept), len(bad)), (1, 0))
    def test_search_candidates_never_publish(self):
        self.assertEqual(len(check([{"ship":"Bolette","departure_date":"2027-01-05","seller_url":BASE["seller_url"],"solo_evidence":"Solo fare"}], TODAY)[0]), 0)
    def test_expired(self):
        self.assertEqual(len(check([dict(BASE, departure_date="2026-12-11")], TODAY)[0]), 0)
    def test_duplicate(self):
        self.assertEqual(len(check([BASE, dict(BASE, seller_url="https://other.example/offer")], TODAY)[0]), 1)
    def test_stale(self):
        self.assertEqual(len(check([dict(BASE, verification_date="2026-11-11")], TODAY)[0]), 0)
    def test_bad_price(self):
        self.assertEqual(len(check([dict(BASE, verified_solo_fare=0)], TODAY)[0]), 0)
    def test_invalid_date(self):
        self.assertEqual(len(check([dict(BASE, departure_date="2027-02-30")], TODAY)[0]), 0)

if __name__ == "__main__":
    unittest.main()
