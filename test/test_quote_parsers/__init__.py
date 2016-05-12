"""This module contains tests for individual QuoteParser subclasses. Each
test is based on an example file in the "quote_files" directory.
"""
from abc import ABCMeta
from collections import defaultdict
from datetime import datetime
from os.path import join

from mock import Mock

from brokerage import ROOT_PATH

DIRECTORY = join(ROOT_PATH, 'test', 'quote_files')

class QuoteParserTest(object):
    """Base for TestCase classes that test QuoteParsers. Subclasses should
    inherit from both this and TestCase (with TestCase second).
    """
    __metaclass__ = ABCMeta

    # QuoteParser subclass to use
    PARSER_CLASS = None

    # optional MatrixFormat object or Mock that contains any data that the
    # QuoteParser needs for parsing, such as a matrix_attachment_name regex for
    # extracting dates from a file name
    MATRIX_FORMAT = None

    # name of example quote file
    FILE_NAME = None

    # number of quotes extracted from the file
    EXPECTED_COUNT = None

    @classmethod
    def get_quote_list(cls):
        """Subclasses can override to pick only certain quotes instead of all.
        """
        return list(cls.parser.extract_quotes())

    @classmethod
    def setUpClass(cls):
        """Shared setup for all QuoteParsers.
        """
        # this mock replaces the brokerage.brokerate_model module to avoid
        # accessing the database
        dao = Mock()
        dao.load_rate_class_aliases = Mock(
            return_value=defaultdict(lambda: [1]))

        cls.parser = cls.PARSER_CLASS(brokerage_dao=dao)
        assert cls.parser.get_count() == 0

        with open(join(DIRECTORY, cls.FILE_NAME), 'rb') as spreadsheet:
            cls.parser.load_file(spreadsheet, cls.FILE_NAME, cls.MATRIX_FORMAT)
        cls.quotes = cls.get_quote_list()

    def test_validate(self):
        for quote in self.quotes:
            quote.validate()

    def test_date_received(self):
        for quote in self.quotes:
            # TODO: does not work when it's near UTC midnight
            self.assertEqual(datetime.utcnow().date(),
                             quote.date_received.date())

    def test_count(self):
        # get_count() is used instead of len(self.quotes) because not all
        # quotes may be included in that list
        self.assertEqual(self.EXPECTED_COUNT, self.parser.get_count())

    def test_all(self):
        """Apply the assertions in the check_every_quote method to all quotes.
        """
        for q in self.quotes:
            self.check_every_quote(q)

    def check_every_quote(self, q):
        """Override this method to make assertions that will be applied to
        every quote (e.g. validity dates, service type).
        :param q: MatrixQuote, will be set to each quote in the sheet.
        """
        pass

