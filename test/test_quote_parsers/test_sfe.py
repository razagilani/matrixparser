from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers import SFEMatrixParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestSFE(QuoteParserTest, TestCase):

    FILE_NAME = 'SFE Pricing Worksheet - April 29, 2016.xlsx'
    PARSER_CLASS = SFEMatrixParser
    EXPECTED_COUNT = 7834

    def check_every_quote(self, q):
        # 12 AM, 10 AM EDT
        self.assertEqual(datetime(2016, 4, 29, 4), q.valid_from)
        self.assertEqual(datetime(2016, 5, 2, 14), q.valid_until)

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 5, 1), q.start_from)
        self.assertEqual(datetime(2016, 6, 1), q.start_until)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(6, q.term_months)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(150000, q.limit_volume)
        self.assertEqual('SFE-electric-NY-A (NiMo, NYSEG)', q.rate_class_alias)
        self.assertEqual(False, q.purchase_of_receivables)
        self.assertEqual(0.0596, q.price)
        self.assertEqual(ELECTRIC, q.service_type)

    def test_more(self):
        # check volume ranges in many rows rows because SFE's units are
        # complicated
        q = self.quotes[5]
        self.assertEqual(150000, q.min_volume)
        self.assertEqual(500000, q.limit_volume)
        q = self.quotes[10]
        self.assertEqual(500000, q.min_volume)
        self.assertEqual(1e6, q.limit_volume)
        q = self.quotes[15]
        self.assertEqual(1e6, q.min_volume)
        self.assertEqual(2e6, q.limit_volume)
        q = self.quotes[20]
        self.assertEqual(2e6, q.min_volume)
        self.assertEqual(None, q.limit_volume)
        q = self.quotes[25]
        self.assertEqual(0, q.min_volume)
        self.assertEqual(150000, q.limit_volume)

    def test_weird_date(self):
        q = self.quotes[250]
        self.assertEqual(datetime(2016, 6, 1), q.start_from)
