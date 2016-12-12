from unittest import TestCase
from datetime import datetime
from brokerage.quote_parsers.agera_gas import AgeraGasMatrixParser
from brokerage.validation import GAS
from test.test_quote_parsers import QuoteParserTest


class AgeraGasTest(QuoteParserTest, TestCase):
    FILE_NAME = 'clean_agera_matrix-updated.csv'
    ALIASES = [
        'Agera-Gas-CA-CA_PGE',
        'Agera-Gas-md-md_wgl'
    ]
    PARSER_CLASS = AgeraGasMatrixParser
    EXPECTED_COUNT = 1806

    def test_agera_gas(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2017, 1, 1), q.start_from)
        self.assertEqual(datetime(2017, 1, 2), q.start_until)
        self.assertEqual(3, q.term_months)
        self.assertEqual(datetime(2016, 10, 19), q.valid_from)
        self.assertEqual(datetime(2016, 10, 26), q.valid_until)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(1000000, q.limit_volume)
        self.assertEqual(self.ALIASES[0], q.rate_class_alias)
        self.assertEqual(.575, q.price)
        self.assertEqual(q.service_type, GAS)
        self.assertEqual(q.dual_billing, False)

        q1 = self.quotes[623]
        self.assertEqual(datetime(2016, 12, 1), q1.start_from)
        self.assertEqual(datetime(2016, 12, 2), q1.start_until)
        self.assertEqual(3, q1.term_months)
        self.assertEqual(datetime(2016, 10, 19), q1.valid_from)
        self.assertEqual(datetime(2016, 10, 26), q1.valid_until)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(1000000, q1.limit_volume)
        self.assertEqual(self.ALIASES[1], q1.rate_class_alias)
        self.assertEqual(0.53, q1.price)
        self.assertEqual(q1.service_type, GAS)
        self.assertEqual(q1.dual_billing, False)