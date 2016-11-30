from datetime import timedelta
from tablib import formats

from brokerage.exceptions import ValidationError
from brokerage.model import MatrixQuote
from brokerage.quote_parser import QuoteParser, FileNameDateGetter
from brokerage.spreadsheet_reader import SpreadsheetReader
from brokerage.validation import ELECTRIC, GAS, _assert_equal
from util.dateutils import date_to_datetime
from util.monthmath import Month
from util.units import unit_registry


class DirectPortalMatrixParser(QuoteParser):
    """Parser for Direct Energy Small Business Portal quotes, not to be
    confused with the main Direct Energy matrixf format.
    """
    NAME = 'directportal'
    reader = SpreadsheetReader(formats.xlsx)

    HEADER_ROW = 1
    QUOTE_START_ROW = 2
    RCA_COLS = ['B', 'C', 'D']
    TERM_COL = 'E'
    PRICE_COL = 'F'
    UNIT_COL = 'G'
    KWH_SUBTRACT_AMOUNT = 0.004
    MCF_SUBTRACT_AMOUNT = 0.4
    THM_SUBTRACT_AMOUNT = .04
    SHEET = 'Prices'

    SHEET = 'Prices'
    EXPECTED_SHEET_TITLES = ['Prices', 'Utility Abbreviations']
    EXPECTED_CELLS = [
        (SHEET, HEADER_ROW, 'A', 'Commodity'),
        (SHEET, HEADER_ROW, 'B', 'State'),
        (SHEET, HEADER_ROW, 'C', 'LDC'),
        (SHEET, HEADER_ROW, 'D', 'Zone'),
        (SHEET, HEADER_ROW, 'E', 'Term'),
        (SHEET, HEADER_ROW, 'F', 'Rate Amt'),
        (SHEET, HEADER_ROW, 'G', 'Unit'),
        (SHEET, HEADER_ROW, 'H', 'Cancel Fee'),
    ]



    date_getter = FileNameDateGetter()

    def _extract_quotes(self):

        # TODO:
        # as a temporary workaround for not being able to represent quotes that
        # stay valid until the next batch of quotes is received, we hard-code
        # an expiration date 2 weeks after the start. the actual fix for this is
        # described here: https://nextility.atlassian.net/browse/MATRIX-89
        self._valid_until = self._valid_from + timedelta(days=15)

        for row in xrange(self.QUOTE_START_ROW, self.reader.get_height(self.SHEET) + 1):

            # different volume limits and interpretation of price unit for
            # electric and gas quotes. also different gas quotes have
            # different units.
            commodity = self.reader.get(self.SHEET, row, 'A', basestring).lower()
            unit_name = self.reader.get(self.SHEET, row, self.UNIT_COL,
                                        basestring).lower()
            if commodity == 'power':
                service_type = ELECTRIC
                _assert_equal(unit_name, 'kwh')
                subtract_amount = self.KWH_SUBTRACT_AMOUNT
                expected_unit = target_unit = unit_registry.kWh
                min_vol, limit_vol = 0, 1000000
            elif commodity == 'gas':
                service_type = GAS
                if unit_name in ('thm', 'ccf'):
                    expected_unit = unit_registry.therm
                    subtract_amount = self.THM_SUBTRACT_AMOUNT
                elif unit_name == 'mcf':
                    expected_unit = unit_registry.therm * 10
                    #subtract_amount = self.MCF_SUBTRACT_AMOUNT
                else:
                    raise ValidationError('Unknown gas unit: "%s"' % unit_name)
                target_unit = unit_registry.therm
                min_vol, limit_vol = 0, 100000
            else:
                raise ValidationError(
                    'Expected service type "power" or "gas", found "%s"' %
                    commodity)

            rca_prefix = 'Direct Energy Small Business-' + service_type.lower()
            rca_data = [self.reader.get(self.SHEET, row, col, object) for col in
                        self.RCA_COLS]
            rca = '-'.join(
                [rca_prefix] + ['' if x is None else x for x in rca_data])
            term = self.reader.get(self.SHEET, row, self.TERM_COL, int)
            price = self.reader.get(self.SHEET, row, self.PRICE_COL, float) *\
                    float(target_unit / expected_unit)
            price = price - subtract_amount
            # TODO: quotes are temporarily duplicated 4 times as a workaround
            # for a bug where Team Portal cannot show quotes that started
            # before the current month
            start = Month(self._valid_from).first
            for start_from, start_until in [
                (start, (Month(start) + 1).first),
                ((Month(start) + 1).first, (Month(start) + 2).first),
                ((Month(start) + 2).first, (Month(start) + 3).first),
                ((Month(start) + 3).first, (Month(start) + 4).first),
            ]:
                yield MatrixQuote(
                    start_from=date_to_datetime(start_from),
                    start_until=date_to_datetime(start_until),
                    term_months=term, valid_from=self._valid_from,
                    valid_until=self._valid_until, min_volume=min_vol,
                    limit_volume=limit_vol, rate_class_alias=rca, price=price,
                    service_type=service_type, file_reference='%s %s,%s,%s' % (
                        self.file_name, 0, row, self.PRICE_COL))
