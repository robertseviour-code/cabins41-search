import unittest
from decimal import Decimal
from solo_fare_math import supplement_percent, classify


class SoloFareMathTests(unittest.TestCase):
    def test_zero_supplement(self):
        self.assertEqual(supplement_percent(500, 500), Decimal("0.0"))

    def test_low_supplement(self):
        self.assertEqual(supplement_percent(600, 500), Decimal("20.0"))

    def test_expensive_solo_fare(self):
        self.assertEqual(supplement_percent(521, 359), Decimal("45.1"))
        self.assertEqual(classify(521, 359)["status"], "above_threshold")

    def test_invalid_prices(self):
        for a, b in [(0, 500), (500, 0), ("unknown", 500), (-1, 500), ("NaN", 500)]:
            self.assertIsNone(supplement_percent(a, b))

    def test_no_assumed_verification(self):
        self.assertEqual(classify(None, 500)["status"], "needs_manual_check")


if __name__ == "__main__":
    unittest.main()
