from unittest import TestCase
from datetime import datetime
from mock import Mock
from brokerage.quote_parsers.agera_electric import AgeraElectricMatrixParser
from brokerage.quote_parsers.agera_gas import AgeraGasMatrixParser
from brokerage.validation import GAS, ELECTRIC
from test.test_quote_parsers import QuoteParserTest


class AgeraElectricTest(QuoteParserTest, TestCase):
    FILE_NAME = 'Back To School MATRIX_2016-10-25.xlsx'
    ALIASES = [
        'Agera-Electric-COMED',
        'Agera-Electric-AEP OHIO',
        'Agera-Electric-COMMONWEALTH-NS'
    ]
    PARSER_CLASS = AgeraElectricMatrixParser
    MATRIX_FORMAT = Mock(
        matrix_attachment_name='Back To School MATRIX_'
                               '(?P<date>\d\d\d\d+-\d+-\d+)\s*\..+')
    EXPECTED_COUNT = 700

    def test_agera_gas(self):
        q = self.quotes[0]
        self.assertEqual(datetime(2016, 11, 1), q.start_from)
        self.assertEqual(datetime(2016, 12, 1), q.start_until)
        self.assertEqual(12, q.term_months)
        self.assertEqual(datetime(2016, 10, 26), q.valid_from)
        self.assertEqual(datetime(2016, 11, 2), q.valid_until)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(2000000, q.limit_volume)
        self.assertEqual(self.ALIASES[0], q.rate_class_alias)
        self.assertEqual(0.0593, q.price)
        self.assertEqual(q.service_type, ELECTRIC)
        self.assertEqual(q.dual_billing, False)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())

        q1 = self.quotes[1]
        self.assertEqual(datetime(2016, 11, 1), q1.start_from)
        self.assertEqual(datetime(2016, 12, 1), q1.start_until)
        self.assertEqual(18, q1.term_months)
        self.assertEqual(datetime(2016, 10, 26), q1.valid_from)
        self.assertEqual(datetime(2016, 11, 2), q1.valid_until)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(2000000, q1.limit_volume)
        self.assertEqual(self.ALIASES[0], q1.rate_class_alias)
        self.assertEqual(0.0613, q1.price)
        self.assertEqual(q1.service_type, ELECTRIC)
        self.assertEqual(q1.dual_billing, False)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())

        q2 = self.quotes[699]
        self.assertEqual(datetime(2017, 3, 1), q2.start_from)
        self.assertEqual(datetime(2017, 4, 1), q2.start_until)
        self.assertEqual(36, q2.term_months)
        self.assertEqual(datetime(2016, 10, 26), q2.valid_from)
        self.assertEqual(datetime(2016, 11, 2), q2.valid_until)
        self.assertEqual(0, q2.min_volume)
        self.assertEqual(2000000, q2.limit_volume)
        self.assertEqual(self.ALIASES[2], q2.rate_class_alias)
        self.assertEqual(0.0918500000000003, q2.price)
        self.assertEqual(q2.service_type, ELECTRIC)
        self.assertEqual(q2.dual_billing, False)
        self.assertEqual(datetime.utcnow().date(), q2.date_received.date())

