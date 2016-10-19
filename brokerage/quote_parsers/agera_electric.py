from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from monthdelta import monthdelta

from tablib import formats

from brokerage.model import MatrixQuote
from brokerage.model import MatrixQuote
from brokerage.validation import ELECTRIC, GAS
from brokerage.quote_parser import QuoteParser, SpreadsheetReader, \
    FileNameDateGetter
from util.dateutils import parse_datetime
from util.units import unit_registry


class AgeraElectricMatrixParser(QuoteParser):
    NAME = 'agera-electric'
    reader = SpreadsheetReader(formats.xlsx)

    EXPECTED_SHEET_TITLES = [
        'Matrix'
    ]
    SHEET = 'Matrix'

    HEADER_ROW = 14

    EXPECTED_CELLS = [
        (SHEET, 10, 'A', 'I.The following state includes GRT: PA'),
        #(SHEET, 10, 'D', 'Sales Commission Add-On $/kWh'),
        #(SHEET, 11, 'D', 'Total Add-On $/kWh'),
        #(SHEET, 11, 'A', 'I.The following state includes SUT: NJ'),
        #(SHEET, 12, 'A', 'II.All prices are quoted in $/kWh'),
        (SHEET, 13, 'F', "Dual Billing"),
        (SHEET, 13, 'J', "Consolidated Billing"),
        (SHEET, HEADER_ROW, 'A', 'START_DATE'),
        (SHEET, HEADER_ROW, 'B', 'END_DATE'),
        (SHEET, HEADER_ROW, 'C', 'TERM'),
        (SHEET, HEADER_ROW, 'D', 'LDC'),
        (SHEET, HEADER_ROW, 'E', 'PRODUCT'),
        (SHEET, HEADER_ROW, 'F', 'STANDARD'),
        (SHEET, HEADER_ROW, 'G', '50% PURE WIND'),
        (SHEET, HEADER_ROW, 'H', '100% PURE WIND'),
        (SHEET, HEADER_ROW, 'J', 'STANDARD'),
        (SHEET, HEADER_ROW, 'K', '50% PURE WIND'),
        (SHEET, HEADER_ROW, 'L', '100% PURE WIND')
    ]
    # TODO
    EXPECTED_ENERGY_UNIT = unit_registry.kWh

    date_getter = FileNameDateGetter()

    QUOTE_START_ROW = 15
    RATE_CLASS_ALIAS_COLS = 'D'
    START_COL = 'A'
    END_COL = 'B'
    TERM_COL = 'C'
    UTILITY_COL = 'D'
    NON_CONSOLIDATED_PRICE_COL = 'F'
    CONSOLIDATED_PRICE_COL = 'J'
    MAX_VOLUME = 2000000
    MIN_VOLUME = 0


    def _extract_quotes(self):
        for row in xrange(self.QUOTE_START_ROW, self.reader.get_height(
                self.SHEET)):
            rate_class_alias = 'Agera-Electric-' + '-'.join(
                    self.reader.get(self.SHEET, row, col, basestring) for col in
                    self.RATE_CLASS_ALIAS_COLS)
            start_from = parse_datetime(self.reader.get(self.SHEET, row, self.START_COL,
                                         basestring))

            start_until = start_from + monthdelta(1)
            start_until = start_until.replace(day=1)

            term = self.reader.get(self.SHEET, row, self.TERM_COL,
                                        int)
            cons_price = self.reader.get(self.SHEET, row,
                                    self.CONSOLIDATED_PRICE_COL,
                                    float)

            #non_cons_price = self.reader.get(self.SHEET, row,
            #                        self.NON_CONSOLIDATED_PRICE_COL,
            #                        float)

            yield MatrixQuote(
                start_from=start_from, start_until=start_until,
                term_months=term, dual_billing=False,
                min_volume=self.MIN_VOLUME, limit_volume = self.MAX_VOLUME,
                rate_class_alias=rate_class_alias, price=cons_price,
                valid_from=self._valid_from, valid_until=self._valid_until,
                service_type=ELECTRIC, file_reference='%s %s,%s,%s' % (
                    self.file_name, self.SHEET, row, self.CONSOLIDATED_PRICE_COL))

            # We only want consolidated price

            # yield MatrixQuote(
            #     start_from=start_from, start_until=start_until,
            #     term_months=term, dual_billing=True,
            #     min_volume=self.MIN_VOLUME, limit_volume = self.MAX_VOLUME,
            #     rate_class_alias=rate_class_alias, price=non_cons_price,
            #     valid_from=self._valid_from, valid_until=self._valid_until,
            #     service_type=ELECTRIC, file_reference='%s %s,%s,%s' % (
            #         self.file_name, self.SHEET, row, self.NON_CONSOLIDATED_PRICE_COL))
