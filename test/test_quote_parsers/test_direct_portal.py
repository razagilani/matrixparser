from datetime import datetime
from unittest import TestCase

from mock import Mock

from brokerage.quote_parsers import DirectPortalMatrixParser
from brokerage.validation import ELECTRIC, GAS
from test.test_quote_parsers import QuoteParserTest


class TestDirectPortal(QuoteParserTest, TestCase):

    FILE_NAME = 'Direct Energy Small Business Prices 5-17-16.xlsx'
    PARSER_CLASS = DirectPortalMatrixParser
    MATRIX_FORMAT = Mock(matrix_attachment_name='.*(?P<date>\d+-\d+-\d+).xlsx')
    # TODO: quotes are temporarily duplicated 4 times as workaround for
    # front-end bug in Team Portal. remove the "* 4" when this is fixed.
    EXPECTED_COUNT = 154 * 4

    def check_every_quote(self, q):
        self.assertEqual(q.valid_from, datetime(2016, 5, 17))
        self.assertEqual(q.valid_until, datetime(2016, 6, 1))
        self.assertEqual(0, q.min_volume)
        if q.service_type == ELECTRIC:
            self.assertEqual(750000, q.limit_volume)
        else:
            self.assertEqual(GAS, q.service_type)
            self.assertEqual(150000, q.limit_volume)

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual('Direct Energy Small Business-electric-CT-CTE-',
                         q.rate_class_alias)
        self.assertEqual(q.term_months, 12)
        self.assertEqual(q.min_volume, 0)
        self.assertEqual(q.price, .0759)
        self.assertEqual(ELECTRIC, q.service_type)

        # TODO: start period should really be 4 months long
        self.assertEqual(datetime(2016, 5, 1), q.start_from)
        self.assertEqual(datetime(2016, 6, 1), q.start_until)

    def test_none_rca(self):
        # the quote in row 4 has None in column D, which should be
        # represented as "" (instead of "None") in the rate class alias
        q = next(
            quote for quote in self.quotes if '4,G' in quote.file_reference)
        self.assertEqual('Direct Energy Small Business-electric-CT-CTE-',
                         q.rate_class_alias)
        self.assertEqual(q.term_months, 18)
        self.assertEqual(q.min_volume, 0)
        self.assertEqual(q.price, .0829)
        self.assertEqual(ELECTRIC, q.service_type)

    def test_gas_therm(self):
        # first gas quote: unit is therm
        q = next(
            quote for quote in self.quotes if '16,G' in quote.file_reference)
        self.assertEqual(0.399, q.price)
        self.assertEqual(GAS, q.service_type)

    def test_gas_mcf(self):
        # first gas quote whose unit is mcf; price must be converted to $/therm
        q = next(
            quote for quote in self.quotes if '83,G' in quote.file_reference)
        self.assertEqual(0.389, q.price)
        self.assertEqual(GAS, q.service_type)

    def test_gas_ccf(self):
        # first gas quote whose unit is ccf; price must be converted to $/therm
        q = next(
            quote for quote in self.quotes if '87,G' in quote.file_reference)
        self.assertEqual(0.389, q.price)
        self.assertEqual(GAS, q.service_type)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(q.term_months, 24)
        self.assertEqual('Direct Energy Small Business-electric-PA-WPE-',
                         q.rate_class_alias)
        self.assertEqual(q.price, .0659)
        self.assertEqual(ELECTRIC, q.service_type)
