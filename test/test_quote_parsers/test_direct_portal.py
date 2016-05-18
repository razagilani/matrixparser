from datetime import datetime
from unittest import TestCase

from mock import Mock

from brokerage.quote_parsers import DirectPortalMatrixParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestDirectPortal(QuoteParserTest, TestCase):

    FILE_NAME = 'Direct Energy Small Business Prices 5-17-16.xlsx'
    PARSER_CLASS = DirectPortalMatrixParser
    MATRIX_FORMAT = Mock(matrix_attachment_name='.*(?P<date>\d+-\d+-\d+).xlsx')
    EXPECTED_COUNT = 154

    def check_every_quote(self, q):
        self.assertEqual(q.valid_from, datetime(2016, 5, 17))
        self.assertEqual(q.valid_until, datetime(2016, 5, 18))

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual('Direct Energy Small Business-electric-CT-CTE-',
                         q.rate_class_alias)
        self.assertEqual(q.term_months, 12)
        # self.assertEqual(datetime(2015, 5, 1), q.start_from)
        # self.assertEqual(datetime(2015, 6, 1), q.start_until)
        # self.assertEqual(q.min_volume, 0)
        # self.assertEqual(q.limit_volume, 75000)
        self.assertEqual(q.price, .0759)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(q.term_months, 24)
        # self.assertEqual(datetime(2016, 4, 1), q.start_from)
        # self.assertEqual(datetime(2016, 5, 1), q.start_until)
        # self.assertEqual(q.min_volume, 750000)
        # self.assertEqual(q.limit_volume, 1e6)
        self.assertEqual('Direct Energy Small Business-electric-PA-WPE-',
                         q.rate_class_alias)
        self.assertEqual(q.price, .0659)
