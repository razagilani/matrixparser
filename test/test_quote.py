from datetime import datetime
from unittest import TestCase

from brokerage.model import Quote, MatrixQuote
from brokerage.exceptions import ValidationError
from brokerage.model import Quote, MatrixQuote
from brokerage.validation import GAS, ELECTRIC


class QuoteTest(TestCase):
    """Unit tests for Quote.
    """
    def setUp(self):
        self.quote = Quote(
            service_type=ELECTRIC,
            start_from=datetime(2000, 3, 1), start_until=datetime(2000, 4, 1),
            term_months=3, valid_from=datetime(2000, 1, 1),
            valid_until=datetime(2000, 1, 2), price=0.1)

class MatrixQuoteTest(TestCase):
    """Unit tests for MatrixQuote.
    """
    def setUp(self):
        self.quote = MatrixQuote(
            service_type=GAS, start_from=datetime(2000, 3, 1),
            start_until=datetime(2000, 4, 1), term_months=3,
            valid_from=datetime(2000, 1, 1), valid_until=datetime(2000, 1, 2),
            price=0.1, min_volume=0, limit_volume=100)

    def test_validate(self):
        self.quote.validate()

        q = self.quote.clone()
        q.start_from = datetime(2000, 4, 1)
        self.assertRaises(ValidationError, q.validate)

        q = self.quote.clone()
        q.valid_until = datetime(2000, 1, 1)
        self.assertRaises(ValidationError, q.validate)

        q = self.quote.clone()
        q.term_months = 0
        self.assertRaises(ValidationError, q.validate)
        q.term_months = 49
        self.assertRaises(ValidationError, q.validate)

        q = self.quote.clone()
        q.price = 0.001
        self.assertRaises(ValidationError, q.validate)
        q.price = 10
        self.assertRaises(ValidationError, q.validate)

    def test_validate(self):
        # min too low
        self.quote.min_volume = -1
        self.quote.limit_volume = 100
        with self.assertRaises(ValidationError):
            self.quote.validate()

        # min too high
        self.quote.min_volume = 7e6
        self.quote.limit_volume = 4e6
        with self.assertRaises(ValidationError):
            self.quote.validate()

        # limit too low
        self.quote.min_volume = 0
        self.quote.limit_volume = 10
        with self.assertRaises(ValidationError):
            self.quote.validate()

        # limit too high
        self.quote.min_volume = 0
        self.quote.limit_volume = 2e7
        with self.assertRaises(ValidationError):
            self.quote.validate()

        # too close together
        self.quote.min_volume = 1
        self.quote.limit_volume = 2
        with self.assertRaises(ValidationError):
            self.quote.validate()

        # crossed
        self.quote.min_volume = 200
        self.quote.limit_volume = 100
        with self.assertRaises(ValidationError):
            self.quote.validate()

        # good
        self.quote.min_volume = 100
        self.quote.limit_volume = 10000
        self.quote.validate()

