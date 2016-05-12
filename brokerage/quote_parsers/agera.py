from datetime import datetime, timedelta

from tablib import formats

from brokerage.model import MatrixQuote
from brokerage.model import MatrixQuote
from brokerage.validation import ELECTRIC
from brokerage.quote_parser import QuoteParser, SpreadsheetReader, \
    FileNameDateGetter


class AgeraMatrixParser(QuoteParser):
    NAME = 'agera'
    reader = SpreadsheetReader(formats.xlsx)

    EXPECTED_SHEET_TITLES = [
        'AGERA Variance Sheet',
    ]
    SHEET = 'AGERA Variance Sheet'
    EXPECTED_CELLS = [
        # TODO
    ]
    # TODO
    #EXPECTED_ENERGY_UNIT = unit_registry.kWh

    date_getter = FileNameDateGetter(r'.*(\d+\.\d+\.\d+).*\.xls.*')

    QUOTE_START_ROW = 9
    RATE_CLASS_ALIAS_COLS = 'ABC'
    START_COL = 'D'
    TERM_COL = 'E'
    PRICE_COL = 'G'

    def _extract_quotes(self):
        for row in xrange(self.QUOTE_START_ROW, self.reader.get_height(
                self.SHEET)):
            rate_class_alias = '-'.join(
                    self.reader.get(self.SHEET, row, col, basestring) for col in
                    self.RATE_CLASS_ALIAS_COLS)
            start_from = self.reader.get(self.SHEET, row, self.START_COL,
                                         datetime)
            start_until = start_from + timedelta(days=1)
            term = self.reader.get(self.SHEET, row, self.TERM_COL, int)
            price = self.reader.get(self.SHEET, row, self.PRICE_COL,
                                    (float, int))
            rate_class_ids = self.get_rate_class_ids_for_alias(rate_class_alias)
            for rate_class_id in rate_class_ids:
                quote = MatrixQuote(
                    start_from=start_from, start_until=start_until,
                    term_months=term, valid_from=self._valid_from,
                    valid_until=self._valid_until,
                    rate_class_alias=rate_class_alias, price=price,
                    service_type=ELECTRIC, file_reference='%s %s,%s,%s' % (
                        self.file_name, self.SHEET, row, self.PRICE_COL))
                # TODO: rate_class_id should be determined automatically
                # by setting rate_class
                if rate_class_id is not None:
                    quote.rate_class_id = rate_class_id
                print quote
                yield quote
