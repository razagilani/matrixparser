from datetime import datetime
from unittest import TestCase, skip

from brokerage.quote_parsers import VolunteerMatrixParser
from brokerage.validation import GAS
from test.test_quote_parsers import QuoteParserTest


class VolunteerTest(QuoteParserTest):
    """Shared variables and method in all the tests below.
    """
    PARSER_CLASS = VolunteerMatrixParser

    # we only want the leftmost column labeled "fixed", which only has 3
    # prices in each file. there are 2 other "fixed" columns but they
    # have invisible text.
    EXPECTED_COUNT = 3

    def check_every_quote(self, q):
        self.assertEqual(datetime(2016, 5, 9), q.valid_from)
        self.assertEqual(datetime(2016, 5, 14), q.valid_until)
        self.assertEqual(datetime(2016, 6, 1), q.start_from)
        self.assertEqual(datetime(2016, 7, 1), q.start_until)
        self.assertEqual(False, q.purchase_of_receivables)
        self.assertEqual(q.service_type, GAS)

        # all quotes have the same volume range
        self.assertEqual(2500, q.min_volume)
        self.assertEqual(6e4, q.limit_volume)

        # only the leftmost "fixed" column has non-invisible prices, so there
        # are only 12-month contracts
        self.assertEqual(12, q.term_months)


class TestDEO(VolunteerTest, TestCase):
    FILE_NAME = 'volunteer/EXCHANGE DEO_MODEL_2016 5-9-16.pdf'

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual('Volunteer-gas-DOMINION EAST OHIO (DEO)',
                         q.rate_class_alias)
        self.assertEqual(3.75 - 0.4, q.price)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(3.39 - 0.2, q.price)


class TestCOH(VolunteerTest, TestCase):
    FILE_NAME = 'volunteer/EXCHANGE_COH MODEL_2016 5-9-16.pdf'

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual('Volunteer-gas-COLUMBIA GAS of OHIO (COH)',
                         q.rate_class_alias)
        self.assertEqual(4.88 - 0.4, q.price)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(4.49 - 0.2, q.price)


class TestCON(VolunteerTest, TestCase):
    FILE_NAME = 'volunteer/EXCHANGE_CON_2016 5-9-16.pdf'

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual('Volunteer-gas-CONSUMERS ENERGY', q.rate_class_alias)
        self.assertEqual(3.8 - 0.2, q.price)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(3.65 - 0.1, q.price)


class TestDTE(VolunteerTest, TestCase):
    FILE_NAME = 'volunteer/EXCHANGE_DTE_2016 5-9-16.pdf'

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual('Volunteer-gas-DTE ENERGY', q.rate_class_alias)
        self.assertEqual(3.75 - 0.2, q.price)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(3.49 - 0.1, q.price)


class TestDUKE(VolunteerTest, TestCase):
    FILE_NAME = 'volunteer/EXCHANGE_DUKE_2016 5-9-16.pdf'

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual('Volunteer-gas-DUKE ENERGY OHIO', q.rate_class_alias)
        self.assertEqual(4.69 - 0.4, q.price)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(4.29 - 0.2, q.price)


class TestPECO(VolunteerTest, TestCase):
    FILE_NAME = 'volunteer/EXCHANGE_PECO_2016 5-9-16.pdf'

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual('Volunteer-gas-PECO ENERGY COMPANY (PECO)',
                         q.rate_class_alias)
        self.assertEqual(4.8 - 0.4, q.price)

    def test_last(self):
        q = self.quotes[-1]
        # TODO: which quote is this?
        self.assertEqual(4.4 - 0.2, q.price)


class TestVEDO(VolunteerTest, TestCase):
    FILE_NAME = 'volunteer/EXCHANGE_VEDO_2016 5-9-16.pdf'

    def test_first(self):
        q = self.quotes[0]
        self.assertEqual('Volunteer-gas-VECTREN ENERGY DELIVERY OHIO (VEDO)',
                         q.rate_class_alias)
        self.assertEqual(4.99 - 0.4, q.price)

    def test_last(self):
        q = self.quotes[-1]
        self.assertEqual(4.69 - 0.2, q.price)
