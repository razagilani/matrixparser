from os.path import basename
from datetime import datetime
from unittest import TestCase
from brokerage.quote_parsers import AEPMatrixParser
from test.test_quote_parsers import QuoteParserTest


class TestAEP(QuoteParserTest, TestCase):
    # these variables are accessed in QuoteParserTest.setUp
    FILE_NAME = 'AEP Energy Matrix 3.0 2016-08-25.xls'
    PARSER_CLASS = AEPMatrixParser
    EXPECTED_COUNT = 8721

    def test_aep(self):
        #since there are so many, only check one
        q1 = self.quotes[0]
        self.assertEqual(datetime(2016, 9, 1), q1.start_from)
        self.assertEqual(datetime(2016, 10, 1), q1.start_until)
        self.assertEqual(12, q1.term_months)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(datetime(2016, 8, 25), q1.valid_from)
        self.assertEqual(datetime(2016, 8, 26), q1.valid_until)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(100 * 1000, q1.limit_volume)
        self.assertEqual('AEP-electric-IL-Ameren_Zone_1_CIPS-DS2-SECONDARY', q1.rate_class_alias)
        # self.assertEqual(self.rate_class.rate_class_id, q1.rate_class_id)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(0.05305, q1.price)
