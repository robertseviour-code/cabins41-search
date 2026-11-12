import unittest
from getthatcruise_cards import visible_cards


class GetThatCruiseCardTests(unittest.TestCase):
    def test_two_sailings_do_not_mix_prices(self):
        text = ("\nMSC Preziosa · 7 nights 29 January 2027 · from Southampton "
                "£521 per person travelling alone £359 per person sharing Check price "
                "\nBalmoral · 14 nights 2 February 2027 · from Southampton "
                "£2,219 per person travelling alone £1,499 per person sharing Check price")
        rows = visible_cards(text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["calculated_supplement"], "45.1")
        self.assertEqual(rows[1]["calculated_supplement"], "48.0")
        self.assertTrue(all(x["verification"] == "needs_manual_check" for x in rows))
        self.assertTrue(all(x["preliminary_status"] == "review_for_cabins41" for x in rows))

    def test_missing_sharing_does_not_steal_next_card_price(self):
        text = ("\nBalmoral · 11 nights 19 November 2026 "
                "£2,479 per person travelling alone £1,299 per person sharing "
                "\nAmbition · 4 nights 27 November 2026 "
                "£899 per person travelling alone "
                "\nMSC Preziosa · 7 nights 29 January 2027 "
                "£521 per person travelling alone £359 per person sharing")
        rows = visible_cards(text)
        self.assertEqual([r["ship"] for r in rows], ["Balmoral", "Ambition", "MSC Preziosa"])
        self.assertEqual([r["sharing_pp_gbp"] for r in rows], [1299, None, 359])
        self.assertEqual([r["calculated_supplement"] for r in rows], ["90.8", None, "45.1"])

    def test_missing_sharing_price(self):
        rows = visible_cards("\nAmbition · 4 nights 27 November 2026 £899 per person travelling alone")
        self.assertEqual(rows[0]["preliminary_status"], "needs_manual_check")


if __name__ == "__main__":
    unittest.main()
