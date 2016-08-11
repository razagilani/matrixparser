from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers import LibertyMatrixParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestLiberty(QuoteParserTest, TestCase):

    FILE_NAME = 'Liberty Power Daily Pricing for NEX ABC 2016-08-08.xlsx'
    PARSER_CLASS = LibertyMatrixParser
    EXPECTED_COUNT = 39708

    def test_first(self):
        # First quote on first page from first table
        q1 = self.quotes[0]
        # validity dates are only checked once
        self.assertEqual(datetime(2016, 8, 8), q1.valid_from)
        self.assertEqual(datetime(2016, 8, 9), q1.valid_until)
        self.assertEqual(datetime(2016, 9, 1), q1.start_from)
        self.assertEqual(datetime(2016, 10, 1), q1.start_until)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(3, q1.term_months)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(25000, q1.limit_volume)
        self.assertEqual(0.096, q1.price)
        self.assertEqual('Liberty-electric-PEPCO-DC-PEPCO-Default',
                         q1.rate_class_alias)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(q1.service_type, ELECTRIC)

    def test_second(self):
        # Last quote from first page from last table (super saver)
        # (to get this index, break after the first iteration of the loop
        # through sheets)
        q2 = self.quotes[2159]
        self.assertEqual(33, q2.term_months)
        self.assertEqual(0.07197, q2.price)
        self.assertEqual(datetime(2017, 8, 1), q2.start_from)
        self.assertEqual(datetime(2017, 9, 1), q2.start_until)
        self.assertEqual('Liberty-electric-PEPCO-DC-PEPCO-GTLV/DMGT',
                         q2.rate_class_alias)
        self.assertEqual(500000, q2.min_volume)
        self.assertEqual(2000000, q2.limit_volume)
        self.assertEqual(q2.service_type, ELECTRIC)

    def test_last(self):
        # Last quote (super saver) from last table on last readable sheet
        q3 = self.quotes[-1]
        self.assertEqual(24, q3.term_months)
        self.assertEqual(.07478, q3.price)
        self.assertEqual(datetime(2017, 1, 1), q3.start_from)
        self.assertEqual(datetime(2017, 2, 1), q3.start_until)
        self.assertEqual('Liberty-electric-WPP-APS-SOHO (Tax ID Required)',
                         q3.rate_class_alias)
        self.assertEqual(0, q3.min_volume)
        self.assertEqual(2000000, q3.limit_volume)
        self.assertEqual(q3.service_type, ELECTRIC)

