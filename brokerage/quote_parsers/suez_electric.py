from datetime import datetime, timedelta

from tablib import formats

from brokerage.model import MatrixQuote
from brokerage.quote_parser import QuoteParser, SpreadsheetReader, \
    SimpleCellDateGetter
from util.dateutils import date_to_datetime
from util.monthmath import Month
from util.units import unit_registry


class SuezElectricParser(QuoteParser):
    NAME = 'suez'
    reader = SpreadsheetReader(formats.xlsx)

    ROUNDING_DIGITS = 5
    SHEET_DEFAULT = 'Price Matrix'
    ROW_LABEL = 3
    COL_START_MONTH = 2 - 1
    COL_STATE = 3 - 1
    COL_UTILITY = 4 - 1
    COL_ZONE = 5 - 1 # If it exists...
    COL_DESC = 5 - 1
    COL_TERM = 6 - 1
    COL_NOTES = 7 - 1
    COL_QUOTE_START = 8 - 1

    def _from_price_cell(self, row, col, has_notes):
        """Produce a quote from the given coordinates"""

        price = self.reader.get(self.SHEET_DEFAULT, row, col, (float, int))
        start_date_str = self.reader.get(self.SHEET_DEFAULT, row,
            self.COL_START_MONTH, basestring)
        term_months = self.reader.get(self.SHEET_DEFAULT, row,
            self.COL_TERM, int)
        volume_range_str = self.reader.get(self.SHEET_DEFAULT,
            self.ROW_LABEL, col, basestring)
        valid_from_str = self.file_name.split('_')[-1].replace('.xlsx', '')
        state_str = self.reader.get(self.SHEET_DEFAULT, row,
            self.COL_STATE, basestring)
        desc_str = str(self.reader.get(self.SHEET_DEFAULT, row, self.COL_DESC,
            (int, basestring)))
        utility_str = self.reader.get(self.SHEET_DEFAULT, row,
            self.COL_UTILITY, basestring)
        zone_str = self.reader.get(self.SHEET_DEFAULT, row,
            self.COL_ZONE, basestring) if self.has_zone else ''
        notes_str = self.reader.get(self.SHEET_DEFAULT, row, self.COL_NOTES,
                basestring) if has_notes else ''

        alias_elts = '-'.join([x.strip() for x in
            [state_str, utility_str, desc_str, zone_str, notes_str]
            if x.strip() != ''])

        rate_class_alias = 'Suez-electric-%s' % alias_elts

        start_from = datetime.strptime(start_date_str, '%B %Y Start')
        start_until = date_to_datetime((Month(start_from) + 1).first)
        min_volume, limit_volume = [int(v.strip().replace(',', ''))
                                    for v in volume_range_str.split('-')]
        valid_from = datetime.strptime(valid_from_str, '%Y.%m.%d')
        valid_until = valid_from + timedelta(days=1)
        has_por = True if 'por' in notes_str.lower() else False

        quote = MatrixQuote(
            start_from=start_from, start_until=start_until,
            term_months=term_months, valid_from=valid_from,
            valid_until=valid_until,
            min_volume=min_volume, limit_volume=limit_volume,
            rate_class_alias=rate_class_alias,
            price=price/100.0, service_type='electric',
            purchase_of_receivables=has_por,
            file_reference='%s %s,%s,%s' % (
                self.file_name, self.SHEET_DEFAULT, row, col))

        return quote

    def _extract_quotes(self):
        if self.reader.get(self.SHEET_DEFAULT, self.ROW_LABEL, self.COL_ZONE,
            basestring).strip() == 'Zone':
            self.COL_DESC += 1
            self.COL_TERM += 1
            self.COL_NOTES += 1
            self.COL_QUOTE_START += 1
            self.has_zone = True
        else:
            self.has_zone = False
       
        # This took me a little while to get right, hence the assertions
        expected_note = self.reader.get(self.SHEET_DEFAULT, self.ROW_LABEL, 
            self.COL_NOTES, basestring)
        has_notes = True
        if 'notes' not in expected_note.strip().lower():
            self.COL_QUOTE_START -= 1
            assert self.COL_QUOTE_START == self.COL_NOTES
            has_notes = False
        else:
            assert self.COL_QUOTE_START - 1 == self.COL_NOTES


        for current_row in xrange(self.ROW_LABEL + 1,
            self.reader.get_height(self.SHEET_DEFAULT)):
            for current_col in xrange(self.COL_QUOTE_START,
                self.reader.get_width(self.SHEET_DEFAULT)):
                
                col_hdr = self.reader.get(self.SHEET_DEFAULT, self.ROW_LABEL,
                    current_col, object)

                # This cell will be in the format 000000 - 000000
                if isinstance(col_hdr, basestring):
                    if col_hdr.replace(' ', '').replace('-', '') \
                        .replace(',', '').strip().isdigit():

                        # Some cells are empty, some are parsed as ints
                        # e.g., if the price is 5.00000
                        price = self.reader.get(self.SHEET_DEFAULT,
                                current_row, current_col,
                                (float, int, type(None)))

                        if price:
                            yield self._from_price_cell(current_row,
                                current_col, has_notes)



