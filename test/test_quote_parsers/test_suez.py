from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers.suez_electric import SuezElectricParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestSuez(QuoteParserTest, TestCase):
    FILE_NAME = 'suez/OH_MATRIX_2016.05.05.xlsx'
    PARSER_CLASS = SuezElectricParser
    EXPECTED_COUNT = (3651 - 3) * 4

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 6, 1), q.start_from)
        self.assertEqual(datetime(2016, 7, 1), q.start_until)
        self.assertEqual(q.term_months, 6)
        self.assertEqual(q.valid_from, datetime(2016, 5, 5))
        self.assertEqual(q.valid_until, datetime(2016, 5, 6))
        self.assertEqual(q.min_volume, 0)
        self.assertEqual(q.limit_volume, 249999)
        self.assertEqual(q.price, 0.05001)
        self.assertEqual(q.rate_class_alias,
            'Suez-electric-OH-AEPCS-CCCSGS1A,835,830, 831, 836-UCB (GRT Excluded)')
        self.assertEqual(q.service_type, ELECTRIC)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(datetime(2017, 6, 1), q.start_from)
        self.assertEqual(datetime(2017, 7, 1), q.start_until)
        self.assertEqual(q.term_months, 48)
        self.assertEqual(q.valid_from, datetime(2016, 5, 5))
        self.assertEqual(q.valid_until, datetime(2016, 5, 6))
        self.assertEqual(q.min_volume, 700000)
        self.assertEqual(q.limit_volume, 1000000)
        self.assertEqual(q.price, 0.05522)
        self.assertEqual(q.rate_class_alias,
            'Suez-electric-OH-DEOK-TL,TL01-UCB (POR Included)')
        self.assertEqual(q.purchase_of_receivables, True)
        self.assertEqual(q.service_type, ELECTRIC)


class TestSuezWithZone(QuoteParserTest, TestCase):
    FILE_NAME = 'suez/NY_MATRIX_2016.05.05.xlsx'
    PARSER_CLASS = SuezElectricParser
    EXPECTED_COUNT = 25740

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 5, 1), q.start_from)
        self.assertEqual(datetime(2016, 6, 1), q.start_until)
        self.assertEqual(q.term_months, 6)
        self.assertEqual(q.valid_from, datetime(2016, 5, 5))
        self.assertEqual(q.valid_until, datetime(2016, 5, 6))
        self.assertEqual(q.min_volume, 100000)
        self.assertEqual(q.limit_volume, 399999)
        self.assertEqual(q.price, 0.06858)
        self.assertEqual(q.rate_class_alias,
            'Suez-electric-NY-CenHud-E200-E-UCB (POR Included)')
        self.assertEqual(q.purchase_of_receivables, True)
        self.assertEqual(q.service_type, ELECTRIC)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(datetime(2017, 5, 1), q.start_from)
        self.assertEqual(datetime(2017, 6, 1), q.start_until)
        self.assertEqual(q.term_months, 42)
        self.assertEqual(q.valid_from, datetime(2016, 5, 5))
        self.assertEqual(q.valid_until, datetime(2016, 5, 6))
        self.assertEqual(q.min_volume, 800000)
        self.assertEqual(q.limit_volume, 999999)
        self.assertEqual(q.price, 0.0624)
        self.assertEqual(q.rate_class_alias,
            'Suez-electric-NY-RGE-SC7-B-UCB (POR Included)')
        self.assertEqual(q.purchase_of_receivables, True)
        self.assertEqual(q.service_type, ELECTRIC)


class TestSuezMA(QuoteParserTest, TestCase):
    FILE_NAME = 'suez/MA_MATRIX_2016.05.06.xlsx'
    PARSER_CLASS = SuezElectricParser
    EXPECTED_COUNT = 21344

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 5, 1), q.start_from)
        self.assertEqual(datetime(2016, 6, 1), q.start_until)
        self.assertEqual(q.term_months, 6)
        self.assertEqual(q.valid_from, datetime(2016, 5, 6))
        self.assertEqual(q.valid_until, datetime(2016, 5, 7))
        self.assertEqual(q.min_volume, 100000)
        self.assertEqual(q.limit_volume, 399999)
        self.assertEqual(q.price, 0.08579)
        self.assertEqual(q.rate_class_alias, 'Suez-electric-MA-NStar-02, 06-NEMA')
        self.assertEqual(q.purchase_of_receivables, False)
        self.assertEqual(q.service_type, ELECTRIC)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(datetime(2017, 5, 1), q.start_from)
        self.assertEqual(datetime(2017, 6, 1), q.start_until)
        self.assertEqual(q.term_months, 48)
        self.assertEqual(q.valid_from, datetime(2016, 5, 6))
        self.assertEqual(q.valid_until, datetime(2016, 5, 7))
        self.assertEqual(q.min_volume, 800000)
        self.assertEqual(q.limit_volume, 999999)
        self.assertEqual(q.price, 0.07251)
        self.assertEqual(q.rate_class_alias, 'Suez-electric-MA-WMECO-S1, S2-WCMASS')
        self.assertEqual(q.purchase_of_receivables, False)
        self.assertEqual(q.service_type, ELECTRIC)
