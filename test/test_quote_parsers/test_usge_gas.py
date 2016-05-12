from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers import USGEGasMatrixParser
from brokerage.validation import GAS
from test.test_quote_parsers import QuoteParserTest


class TestUSGEGas(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = 'USGE Matrix Pricing - Gas - 20160502.xlsx'
    PARSER_CLASS = USGEGasMatrixParser
    EXPECTED_COUNT = 1948

    def check_every_quote(self, q):
        self.assertEqual(datetime(2016, 5, 2, 0), q.valid_from)
        self.assertEqual(datetime(2016, 5, 3, 0), q.valid_until)
        self.assertEqual(GAS, q.service_type)

    def test_in(self):
        q = self.quotes[0]
        self.assertEqual(
            'USGE-gas-Nipsco ("A")-Residential-Residential',
            q.rate_class_alias)
        self.assertEqual(datetime(2016, 6, 1), q.start_from)
        self.assertEqual(datetime(2016, 7, 1), q.start_until)
        self.assertEqual(6, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(0, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual(.55, q.price)

    def test_ky(self):
        q = self.quotes[160]
        self.assertEqual('USGE-gas-Columbia of Kentucky-Residential-Residential', q.rate_class_alias)
        self.assertEqual(datetime(2016, 6, 1), q.start_from)
        self.assertEqual(datetime(2016, 7, 1), q.start_until)
        self.assertEqual(6, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(0, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual(.4279, q.price)

    def test_md(self):
        q = self.quotes[240]
        self.assertEqual(
            'USGE-gas-Baltimore Gas & Electric-Residential-Residential',
            q.rate_class_alias)
        self.assertEqual(datetime(2016, 6, 1), q.start_from)
        self.assertEqual(datetime(2016, 7, 1), q.start_until)
        self.assertEqual(6, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(0, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual(.3932, q.price)

    def test_nj(self):
        q = self.quotes[400]
        self.assertEqual(
            'USGE-gas-New Jersey Natural-Residential-Residential',
            q.rate_class_alias)
        self.assertEqual(datetime(2016, 7, 1), q.start_from)
        self.assertEqual(datetime(2016, 8, 1), q.start_until)
        self.assertEqual(6, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(0, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual(.4833, q.price)

    def test_ny(self):
        q = self.quotes[608]
        self.assertEqual(
            'USGE-gas-Central Hudson-Commercial-Commercial',
            q.rate_class_alias)
        self.assertEqual(datetime(2016, 6, 1), q.start_from)
        self.assertEqual(datetime(2016, 7, 1), q.start_until)
        self.assertEqual(6, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(0, q.min_volume)
        self.assertEqual(10000, q.limit_volume)
        self.assertEqual(.4966, q.price)

    def test_oh(self):
        q = self.quotes[1388]
        self.assertEqual(
            'USGE-gas-Columbia of Ohio-Residential-Residential',
            q.rate_class_alias)
        self.assertEqual(datetime(2016, 6, 1), q.start_from)
        self.assertEqual(datetime(2016, 7, 1), q.start_until)
        self.assertEqual(6, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(0, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual(0.4394, q.price)

    def test_pa(self):
        q = self.quotes[1548]
        self.assertEqual(
            'USGE-gas-Columbia of PA-Residential-Residential',
            q.rate_class_alias)
        self.assertEqual(datetime(2016, 6, 1), q.start_from)
        self.assertEqual(datetime(2016, 7, 1), q.start_until)
        self.assertEqual(6, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(0, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual(.4174, q.price)
