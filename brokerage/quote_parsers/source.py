import re
from datetime import timedelta

from tablib import formats

from brokerage.model import MatrixQuote
from brokerage.file_utils import extract_zip
from brokerage.quote_parser import QuoteParser, SpreadsheetReader
from util.dateutils import date_to_datetime, parse_datetime
from util.monthmath import Month
from util.units import unit_registry


class SourceMatrixParser(QuoteParser):
    NAME = 'source'
    reader = SpreadsheetReader(formats.csv)

    HEADER_ROW = 1
    VALID_DATE_COL = 'A'
    RCA_COLS = ['B', 'C']
    START_COL = 'D'
    VOLUME_RANGE_COL = 'E'
    PRICE_START_COL = 'F'
    TERMS = [12, 18, 24, 30, 36]

    SHEET = 0  # CSV has only one sheet

    EXPECTED_CELLS = [
        (SHEET, HEADER_ROW, 'A', 'Date'),
        (SHEET, HEADER_ROW, 'B', 'LDC Name'),
        (SHEET, HEADER_ROW, 'C', 'Rate Class'),
        (SHEET, HEADER_ROW, 'D', 'Start Date'),
        (SHEET, HEADER_ROW, 'E', 'Annual Volume Range \(KWH\)'),
    ]

    def _preprocess_file(self, quote_file, file_name):
        # extract file from zip archive, assuming there's exactly one
        return extract_zip(quote_file)

    def _extract_quotes(self):
        for row in xrange(self.HEADER_ROW + 1,
                          self.reader.get_height(self.SHEET) + 1):
            valid_from = parse_datetime(self.reader.get(
                self.SHEET, row, self.VALID_DATE_COL, basestring))
            rate_class_alias = '-'.join(['Source-electric'] + [self.reader.get(
                self.SHEET, row, col, basestring) for col in self.RCA_COLS])

            # some examples have all blank cells in columns right of the first
            # one with the date. skip these (just one row at a time, in case later
            # rows do contain quotes)
            if self.reader.get(self.SHEET, row, 'B', object) in (None, ''):
                continue

            start_from = parse_datetime(self.reader.get(
                self.SHEET, row, self.START_COL, basestring))
            start_until = date_to_datetime((Month(start_from) + 1).first)

            min_vol, limit_vol = self._extract_volume_range(
                self.SHEET, row, self.VOLUME_RANGE_COL,
                r'(?P<low>[\d,]+)\s*-\s*(?P<high>[\d,]+)', fudge_low=True,
                expected_unit=unit_registry.kWh)

            for col in self.reader.column_range(
                    self.PRICE_START_COL, self.reader.get_width(self.SHEET) -1 ):
                # blank header means end
                if self.reader.get(
                        self.SHEET, self.HEADER_ROW, col, basestring) == '':
                    break
                term = self.reader.get_matches(
                    self.SHEET, self.HEADER_ROW, col, '(\d+)', int)
                if term not in self.TERMS:
                    continue

                if re.match(r'.*N\/A.*',
                            self.reader.get(self.SHEET, row, col, basestring)):
                    continue
                price = self.reader.get_matches(self.SHEET, row, col,
                                                r'\s*\$?(.+)\s*', float)

                yield MatrixQuote(
                    start_from=start_from, start_until=start_until,
                    term_months=term, valid_from=valid_from,
                    valid_until=valid_from + timedelta(days=1),
                    min_volume=min_vol, limit_volume=limit_vol,
                    rate_class_alias=rate_class_alias,
                    price=price, service_type='electric',
                    file_reference='%s %s,%s' % (self.file_name, row, col))
