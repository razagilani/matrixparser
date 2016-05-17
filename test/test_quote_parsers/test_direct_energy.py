from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers import DirectEnergyMatrixParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestDirectEnergy(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = 'Matrix 1 Example - Direct Energy.xls'
    PARSER_CLASS = DirectEnergyMatrixParser
    EXPECTED_COUNT = 106560

    def check_every_quote(self, q):
        self.assertEqual(q.service_type, ELECTRIC)
        self.assertEqual(q.valid_from, datetime(2015, 5, 4))
        self.assertEqual(q.valid_until, datetime(2015, 5, 5))

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual(q.term_months, 6)
        self.assertEqual(datetime(2015, 5, 1), q.start_from)
        self.assertEqual(datetime(2015, 6, 1), q.start_until)
        self.assertEqual(q.min_volume, 0)
        self.assertEqual(q.limit_volume, 75000)
        self.assertEqual('Direct-electric-CT-CLP-37, R35--', q.rate_class_alias)
        self.assertEqual(q.price, .07036)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(q.term_months, 25)
        self.assertEqual(datetime(2016, 4, 1), q.start_from)
        self.assertEqual(datetime(2016, 5, 1), q.start_until)
        self.assertEqual(q.min_volume, 750000)
        self.assertEqual(q.limit_volume, 1e6)
        self.assertEqual('Direct-electric-RI-NECO-S00--', q.rate_class_alias)
        self.assertEqual(q.price, .08628)
