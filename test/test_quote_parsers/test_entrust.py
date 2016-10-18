from unittest import TestCase
from datetime import datetime
from brokerage.quote_parsers import EntrustMatrixParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestEntrust(QuoteParserTest, TestCase):
    FILE_NAME = 'Entrust Energy Commercial Matrix Pricing_10182016.xlsx'
    PARSER_CLASS = EntrustMatrixParser
    EXPECTED_COUNT = 14073

    def test_entrust(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 10, 1), q.start_from)
        self.assertEqual(datetime(2016, 11, 1), q.start_until)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(12, q.term_months)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(100000, q.limit_volume)
        self.assertEqual('Entrust-electric-Commonwealth Edison (C28) (0 -100 kw)', q.rate_class_alias)

        self.assertEqual(0.0658, q.price)
        self.assertEqual(q.service_type, ELECTRIC)

        # since this one is especially complicated and also missed a row,
        # check the last quote too. (this also checks the "sweet spot"
        # columns which work differently from the other ones)
        q = self.quotes[-1]
        self.assertEqual(datetime(2018, 3, 1), q.start_from)

        self.assertEqual(datetime(2018, 4, 1), q.start_until)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(24, q.term_months)
        self.assertEqual(6e5, q.min_volume)
        self.assertEqual(1e6, q.limit_volume)
        self.assertEqual('Entrust-electric-Consolidated Edison - Zone J', q.rate_class_alias)
        self.assertEqual(0.0687, q.price)
        self.assertEqual(q.service_type, ELECTRIC)
