from unittest import TestCase
from datetime import datetime
from mock import Mock
from brokerage.quote_parsers.agera_electric import AgeraElectricMatrixParser
from brokerage.quote_parsers.agera_gas import AgeraGasMatrixParser
from brokerage.validation import GAS, ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class AgeraElectricTest(QuoteParserTest, TestCase):
    FILE_NAME = 'Back To School MATRIX_2016-09-07.xlsx'
    ALIASES = [
        'Agera-Electric-COMED',
        'Agera-Electric-AEP OHIO'
    ]
    PARSER_CLASS = AgeraElectricMatrixParser
    MATRIX_FORMAT = Mock(
        matrix_attachment_name='Back To School MATRIX_'
                               '(?P<date>\d\d\d\d+-\d+-\d+)\s*\..+')
    EXPECTED_COUNT = 1758

    def test_agera_gas(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 9, 1), q.start_from)
        self.assertEqual(datetime(2017, 8, 31), q.start_until)
        self.assertEqual(12, q.term_months)
        self.assertEqual(datetime(2016, 9, 7), q.valid_from)
        self.assertEqual(datetime(2016, 9, 15), q.valid_until)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(2000000, q.limit_volume)
        self.assertEqual(self.ALIASES[0], q.rate_class_alias)
        self.assertEqual(0.056600000000000004, q.price)
        self.assertEqual(q.service_type, ELECTRIC)
        self.assertEqual(q.dual_billing, False)

        q1 = self.quotes[1]
        self.assertEqual(datetime(2016, 9, 1), q1.start_from)
        self.assertEqual(datetime(2017, 8, 31), q1.start_until)
        self.assertEqual(12, q1.term_months)
        self.assertEqual(datetime(2016, 9, 7), q1.valid_from)
        self.assertEqual(datetime(2016, 9, 15), q1.valid_until)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(2000000, q1.limit_volume)
        self.assertEqual(self.ALIASES[0], q1.rate_class_alias)
        self.assertEqual(0.05606368842578995, q1.price)
        self.assertEqual(q1.service_type, ELECTRIC)
        self.assertEqual(q1.dual_billing, True)

        q2 = self.quotes[1757]
