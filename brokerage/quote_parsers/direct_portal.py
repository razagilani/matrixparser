from datetime import datetime

from brokerage.exceptions import ValidationError
from tablib import formats

from brokerage.quote_parser import QuoteParser, excel_number_to_datetime, \
    SimpleCellDateGetter, FileNameDateGetter
from brokerage.spreadsheet_reader import SpreadsheetReader
from brokerage.validation import _assert_true, ELECTRIC, GAS, _assert_equal
from util.dateutils import date_to_datetime
from util.monthmath import Month
from brokerage.model import MatrixQuote
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
    OFFER_TYPE_COL = 'F'
    PRICE_COL = 'G'
    UNIT_COL = 'H'

    EXPECTED_SHEET_TITLES = ['Prices', 'Utility Abbreviations']
    EXPECTED_CELLS = [
        (0, HEADER_ROW, 'A', 'Commodity'),
        (0, HEADER_ROW, 'B', 'State'),
        (0, HEADER_ROW, 'C', 'LDC'),
        (0, HEADER_ROW, 'D', 'Zone'),
        (0, HEADER_ROW, 'E', 'Term'),
        (0, HEADER_ROW, 'F', 'Offer Type'),
        (0, HEADER_ROW, 'G', 'Rate Amt'),
        (0, HEADER_ROW, 'H', 'Unit'),
        (0, HEADER_ROW, 'I', 'Cancel Fee'),
    ]

    date_getter = FileNameDateGetter()

    def _extract_quotes(self):
        for row in xrange(self.QUOTE_START_ROW, self.reader.get_height(0) + 1):
            # skip "NEST" rows, related to Nest thermostat
            if self.reader.get(0, row, self.OFFER_TYPE_COL,
                               basestring) == 'NEST':
                continue

            # different volume limits and interpretation of price unit for
            # electric and gas quotes. also different gas quotes have
            # different units.
            commodity = self.reader.get(0, row, 'A', basestring).lower()
            unit_name = self.reader.get(0, row, self.UNIT_COL,
                                        basestring).lower()
            if commodity == 'power':
                service_type = ELECTRIC
                _assert_equal(unit_name, 'kwh')
                expected_unit = target_unit = unit_registry.kWh
                min_vol, limit_vol = 0, 750000
            elif commodity == 'gas':
                service_type = GAS
                if unit_name in ('thm', 'ccf'):
                    expected_unit = unit_registry.therm
                elif unit_name == 'mcf':
                    expected_unit = unit_registry.therm * 10
                else:
                    raise ValidationError('Unknown gas unit: "%s"' % unit_name)
                target_unit = unit_registry.therm
                min_vol, limit_vol = 0, 150000
            else:
                raise ValidationError(
                    'Expected service type "power" or "gas", found "%s"' %
                    commodity)

            rca_prefix = 'Direct Energy Small Business-' + service_type.lower()
            rca = '-'.join([rca_prefix] + [
                str(self.reader.get(0, row, col, object)) for col in
                self.RCA_COLS])
            term = self.reader.get(0, row, self.TERM_COL, int)
            price = self.reader.get(0, row, self.PRICE_COL, float) * \
                    target_unit / expected_unit

            # all TODO
            start_from = datetime(2000, 1, 1)
            start_until = datetime(2000, 1, 2)

            yield MatrixQuote(
                start_from=start_from, start_until=start_until,
                term_months=term, valid_from=self._valid_from,
                valid_until=self._valid_until, min_volume=min_vol,
                limit_volume=limit_vol, rate_class_alias=rca, price=price,
                service_type=service_type, file_reference='%s %s,%s,%s' % (
                    self.file_name, 0, row, self.PRICE_COL))
