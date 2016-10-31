from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers import GEEMatrixParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestGeeElectricNY(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = 'GEE Rack Rates_NY_10.27.2016.xlsx'
    ALIASES = ['GEE-electric-ConEd-J-SC-02']
    PARSER_CLASS = GEEMatrixParser
    EXPECTED_COUNT = 270

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 10, 27), q.valid_from)
        self.assertEqual(datetime(2016, 10, 28), q.valid_until)
        self.assertEqual(datetime(2016, 11, 1), q.start_from)
        self.assertEqual(datetime(2016, 12, 1), q.start_until)
        self.assertEqual('GEE-electric-ConEd-J-SC-02 - Non-Demand Meter', q.rate_class_alias)
        self.assertEqual(6, q.term_months)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(499999, q.limit_volume)
        self.assertEqual(0.07593, q.price)
        self.assertEqual(False, q.purchase_of_receivables)
        self.assertEqual(q.service_type, ELECTRIC)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(datetime(2016, 10, 27), q.valid_from)
        self.assertEqual(datetime(2016, 10, 28), q.valid_until)
        self.assertEqual(datetime(2017, 4, 1), q.start_from)
        self.assertEqual(datetime(2017, 5, 1), q.start_until)
        self.assertTrue('GEE-electric-O&R' in q.rate_class_alias)
        self.assertEqual(24, q.term_months)
        self.assertEqual(250000, q.min_volume)
        self.assertEqual(500000, q.limit_volume)
        self.assertAlmostEqual( 0.07014, q.price, delta=0.000001)
        self.assertEqual(q.service_type, ELECTRIC)


class TestGeeElectricNJ(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = 'GEE Rack Rates_NJ_10.27.2016.xlsx'
    PARSER_CLASS = GEEMatrixParser
    EXPECTED_COUNT = 275

    def test_first(self):
        q_nj_0 = self.quotes[0]
        self.assertEqual(datetime(2016, 10, 27), q_nj_0.valid_from)
        self.assertEqual(datetime(2016, 10, 28), q_nj_0.valid_until)
        self.assertEqual(datetime(2016, 11, 1), q_nj_0.start_from)
        self.assertEqual(datetime(2016, 12, 1), q_nj_0.start_until)
        self.assertEqual(6, q_nj_0.term_months)
        self.assertAlmostEqual(0.10439, q_nj_0.price, delta=0.000001)
        self.assertEqual(q_nj_0.service_type, ELECTRIC)

    def test_last(self):
        q_nj_l = self.quotes[-1]
        self.assertEqual(datetime(2017, 4, 1), q_nj_l.start_from)
        self.assertEqual(datetime(2017, 5, 1), q_nj_l.start_until)
        self.assertEqual(7, q_nj_l.term_months)
        self.assertAlmostEqual(0.06853000000000001, q_nj_l.price, delta=0.000001)
        self.assertEqual(q_nj_l.service_type, ELECTRIC)


class TestGeeElectricMA(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = 'GEE Rack Rates_MA_10.27.2016.xlsx'
    PARSER_CLASS = GEEMatrixParser
    EXPECTED_COUNT = 625

    def test_first(self):
        q_ma_0 = self.quotes[0]
        self.assertEqual(datetime(2016, 10, 27), q_ma_0.valid_from)
        self.assertEqual(datetime(2016, 10, 28), q_ma_0.valid_until)
        self.assertEqual(datetime(2016, 11, 1), q_ma_0.start_from)
        self.assertEqual(datetime(2016, 12, 1), q_ma_0.start_until)
        self.assertEqual(6, q_ma_0.term_months)
        self.assertAlmostEqual(0.09284, q_ma_0.price, delta=0.000001)
        self.assertEqual(q_ma_0.service_type, ELECTRIC)

    def test_2nd_last(self):
        q_ma_l = self.quotes[-2]
        self.assertEqual(datetime(2016, 10, 27), q_ma_l.valid_from)
        self.assertEqual(datetime(2016, 10, 28), q_ma_l.valid_until)
        self.assertEqual(datetime(2017, 4, 1), q_ma_l.start_from)
        self.assertEqual(datetime(2017, 5, 1), q_ma_l.start_until)
        self.assertEqual(24, q_ma_l.term_months)
        self.assertEqual(500000, q_ma_l.min_volume)
        self.assertEqual(999999, q_ma_l.limit_volume)
        self.assertAlmostEqual(0.0936, q_ma_l.price, delta=0.000001)
        self.assertEqual(q_ma_l.service_type, ELECTRIC)

    def test_last(self):
        q_ma_l = self.quotes[-1]
        self.assertEqual(datetime(2017, 3, 1), q_ma_l.start_from)
        self.assertEqual(datetime(2017, 4, 1), q_ma_l.start_until)
        self.assertEqual(6, q_ma_l.term_months)
        self.assertAlmostEqual(0.0781, q_ma_l.price, delta=0.000001)
        self.assertEqual(q_ma_l.service_type, ELECTRIC)

