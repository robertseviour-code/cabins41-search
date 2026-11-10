import unittest
from search import bounded_sailings

class OfferExtractionTests(unittest.TestCase):
    def test_destination_does_not_extend_ship(self):
        for ship, region in [('MSC Divina','South America'), ('MSC Virtuosa','South America'), ('MSC Musica','South America'), ('Norwegian Encore','North America'), ('Carnival Firenze','Central America')]:
            with self.subTest(ship=ship):
                offers = bounded_sailings(f'<article>14 Mar 2027 1 Nights {ship} {region} Solo Prices From £67</article>')
                self.assertEqual([(x['ship'],x['departure_date']) for _,x in offers], [(ship,'2027-03-14')])

    def test_neighbouring_offers_cannot_supply_solo_evidence(self):
        self.assertEqual(bounded_sailings('<section><article>Solo Prices £67</article><article>MSC Divina 14 Mar 2027</article><article>Norwegian Joy 14 Dec 2026</article></section>'), [])

    def test_multiple_departure_options_rejected(self):
        self.assertEqual(bounded_sailings('<article>Norwegian Joy 14 Dec 2026 or 30 Nov 2026 Solo Prices £239</article>'), [])

    def test_individual_offers_stay_separate(self):
        offers=bounded_sailings('<section><article>Norwegian Joy 14 Dec 2026 Solo Prices £239</article><article>MSC Divina 14 Mar 2027 Solo Prices £67</article></section>')
        self.assertEqual([(x['ship'],x['departure_date']) for _,x in offers], [('Norwegian Joy','2026-12-14'),('MSC Divina','2027-03-14')])

if __name__ == '__main__':
    unittest.main()
