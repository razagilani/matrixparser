from datetime import timedelta

from tablib import formats

from brokerage.model import MatrixQuote
from brokerage.quote_parser import QuoteParser, FileNameDateGetter
from brokerage.quote_parser import excel_number_to_datetime
from brokerage.spreadsheet_reader import SpreadsheetReader
from brokerage.file_utils import LibreOfficeFileConverter
from brokerage.validation import _assert_true


class AmerigreenMatrixParser(QuoteParser):
    """Parser for Amerigreen spreadsheet.
    """
    NAME = 'amerigreen'
    # original spreadsheet is in "xlsx" format. but reading it using
    # tablib.formats.xls gives this error from openpyxl:
    # "ValueError: Negative dates (-0.007) are not supported"
    # solution: open in Excel and re-save in "xls" format.
    reader = SpreadsheetReader(formats.xls)

    HEADER_ROW = 25
    QUOTE_START_ROW = 26
    UTILITY_COL = 'C'
    STATE_COL = 'D'
    TERM_COL = 'E'
    START_MONTH_COL = 'F'
    START_DAY_COL = 'G'
    PRICE_COL = 'N'
    ROUNDING_DIGITS = 4

    # Amerigreen builds in the broker fee to the prices, so it must be
    # subtracted from the prices shown
    BROKER_FEE_CELL = (22, 'F')

    EXPECTED_SHEET_TITLES = None
    EXPECTED_CELLS = [
        (0, 11, 'C', 'AMERIgreen Energy Daily Matrix Pricing'),
        (0, 13, 'C', "Today's Date:"),
        (0, 15, 'C', 'The Matrix Rates include a \$0.0200/therm Broker Fee'),
        (0, 15, 'J', 'All rates are quoted at the burner tip and include LDC '
                     'Line Loss fees'),
        (0, 16, 'J', 'Quotes are valid through the end of the business day'),
        (0, 17, 'J',
         'Valid for accounts with annual volume of up to 50,000 therms'),
        (0, 19, 'J',
         "O&R and PECO rates are in Ccf's, all others are in Therms"),
        (0, HEADER_ROW, 'C', 'LDC'),
        (0, HEADER_ROW, 'D', 'State'),
        (0, HEADER_ROW, 'E', 'Term \(Months\)'),
        (0, HEADER_ROW, 'F', 'Start Month'),
        (0, HEADER_ROW, 'G', 'Start Day'),
        (0, HEADER_ROW, 'J', 'Broker Fee'),
        (0, HEADER_ROW, 'K', "Add'l Fee"),
        (0, HEADER_ROW, 'L', "Total Fee"),
        (0, HEADER_ROW, 'M', "Heat"),
        (0, HEADER_ROW, 'N', "Flat"),
    ]

    date_getter = FileNameDateGetter()

    def _preprocess_file(self, quote_file, file_name):
        return LibreOfficeFileConverter(
            'xls', 'xls:"MS Excel 97"').convert_file(quote_file, file_name)

    def _extract_quotes(self):
        broker_fee = self.reader.get(0, self.BROKER_FEE_CELL[0],
                                     self.BROKER_FEE_CELL[1], float)

        # "Valid for accounts with annual volume of up to 50,000 therms"
        min_volume, limit_volume = 0, 50000

        for row in xrange(self.QUOTE_START_ROW, self.reader.get_height(0)):
            utility = self.reader.get(0, row, self.UTILITY_COL, basestring)
            # detect end of quotes by blank cell in first column
            if utility == "":
                break

            state = self.reader.get(0, row, self.STATE_COL, basestring)
            rate_class_alias = 'Amerigreen-gas-' + state + '-' + utility

            term_months = int(self.reader.get(0, row, self.TERM_COL,
                                              (int, float)))

            start_from = excel_number_to_datetime(
                self.reader.get(0, row, self.START_MONTH_COL, float))
            start_day_str = self.reader.get(0, row, self.START_DAY_COL,
                                            basestring)
            _assert_true(start_day_str in ('1st of the Month',
                                           'On Cycle Read Date'))
            # TODO: does "1st of the month" really mean starting only on one day?
            start_until = start_from + timedelta(days=1)

            price = self.reader.get(0, row, self.PRICE_COL, float) - broker_fee

            for rate_class_id in self.get_rate_class_ids_for_alias(
                    rate_class_alias):
                quote = MatrixQuote(
                    start_from=start_from, start_until=start_until,
                    term_months=term_months, valid_from=self._valid_from,
                    valid_until=self._valid_until,
                    min_volume=min_volume, limit_volume=limit_volume,
                    rate_class_alias=rate_class_alias,
                    purchase_of_receivables=False, price=price,
                    service_type='electric',
                    file_reference='%s %s,%s,%s' % (
                        self.file_name, 0, row, self.PRICE_COL))
                # TODO: rate_class_id should be determined automatically
                # by setting rate_class
                if rate_class_id is not None:
                    quote.rate_class_id = rate_class_id
                yield quote

