from datetime import datetime
from unittest import TestCase

from brokerage.quote_parsers.source import SourceMatrixParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestSource(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = '20161114_SPG PJM Small Comm Matrix Table.zip'
    PARSER_CLASS = SourceMatrixParser
    EXPECTED_COUNT = 1381380

    @classmethod
    def get_quote_list(cls):
        """Override to avoid storing all quotes in memory at once
        """
        return [q for i, q in enumerate(cls.parser.extract_quotes())
                if i in (0, cls.EXPECTED_COUNT - 1)]

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 11, 1), q.start_from)
        self.assertEqual(datetime(2016, 12, 1), q.start_until)
        self.assertEqual(1, q.term_months)
        self.assertEqual(datetime(2016, 11, 12), q.valid_from)
        self.assertEqual(datetime(2016, 11, 13), q.valid_until)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(25000, q.limit_volume)
        self.assertEqual('Source-electric-PEPCO DC-Rate GS 3A',
                         q.rate_class_alias)
        self.assertEqual(0.10491, q.price)
        self.assertEqual(q.service_type, ELECTRIC)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(datetime(2018, 4, 1), q.start_from)
        self.assertEqual(datetime(2018, 5, 1), q.start_until)
        self.assertEqual(34, q.term_months)
        self.assertEqual(datetime(2016, 11, 12), q.valid_from)
        self.assertEqual(datetime(2016, 11, 13), q.valid_until)
        self.assertEqual(900000, q.min_volume)
        self.assertEqual(1000000, q.limit_volume)
        self.assertEqual(
            ('Source-electric-DUQUESNE LIGHT-PAL'), q.rate_class_alias)
        self.assertEqual(0.20839, q.price)
        self.assertEqual(q.service_type, ELECTRIC)
