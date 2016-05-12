from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers import DirectEnergyMatrixParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestDirectEnergy(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = 'Matrix 1 Example - Direct Energy.xls'
    ALIASES = ['Direct-electric-CT-CLP-37, R35--']
    PARSER_CLASS = DirectEnergyMatrixParser
    EXPECTED_COUNT = 106554

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2015, 5, 1), q.start_from)
        self.assertEqual(datetime(2015, 6, 1), q.start_until)
        self.assertEqual(q.term_months, 6)
        self.assertEqual(q.valid_from, datetime(2015, 5, 4))
        self.assertEqual(q.valid_until, datetime(2015, 5, 5))
        self.assertEqual(q.min_volume, 0)
        self.assertEqual(q.limit_volume, 75000)
        self.assertEqual(q.rate_class_alias, self.ALIASES[0])
        self.assertEqual(q.price, .07036)
        self.assertEqual(q.service_type, ELECTRIC)
