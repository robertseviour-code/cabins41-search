import unittest
import json
from search import bounded_sailings, extract_page_leads, structured_solo_sailings

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

class FinderExtractionTests(unittest.TestCase):
    def page(self, records):
        payload = json.dumps([1, 'x:{"sailings":' + json.dumps(records) + '}'])
        return '<script>self.__next_f.push(' + payload + ')</script>'

    def test_solo_fare_belongs_to_same_record(self):
        raw = self.page([
            {'ship':'Balmoral','departureDate':'2027-12-05','soloFrom':1279,'path':'/fred/a'},
            {'ship':'Borealis','departureDate':'2027-12-06','soloFrom':'$undefined','path':'/fred/b'}])
        found, duplicates = extract_page_leads(raw, 'https://www.getthatcruise.co.uk/cruises?chips=solo',
                                              {'id':30,'name':'Get That Cruise'}, set(), True)
        self.assertEqual([(x['ship'],x['departure_date']) for x in found], [('Balmoral','2027-12-05')])
        self.assertEqual(found[0]['advertised_solo_from'],1279)
        self.assertEqual(duplicates,[])

    def test_invalid_and_external_records_rejected(self):
        records = [{'ship':'Balmoral','departureDate':'2027-02-30','soloFrom':100,'path':'/fred/a'},
                   {'ship':'Borealis','departureDate':'2027-12-06','soloFrom':100,'path':'//other.test/a'}]
        self.assertEqual(list(structured_solo_sailings(self.page(records))), [])

    def test_missing_data_is_visible_failure(self):
        with self.assertRaises(ValueError):
            list(structured_solo_sailings('<html>Loading</html>'))

if __name__ == '__main__':
    unittest.main()
