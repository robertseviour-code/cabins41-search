import unittest
import json
import datetime
from search import candidate_batch
from search import bounded_sailings, extract_page_leads, structured_solo_sailings, homepage_sailings, travel_dealz_sailing

class TravelDealzTests(unittest.TestCase):
    def test_deferred_links_rotate_without_exceeding_budget(self):
        links = list(range(44))
        days = [candidate_batch(links, 20, datetime.date(2026, 11, 13)+datetime.timedelta(days=i)) for i in range(34)]
        self.assertTrue(all(len(x) == len(set(x)) == 20 for x in days))
        self.assertTrue(all(x[:10] == links[:10] for x in days))
        self.assertEqual(set().union(*map(set, days)), set(links))
    def test_departure_not_publication_or_itinerary_date(self):
        raw = '<time>13 November 2026</time><div class="entry-content"><p>Die AIDAprima fährt nach Kiel.</p><p>Für Alleinreisende werden ab 1.189€ fällig.</p><h2>Route</h2><p>Die Kreuzfahrt beginnt am 5. Dezember 2026 auf Gran Canaria.</p><p>Am 7. Dezember 2026 erreicht sie Agadir.</p></div><aside>MSC Musica Abfahrt am 8. Dezember 2026</aside>'
        records = travel_dealz_sailing(raw)
        self.assertEqual([(x[1]['ship'], x[1]['departure_date']) for x in records], [('AIDAprima', '2026-12-05')])

    def test_ambiguous_ships_or_departures_rejected(self):
        for offer in ['AIDAprima und MSC Sinfonia', 'AIDAprima']:
            raw = f'<div class="entry-content"><p>{offer}. Für Alleinreisende ab 541€.</p><p>Abfahrt am 5. Dezember 2026.</p><p>Abfahrt am 12. Dezember 2026.</p></div>'
            self.assertEqual(travel_dealz_sailing(raw), [])

    def test_solo_wording_outside_article_cannot_qualify(self):
        raw = '<div class="entry-content"><p>MSC Sinfonia ab 389€ bei Doppelbelegung.</p><p>Abfahrt am 15. Dezember 2026.</p></div><aside>Alleinreisende ab 541€</aside>'
        self.assertEqual(travel_dealz_sailing(raw), [])

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

class HomepageTests(unittest.TestCase):
    def test_explicit_departure_and_heading_include_river_ships(self):
        raw = '<article class="offer" data-departure="2027-12-15"><h3>MS Maxima · Advent in Austria</h3><p>Added 9 November 2026</p></article>'
        self.assertEqual(homepage_sailings(raw), [{'ship':'MS Maxima','departure_date':'2027-12-15'}])

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
