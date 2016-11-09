from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers import USGEGasMatrixParser
from brokerage.validation import GAS
from test.test_quote_parsers import QuoteParserTest


class TestUSGEGas(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = 'USGE Matrix Pricing - Gas - 20161107.xlsx'
    PARSER_CLASS = USGEGasMatrixParser
    EXPECTED_COUNT = 2224

    def check_every_quote(self, q):
        self.assertEqual(datetime(2016, 11, 7, 0), q.valid_from)
        self.assertEqual(datetime(2016, 11, 8, 0), q.valid_until)
        self.assertEqual(GAS, q.service_type)

    def test_in(self):
        q = self.quotes[0]
        self.assertEqual(
            'USGE-gas-Nipsco ("A")-Residential-Residential',
            q.rate_class_alias)
        self.assertEqual(datetime(2016, 12, 1), q.start_from)
        self.assertEqual(datetime(2017, 1, 1), q.start_until)
        self.assertEqual(6, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(0, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual(.5558, q.price)

    def test_ky(self):
        q = self.quotes[160]
        self.assertEqual('USGE-gas-Nipsco ("B")-Commercial-Commercial', q.rate_class_alias)
        self.assertEqual(datetime(2017, 4, 1), q.start_from)
        self.assertEqual(datetime(2017, 5, 1), q.start_until)
        self.assertEqual(18, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(10000, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual(.4176, q.price)

    def test_md(self):
        q = self.quotes[240]
        self.assertEqual(
            'USGE-gas-Columbia of Kentucky-Commercial-Commercial',
            q.rate_class_alias)
        self.assertEqual(datetime(2016, 12, 1), q.start_from)
        self.assertEqual(datetime(2017, 1, 1), q.start_until)
        self.assertEqual(6, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(10000, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual(.3989, q.price)

    def test_nj(self):
        q = self.quotes[400]
        self.assertEqual(
            'USGE-gas-Washington Gas & Light-Residential-Residential',
            q.rate_class_alias)
        self.assertEqual(datetime(2017, 4, 1), q.start_from)
        self.assertEqual(datetime(2017, 5, 1), q.start_until)
        self.assertEqual(18, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(0, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual(.4812, q.price)

    def test_ny(self):
        q = self.quotes[608]
        self.assertEqual(
            'USGE-gas-PSEG-Commercial-Commercial',
            q.rate_class_alias)
        self.assertEqual(datetime(2017, 4, 1), q.start_from)
        self.assertEqual(datetime(2017, 5, 1), q.start_until)
        self.assertEqual(12, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(10000, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual(.5785, q.price)

    def test_oh(self):
        q = self.quotes[1388]
        self.assertEqual(
            'USGE-gas-NYSEG (ORU)-Commercial-Commercial',
            q.rate_class_alias)
        self.assertEqual(datetime(2017, 4, 1), q.start_from)
        self.assertEqual(datetime(2017, 5, 1), q.start_until)
        self.assertEqual(6, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(0, q.min_volume)
        self.assertEqual(10000, q.limit_volume)
        self.assertEqual(0.2773, q.price)

    def test_pa(self):
        q = self.quotes[1548]
        self.assertEqual(
            'USGE-gas-Orange & Rockland-Commercial-Commercial',
            q.rate_class_alias)
        self.assertEqual(datetime(2017, 2, 1), q.start_from)
        self.assertEqual(datetime(2017, 3, 1), q.start_until)
        self.assertEqual(24, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(0, q.min_volume)
        self.assertEqual(10000, q.limit_volume)
        self.assertEqual(.3584, q.price)
