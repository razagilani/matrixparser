from datetime import datetime

from tablib import formats
from brokerage.spreadsheet_reader import SpreadsheetReader
from brokerage.validation import _assert_true

from util.dateutils import date_to_datetime
from util.monthmath import Month
from brokerage.model import MatrixQuote
from brokerage.quote_parser import QuoteParser, StartEndCellDateGetter
from util.units import unit_registry


class MajorEnergyElectricSheetParser(QuoteParser):
    """Used by MajorEnergyMatrixParser for handling only the sheet that contains
    electricity quotes.
    """
    NAME = ''
    reader = SpreadsheetReader(formats.xlsx)

    HEADER_ROW = 20
    QUOTE_START_ROW = 21
    START_COL = 'B'
    TERM_COL = 'C'
    STATE_COL = 'D'
    UTILITY_COL = 'E'
    ZONE_COL = 'F'
    PRICE_START_COL = 6
    PRICE_END_COL = 9

    SHEET = 'Commercial E'
    EXPECTED_CELLS = [
        # (SHEET, 11, 'B',
        #  'Transfer Rates below include all applicable fees \(SUT/GRT/POR\)\s+To '
        #  'apply these fees to your agent fee please use calculator above'),
        (SHEET, HEADER_ROW - 1, 'G', 'Annual KWH Usage Tier'),
        (SHEET, HEADER_ROW, 'B', 'Start'),
        (SHEET, HEADER_ROW, 'C', 'Term'),
        (SHEET, HEADER_ROW, 'D', 'State'),
        (SHEET, HEADER_ROW, 'E', 'Utility'),
        (SHEET, HEADER_ROW, 'F', 'Zone'),
    ]

    # spreadsheet says "kWh usage tier" but the numbers are small, so they
    # probably are MWh
    EXPECTED_ENERGY_UNIT = unit_registry.MWh

    date_getter = StartEndCellDateGetter(SHEET, 3, 'C', 3, 'E', None)

    def _extract_quotes(self):
        # note: these are NOT contiguous. the first two are "0-74" and
        # "75-149" but they are contiguous after that. for now, assume they
        # really mean what they say.
        volume_ranges = [
            self._extract_volume_range(self.SHEET, self.HEADER_ROW, col,
                                       r'(?P<low>\d+)\s*-\s*(?P<high>\d+)',
                                       unit_registry.MWh, unit_registry.kWh)
            for col in xrange(self.PRICE_START_COL, self.PRICE_END_COL + 1)]

        for row in xrange(self.QUOTE_START_ROW,
                          self.reader.get_height(self.SHEET) + 1):
            # TODO use time zone here
            start_from = self.reader.get(self.SHEET, row, self.START_COL,
                                         datetime)
            start_until = date_to_datetime((Month(start_from) + 1).first)

            utility = self.reader.get(self.SHEET, row, self.UTILITY_COL,
                                      basestring)
            state = self.reader.get(self.SHEET, row, self.STATE_COL,
                                    basestring)
            zone = self.reader.get(self.SHEET, row, self.ZONE_COL,
                                   (basestring, type(None)))
            if zone is None:
                zone = ''
            rate_class_alias_parts = ['electric', state, utility, zone]
            rate_class_alias = 'Major-%s' % '-'.join(rate_class_alias_parts)

            term_months = self.reader.get(self.SHEET, row, self.TERM_COL, int)

            for col in xrange(self.PRICE_START_COL, self.PRICE_END_COL + 1):
                # for gas, term is different for each column
                # (this could be done one instead of in a loop)
                min_vol, max_vol = volume_ranges[col - self.PRICE_START_COL]
                price = self.reader.get(self.SHEET, row, col, (int, float))
                yield MatrixQuote(
                    start_from=start_from, start_until=start_until,
                    term_months=term_months, valid_from=self._valid_from,
                    valid_until=self._valid_until, min_volume=min_vol,
                    limit_volume=max_vol, purchase_of_receivables=False,
                    rate_class_alias=rate_class_alias, price=price,
                    service_type='electric', file_reference='%s %s,%s,%s' % (
                        self.file_name, self.SHEET, row, col))


