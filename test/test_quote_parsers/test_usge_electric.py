from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers import USGEElectricMatrixParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestUSGEElectric(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = 'USGE Matrix Pricing - ELEC - 20160613.xlsx'
    PARSER_CLASS = USGEElectricMatrixParser
    EXPECTED_COUNT = 4032

    def check_every_quote(self, q):
        self.assertEqual(ELECTRIC, q.service_type)
        self.assertEqual(q.valid_from, datetime(2016, 6, 13))
        self.assertEqual(q.valid_until, datetime(2016, 6, 14))

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual(q.price, 0.0825)
        self.assertEqual(q.min_volume, 0)
        self.assertEqual(q.limit_volume, 500000)
        self.assertEqual(q.term_months, 6)
        self.assertEqual(q.start_from, datetime(2016, 07, 01))
        self.assertEqual(q.start_until, datetime(2016, 8, 01))
        self.assertEqual(q.rate_class_alias,
                         "USGE-electric-Connecticut Light & Power-Residential-"
                         "Residential-All Zones")

    def test_second(self):
        q = self.quotes[1]
        self.assertEqual(q.price, 0.0808)
        self.assertEqual(q.min_volume, 0)
        self.assertEqual(q.limit_volume, 5e5)
        self.assertEqual(q.term_months, 6)
        self.assertEqual(q.start_from, datetime(2016, 8, 1))
        self.assertEqual(q.start_until, datetime(2016, 9, 1))

    def test_third(self):
        self.assertEqual(self.quotes[2].price, 0.0883)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(q.price, 0.0652)
        self.assertEqual(q.min_volume, 5e5)
        self.assertEqual(q.limit_volume, 1e6)
        self.assertEqual(q.term_months, 24)
        self.assertEqual(q.start_from, datetime(2016, 12, 1))
        self.assertEqual(q.start_until, datetime(2017, 1, 1))
        self.assertEqual(
            q.rate_class_alias,
            "USGE-electric-Penn Power-Commercial-Commerical: C1, C2, C3, "
            "CG, CH, GH1, GH2, GS1, GS3-PJMATSI")

