from datetime import datetime, timedelta
from itertools import chain

from tablib import formats

from brokerage.model import MatrixQuote
from brokerage.exceptions import ValidationError
from brokerage.quote_parser import QuoteParser
from brokerage.reader import parse_number
from brokerage.spreadsheet_reader import SpreadsheetReader
from brokerage.validation import _assert_true, _assert_equal, _assert_match
from util.dateutils import date_to_datetime
from util.monthmath import Month

__author__ = 'Bill Van Besien'

class USGEElectricMatrixParser(QuoteParser):
    """Parser for USGE spreadsheet. This one has energy along the rows and
    time along the columns.
    """
    NAME = 'usgeelectric'
    reader = SpreadsheetReader(formats.xlsx)

    TERM_HEADER_ROW = 4
    HEADER_ROW = 5
    RATE_START_ROW = 6
    UTILITY_COL = 0
    VOLUME_RANGE_COL = 3
    RATE_END_COL = 11
    TERM_START_COL = 6
    TERM_END_COL = 28
    LDC_COL = 'A'
    CUSTOMER_TYPE_COL = 'B'
    RATE_CLASS_COL = 'C'

    EXPECTED_SHEET_TITLES = [
        'CT',
        'IL',
        'MA',
        'MD',
        'NJ',
        'NY',
        'OH',
        'PA',
        #'CheatSheet',
    ]


    def _validate(self):
        for sheet in [s for s in self.EXPECTED_SHEET_TITLES if s != 'CheatSheet']:
            start_row = self._find_valid_thru_row(sheet, 2)
            sheet_columns = [
                (sheet, start_row, 2, 'Valid Thru'),
                (sheet, start_row + 2, 0, 'LDC'),
                (sheet, start_row + 2, 1, 'Customer Type'),
                (sheet, start_row + 2, 2, 'RateClass'),
                (sheet, start_row + 2, 3, 'Annual Usage Tier'),
            ]
            for _, row, col, regex in sheet_columns:
                _assert_match(
                    regex, self.reader.get(sheet, row, col, basestring))

    def _find_valid_thru_row(self, sheet, col):
        """
        Return the row index of the 'Valid Thru' token. If the given
        col does not have 'Valid Thru', raise ValueError.
        :param sheet: Sheet name
        :param col: Column index
        :return: First row index containing price data
        """
        for test_row in xrange(0, self.reader.get_height(sheet)):
            # Find the first row containing pricing data.
            cell_val = self.reader.get(sheet, test_row, col, (basestring, type(None)))
            if cell_val and ('Valid Thru' in cell_val):
                return test_row
        raise ValueError("Cannot find start row")

    def _extract_volume_range(self, sheet, row, col):
        below_regex = r'Below ([\d,]+) [kK][wW][hH]'
        normal_regex = r'([\d,]+)-([\d,]+) [kK][wW][hH]'
        try:
            low, high = self.reader.get_matches(sheet, row, col, normal_regex,
                                                (parse_number, parse_number))
        except ValidationError:
            high = self.reader.get_matches(sheet, row, col, below_regex,
                                           parse_number)
            low = 0
        return low, high
    # TODO: can't use superclass method here because there's more than one
    # regex to use, with different behavior for each one.

    def _extract_quotes(self):
        # not every sheet has the validity date on it. get it from the first
        # sheet, then assert that it's the same in every other.
        # the time within that day is on every sheet.
        valid_from = self.reader.get(0, 2, 'D', datetime)

        for sheet in self.EXPECTED_SHEET_TITLES:
            # Sometimes this can be None so we can't force it to expect a basestring
            zone = self.reader.get(sheet, 5, 'E', object)
            if zone == 'Zone':
                zone_col = 'E'
                term_start_col = 6
            else:
                zone_col = None
                term_start_col = 5

            # This is the date at the top of the document in each spreadsheet
            # the validity date must either match the one on the first sheet
            # (above), or be blank
            valid_from_cell_value = self.reader.get(sheet, 2, 'D', object)
            if isinstance(valid_from_cell_value, datetime):
                _assert_equal(valid_from_cell_value, valid_from)
            else:
                _assert_true(valid_from_cell_value is None)
            valid_until = valid_from + timedelta(days=1)

            for row in xrange(self.RATE_START_ROW,
                              self.reader.get_height(sheet) + 1):
                utility = self.reader.get(sheet, row, self.UTILITY_COL,
                                          (basestring, type(None)))
                if utility is None:
                    continue

                ldc = self.reader.get(sheet, row, self.LDC_COL,
                                      (basestring, type(None)))
                customer_type = self.reader.get(
                    sheet, row, self.CUSTOMER_TYPE_COL, (basestring, type(None)))
                rate_class = self.reader.get(sheet, row, self.RATE_CLASS_COL,
                                             (basestring, type(None)))
                if zone_col:
                    zone = self.reader.get(sheet, row, zone_col, basestring)
                else:
                    zone = ""
                rate_class_alias = 'USGE-electric-%s' % '-'.join(
                        [ldc, customer_type, rate_class, zone])
                min_volume, limit_volume = self._extract_volume_range(
                    sheet, row, self.VOLUME_RANGE_COL)

                for term_col in self.reader.column_range(
                        term_start_col, self.reader.get_width(sheet), 7):
                    # empty cell where header is expected means end of relevant
                    # columns in this sheet
                    if self.reader.get(sheet, self.TERM_HEADER_ROW, term_col,
                                       object) is None:
                        break
                    term = self.reader.get_matches(
                        sheet, self.TERM_HEADER_ROW, term_col,
                        '(\d+) Months Beginning in:', int)

                    end_col = min(self.reader.get_width(sheet) - 1, term_col + 5)
                    for i in self.reader.column_range(term_col, end_col):
                        start_from = self.reader.get(sheet, self.HEADER_ROW,
                                                     i, (type(None),datetime))
                        if start_from is None:
                            continue

                        start_until = date_to_datetime(
                            (Month(start_from) + 1).first)
                        price = self.reader.get(
                            sheet, row, i, (float, type(None), basestring))
                        # some cells are blank
                        # TODO: test spreadsheet does not include this
                        if price is None or price in ('', 'N/A', 'NA'):
                            continue

                        yield MatrixQuote(
                            start_from=start_from, start_until=start_until,
                            term_months=term, valid_from=valid_from,
                            valid_until=valid_until,
                            min_volume=min_volume,
                            limit_volume=limit_volume,
                            purchase_of_receivables=False, price=price,
                            rate_class_alias=rate_class_alias,
                            service_type='electric',
                            file_reference='%s %s,%s,%s' % (
                                self.file_name, sheet, row, i))
