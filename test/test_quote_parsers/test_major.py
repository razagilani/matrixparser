from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers import MajorEnergyMatrixParser
from brokerage.validation import GAS, ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestMajor(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = 'Commercial and Residential Electric and Gas Rack Rates March 11 2016.xlsx'
    PARSER_CLASS = MajorEnergyMatrixParser
    EXPECTED_COUNT = 3810

    def test_first(self):
        # first quote is electric
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 3, 14), q.valid_from)
        self.assertEqual(datetime(2016, 3, 18), q.valid_until)
        self.assertEqual(datetime(2016, 4, 1), q.start_from)
        self.assertEqual(datetime(2016, 5, 1), q.start_until)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(6, q.term_months)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(74000, q.limit_volume)
        self.assertEqual('Major-electric-IL-ComEd-', q.rate_class_alias)
        self.assertEqual(0.0585, q.price)
        self.assertEqual(q.service_type, ELECTRIC)

    def test_last(self):
        # last quote is gas
        q = self.quotes[-1]
        self.assertEqual(datetime(2016, 3, 14), q.valid_from)
        self.assertEqual(datetime(2016, 3, 18), q.valid_until)
        self.assertEqual(datetime(2016, 7, 1), q.start_from)
        self.assertEqual(datetime(2016, 8, 1), q.start_until)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(24, q.term_months)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual('Major-gas-SJG', q.rate_class_alias)
        self.assertEqual(0.5762, q.price)
        self.assertEqual(q.service_type, GAS)