class MajorEnergyGasSheetParser(QuoteParser):
    """Used by MajorEnergyMatrixParser for handling only the sheet that contains
    gas quotes.
    """
    NAME = ''
    reader = SpreadsheetReader(formats.xlsx)

    HEADER_ROW = 17
    QUOTE_START_ROW = 18
    START_COL = 'C'
    UTILITY_COL = 'B'
    PRICE_START_COL = 'E'
    PRICE_END_COL = 'H'

    SHEET = 'NG R & SC'
    EXPECTED_CELLS = [
        (SHEET, HEADER_ROW, START_COL, 'Start'),
        (SHEET, HEADER_ROW, UTILITY_COL, 'Utility'),
    ]

    date_getter = StartEndCellDateGetter(SHEET, 3, 'C', 3, 'E', None)

    def _extract_quotes(self):
        for row in xrange(self.QUOTE_START_ROW,
                          self.reader.get_height(self.SHEET) + 1):
            # todo use time zone here
            start_from = self.reader.get(self.SHEET, row, self.START_COL,
                                         (datetime, basestring))
            # one example of the file repeated the column headers in the
            # first row of quotes, instead of actual quote data. probably a
            # mistake that they'll fix later. handle it by skipping the row.
            if start_from == 'Start':
                continue
            else:
                _assert_true(isinstance(start_from, datetime))
            start_until = date_to_datetime((Month(start_from) + 1).first)
            utility = self.reader.get(self.SHEET, row, self.UTILITY_COL,
                                      basestring)
            rate_class_alias_parts = ['gas', utility]
            rate_class_alias = 'Major-%s' % '-'.join(rate_class_alias_parts)

            for col in self.reader.column_range(
                    self.PRICE_START_COL, self.reader.get_width(self.SHEET), inclusive=False):
                if self.reader.get(self.SHEET, self.HEADER_ROW, col, object) is None:
                    # past last column
                    continue

                # for gas, term is different for each column
                # (this could be done one instead of in a loop)
                term_months = self.reader.get_matches(
                    self.SHEET, self.HEADER_ROW, col, '(\d+) Months', int)
                price = self.reader.get(self.SHEET, row, col,
                                        (int, float, type(None), basestring))
                # skip blank cells (may be blank or None)
                if price in (None, ''):
                    continue
                _assert_true(isinstance(price, (float, int)))

                yield MatrixQuote(
                    start_from=start_from,
                    start_until=start_until, term_months=term_months,
                    valid_from=self._valid_from, valid_until=self._valid_until,
                    # hard-coded volume range values come from email body
                    min_volume=0, limit_volume=50000,
                    purchase_of_receivables=False,
                    rate_class_alias=rate_class_alias, price=price,
                    service_type='gas',
                    file_reference='%s,%s,%s' % (self.SHEET, row, col))


class MajorEnergyMatrixParser(QuoteParser):
    """Parser for Major Energy spreadsheet. This has two sheets for electric
    and gas quotes, which have so little overlap that they are implemented in
    separate classes.

    This design may not be very good because it loads the same file multiple
    times, and because there is still some code duplication between the two
    classes that should be eliminated. But it works well enough.
    """
    NAME = 'major'
    reader = SpreadsheetReader(formats.xlsx)

    # only validation that applies to the entire file goes in this class.
    # beware of hidden sheet that contains similar data
    EXPECTED_SHEET_TITLES = ['Commercial E', 'NG R & SC']

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self._electric_parser = MajorEnergyElectricSheetParser(*args, **kwargs)
        self._gas_parser = MajorEnergyGasSheetParser(*args, **kwargs)

    def load_file(self, quote_file, file_name, matrix_format):
        super(self.__class__, self).load_file(quote_file, file_name, matrix_format)
        self._electric_parser.load_file(quote_file, file_name, matrix_format)
        self._gas_parser.load_file(quote_file, file_name, matrix_format)

    def _validate(self):
        self._electric_parser.validate()
        self._gas_parser.validate()

    def _extract_quotes(self):
        for quote in self._electric_parser.extract_quotes():
            yield quote
        for quote in self._gas_parser.extract_quotes():
            yield quote
