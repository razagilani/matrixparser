from datetime import datetime, timedelta
import re
from time import mktime, strptime

from tablib import formats

from brokerage.model import MatrixQuote
from brokerage.exceptions import ValidationError
from brokerage.quote_parser import QuoteParser, SimpleCellDateGetter, \
    SpreadsheetReader
from brokerage.validation import _assert_match, ELECTRIC
from util.dateutils import date_to_datetime, parse_datetime
from util.monthmath import Month
from util.units import unit_registry


class EntrustMatrixParser(QuoteParser):
    """Parser for Entrust spreadsheet.
    """
    NAME = 'entrust'
    reader = SpreadsheetReader(formats.xlsx)

    EXPECTED_SHEET_TITLES = [
        'IL - ComEd Matrix',
        'OH - Duke Matrix',
        'OH - Dayton Matrix',
        'OH - AEP OP Matrix',
        'OH - AEP CS Matrix',
        'OH - FE CEI Matrix',
        'OH - FE Ohio Edison Matrix',
        'OH - FE Toledo Edison Matrix',
        'PA - PECO Matrix',
        'PA - Duquesne Matrix',
        'PA - FE MetEd Matrix',
        'PA - FE Penelec Matrix',
        'PA - FE WestPenn Matrix',
        'PA - FE Penn Power Matrix',
        'PA - PPL Matrix',
        'MD - BGE Matrix',
        'MD - PEPCO Matrix',
        'NJ - JCPL Matrix',
        'NJ - PSEG Matrix',
        'NY - NYSEG - A Matrix',
        'NY - NYSEG - B Matrix',
        'NY - NYSEG - C Matrix',
        'NY - NYSEG - D Matrix',
        'NY - NYSEG - E Matrix',
        'NY - NYSEG - F Matrix',
        'NY - NYSEG - G Matrix',
        'NY - NYSEG - H Matrix',
        'NY - NYSEG - I Matrix',
        'NY - NATGRID - A Matrix',
        'NY - NATGRID - B Matrix',
        'NY - NATGRID - C Matrix',
        'NY - NATGRID - D Matrix',
        'NY - NATGRID - E Matrix',
        'NY- ConEd - H Matrix',
        'NY- ConEd - I Matrix',
        'NY- ConEd - J Matrix'
    ]

    DATE_REGEX = ('Pricing for Commercial Customers\s+'
                  'for (\w+ \w+ \d\d?, \d\d\d\d)')


    RATE_START_ROW = 9
    TABLE_ROWS = 18
    ORIGINAL_TABLE_ROWS = TABLE_ROWS
    START_DATE_COL = 3
    NO_OF_TERM_COLS = 4
    VOLUME_RANGE_COL = 2
    COL_INCREMENT = 7
    TABLE_HEIGHT = 21  # the expected number of rows in a table
    ORIGINAL_TABLE_HEIGHT = TABLE_HEIGHT
    UTILITY_ROW = 6
    CHANGED_TABLE_PARMS = False


    DATE_ROW = 4
    VOLUME_RANGE_ROW = 7
    TERM_ROW = 8
    QUOTE_START_ROW = 9
    START_COL = 'D'
    PRICE_START_COL = 'E'
    DATE_COL = 'C'
    ROUNDING_DIGITS = 4
    # certain columns have term length in a different place
    # (indices are used instead of letters to enable comparison)
    # each of the prices has a corresponding term in the cell whose row is
    # the same and whose column is at the same index in the second list
    SWEET_SPOT_PRICE_COLS = [8, 15, 22, 29]
    SWEET_SPOT_TERM_COLS = [x + 1 for x in SWEET_SPOT_PRICE_COLS]

    VOLUME_RANGE_COLS = ['E', 'L', 'S', 'Z']

    EXPECTED_ENERGY_UNIT = unit_registry.kWh

    date_getter = SimpleCellDateGetter(0, DATE_ROW, 'C', DATE_REGEX)

    def process_table(self, sheet, row, col, rate_class_alias, valid_from,
            valid_until, min_volume, limit_volume, term_row):
        """
        Extracts quotes from a table
        :param sheet: the sheet number or title
        :param row: the starting row of the table containing quotes
        :param col: the starting column of the table containing quotes
        :param rate_class_alias: rate class alias for the quotes in the table
        :param valid_from: the starting date from which the quote becomes valid
        :param valid_until: the date at which the quotes becomes invalid
        :param min_volume: the minimum volume for the quote
        :param limit_volume: the maximum volume for the quote
        :param term_row: the row at which the term of the quote is located
        :return yield a quote object
        """

        for table_row in xrange(row, row + self.TABLE_ROWS):
            start_from = self._reader.get(sheet, table_row,
                                          self.START_DATE_COL, (datetime, type(None), unicode))
            if start_from is None:
                # table is shorter
                # change table rows and height
                self.CHANGED_TABLE_PARMS = True
                self.TABLE_ROWS = table_row - self.RATE_START_ROW
                self.TABLE_HEIGHT = self.TABLE_ROWS + 3
                return
            elif isinstance(start_from, unicode):
                return
            start_until = date_to_datetime((Month(start_from) + 1).first)
            for price_col in xrange(col + 2, col + 2 + self.NO_OF_TERM_COLS):
                term = self._reader.get(sheet, term_row, price_col, int)
                price = self._reader.get(sheet, table_row, price_col, (float, type(None), unicode))
                if price is None or isinstance(price, unicode):
                    continue
                yield MatrixQuote(start_from=start_from,
                    start_until=start_until, term_months=term,
                    valid_from=valid_from, valid_until=valid_until,
                    min_volume=min_volume, limit_volume=limit_volume,
                    purchase_of_receivables=False, price=price,
                    rate_class_alias=rate_class_alias, service_type=ELECTRIC,
                    file_reference='%s %s,%s' % (
                        self.file_name, sheet, table_row))


    def _validate(self):
        # EXPECTED_SHEET_TITLES and EXPECTED_CELLS are not used because
        # there are many sheets the titles change. instead check cells here.
        for sheet in self.reader.get_sheet_titles():
            for row, col, regex in [
                (4, 'C', self.DATE_REGEX),
                (7, 'E', 'Term \(Months\)'),
                (8, 'D', 'Start Month')
            ]:
                _assert_match(
                    regex, self.reader.get(sheet, row, col, basestring))


        # since only the first sheet is the official source of the date,
        # make sure all others have the same date in them
        all_dates = [
            self.reader.get(sheet, self.DATE_ROW, self.DATE_COL, object) for
            sheet in self.reader.get_sheet_titles()]
        if not all(all_dates[0] == d for d in all_dates):
            raise ValidationError('Dates are not the same in all sheets')


    def _process_sheet(self, sheet):

        for table_start_row in xrange(self.RATE_START_ROW,
                                      self._reader.get_height(sheet),
                                      self.TABLE_HEIGHT):
            term_row = table_start_row - 1
            for col in xrange(self.VOLUME_RANGE_COL,
                              self._reader.get_width(sheet),
                              self.COL_INCREMENT):
                volume_column = self._reader.get(sheet, table_start_row, col, object)
                if volume_column is not None and 'kWh' in volume_column:
                    min_volume, limit_volume = self._extract_volume_range(
                        sheet, table_start_row, col,
                        r'(?P<low>[\d,]+)'
                        r'(?: - |-)(?P<high>[\d,]+)'
                        r'(?: kWh)',
                        expected_unit=unit_registry.kwh,
                        target_unit=unit_registry.kwh)
                    rate_class_alias = 'Entrust-electric-'
                    rate_class_alias += self._reader.get(sheet,
                                                     self.UTILITY_ROW,
                                                     col + 2,
                                                     basestring)
                else:
                    continue
                quotes = self.process_table(sheet, table_start_row, col,
                                            rate_class_alias, self._valid_from,
                                            self._valid_until, min_volume,
                                            limit_volume, term_row)
                for quote in quotes:
                        yield quote

    def _extract_quotes(self):
        for sheet in self.reader.get_sheet_titles():
            if self.CHANGED_TABLE_PARMS:
                self.TABLE_HEIGHT = self.ORIGINAL_TABLE_HEIGHT
                self.TABLE_ROWS = self.ORIGINAL_TABLE_ROWS
                self.CHANGED_TABLE_PARMS = False
            for quote in self._process_sheet(sheet):
                yield quote
