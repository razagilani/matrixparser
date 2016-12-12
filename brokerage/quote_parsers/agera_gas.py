from datetime import datetime, timedelta

from tablib import formats

from brokerage.model import MatrixQuote
from brokerage.model import MatrixQuote
from brokerage.validation import ELECTRIC, GAS
from brokerage.quote_parser import QuoteParser, SpreadsheetReader, \
    FileNameDateGetter
from util.dateutils import parse_datetime
from util.units import unit_registry


class AgeraGasMatrixParser(QuoteParser):
    NAME = 'agera-gas'
    reader = SpreadsheetReader(formats.csv)

    EXPECTED_SHEET_TITLES = [

    ]
    SHEET = 0
    EXPECTED_CELLS = [
        (SHEET, 1, 'A', 'state'),
        (SHEET, 1, 'B', 'utility'),
        (SHEET, 1, 'C', 'billing_type'),
        (SHEET, 1, 'D', 'term_mo'),
        (SHEET, 1, 'E', 'earliest_contract_start_date'),
        (SHEET, 1, 'F', 'price'),
        (SHEET, 1, 'G', 'valid_from'),
        (SHEET, 1, 'H', 'valid_until'),
        (SHEET, 1, 'I', 'minimum_annual_volume'),
        (SHEET, 1, 'J', 'maximum_annual_volume')
    ]
    # TODO
    EXPECTED_ENERGY_UNIT = unit_registry.kWh

    #date_getter = FileNameDateGetter(r'.*(\d+\.\d+\.\d+).*\.xls.*')

    QUOTE_START_ROW = 2
    RATE_CLASS_ALIAS_COLS = 'AB'
    START_COL = 'E'
    TERM_COL = 'D'
    PRICE_COL = 'F'
    UTILITY_COL = 'B'
    MAX_VOLUME_COL = 'J'
    MIN_VOLUME_COL = 'I'
    VALID_FROM = 'G'
    VALID_UNTIL = 'H'
    BILLING_TYPE = 'C'
    WEDNESDAY = 2 # datetime.weekday() uses 2 for Wednesday

    def _extract_quotes(self):
        for row in xrange(self.QUOTE_START_ROW, self.reader.get_height(
                self.SHEET) + 1):
            rate_class_alias = 'Agera-Gas-' + '-'.join(
                    self.reader.get(self.SHEET, row, col, basestring) for col in
                    self.RATE_CLASS_ALIAS_COLS)
            start_from = parse_datetime(self.reader.get(self.SHEET, row, self.START_COL,
                                         basestring))

            start_until = start_from + timedelta(days=1)
            valid_from = parse_datetime(self.reader.get(self.SHEET, row, self.VALID_FROM,
                                         basestring))
            week_of_day = valid_from.weekday()
            valid_from = valid_from + timedelta(days=(self.WEDNESDAY - week_of_day))
            valid_until = parse_datetime(self.reader.get(self.SHEET, row, self.VALID_UNTIL,
                                          basestring))
            valid_until = valid_until + timedelta(days=(self.WEDNESDAY - week_of_day + 7))

            min_volume = self.reader.get_matches(self.SHEET, row, self.MIN_VOLUME_COL,
                                         r'\s*\$?(.+)\s*', float)
            max_volume = self.reader.get_matches(self.SHEET, row, self.MAX_VOLUME_COL,
                                         r'\s*\$?(.+)\s*', float)
            term = self.reader.get_matches(self.SHEET, row, self.TERM_COL, '(\d+)',
                                           int)
            price = self.reader.get_matches(self.SHEET, row, self.PRICE_COL,
                                    r'\s*\$?(.+)\s*', float)
            dual_billing = self.reader.get(self.SHEET, row, self.BILLING_TYPE,
                                           basestring)
            dual_billing = True if dual_billing == 'dual' else False
            yield MatrixQuote(
                start_from=start_from, start_until=start_until,
                term_months=term, valid_from=valid_from,
                valid_until=valid_until, dual_billing=dual_billing,
                min_volume=min_volume, limit_volume = max_volume,
                rate_class_alias=rate_class_alias, price=price,
                service_type=GAS, file_reference='%s %s,%s,%s' % (
                    self.file_name, self.SHEET, row, self.PRICE_COL))
