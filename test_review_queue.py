import unittest
from review_queue import row_for, build_rows


class ReviewQueueTests(unittest.TestCase):
    def test_zero_wording(self):
        x = row_for({"solo_evidence": "Zuschlag nur 0%"})
        self.assertEqual(x["review_priority"], "explicit_zero_claim")
        self.assertEqual(x["advertised_supplement"], "0%")
        self.assertEqual(x["review_status"], "needs_manual_check")

    def test_generic_solo_fare_not_qualified(self):
        x = row_for({"solo_evidence": "Solo fare"})
        self.assertEqual(x["review_priority"], "solo_fare_only")
        self.assertFalse(x["advertised_supplement"])

    def test_ignore_unrelated_percent_in_context(self):
        x = row_for({"solo_evidence": "Solo fare", "evidence": "0% on another voyage"})
        self.assertFalse(x["advertised_supplement"])

    def test_filter_source(self):
        rows = build_rows({"offers": [
            {"source_name": "Get That Cruise", "solo_evidence": "Solo fare"},
            {"source_name": "Other", "solo_evidence": "Zuschlag nur 0%"}]}, "Get That Cruise")
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
