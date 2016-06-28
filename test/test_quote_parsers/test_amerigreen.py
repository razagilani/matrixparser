from datetime import datetime
from unittest import TestCase

from mock import Mock

from brokerage.quote_parsers import AmerigreenMatrixParser
from brokerage.validation import ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class TestAmerigreen(QuoteParserTest, TestCase):

    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = 'Amerigreen Matrix 6-27-2016 .xlsx'
    PARSER_CLASS = AmerigreenMatrixParser
    MATRIX_FORMAT = Mock(
        matrix_attachment_name='Amerigreen Matrix '
                               '(?P<date>\d+-\d+-\d\d\d\d)\s*\..+')
    EXPECTED_COUNT = 96

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 8, 1), q.start_from)
        self.assertEqual(datetime(2016, 8, 2), q.start_until)
        self.assertEqual(6, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        # quote validity dates come from file name
        self.assertEqual(datetime(2016, 6, 27), q.valid_from)
        self.assertEqual(datetime(2016, 6, 28), q.valid_until)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual('Amerigreen-gas-NY-Con Ed', q.rate_class_alias)
        self.assertEqual(False, q.purchase_of_receivables)
        self.assertEqual(0.4669, q.price)
        self.assertEqual(q.service_type, ELECTRIC)



