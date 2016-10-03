from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers.source import SourceMatrixParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestSource(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = '20161003_SPG PJM Small Comm Matrix Table.zip'
    PARSER_CLASS = SourceMatrixParser
    EXPECTED_COUNT = 762048

    @classmethod
    def get_quote_list(cls):
        """Override to avoid storing all quotes in memory at once
        """
        return [q for i, q in enumerate(cls.parser.extract_quotes())
                if i in (0, cls.EXPECTED_COUNT - 1)]

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 10, 1), q.start_from)
        self.assertEqual(datetime(2016, 11, 1), q.start_until)
        self.assertEqual(1, q.term_months)
        self.assertEqual(datetime(2016, 10, 1), q.valid_from)
        self.assertEqual(datetime(2016, 10, 2), q.valid_until)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(25000, q.limit_volume)
        self.assertEqual('Source-electric-PEPCO DC-Rate GS 3A',
                         q.rate_class_alias)
        self.assertEqual(0.10288, q.price)
        self.assertEqual(q.service_type, ELECTRIC)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(datetime(2017, 9, 1), q.start_from)
        self.assertEqual(datetime(2017, 10, 1), q.start_until)
        self.assertEqual(36, q.term_months)
        self.assertEqual(datetime(2016, 10, 1), q.valid_from)
        self.assertEqual(datetime(2016, 10, 2), q.valid_until)
        self.assertEqual(900000, q.min_volume)
        self.assertEqual(1000000, q.limit_volume)
        self.assertEqual(
            ('Source-electric-Atlantic City Electric-Rate SPL\n'
            'Street and Private Lighting'), q.rate_class_alias)
        self.assertEqual(0.10041, q.price)
        self.assertEqual(q.service_type, ELECTRIC)
