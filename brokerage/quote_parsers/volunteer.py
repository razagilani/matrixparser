import calendar
import re
from datetime import datetime

from brokerage.exceptions import ValidationError
from brokerage.model import MatrixQuote
from brokerage.pdf_reader import PDFReader
from brokerage.quote_parser import QuoteParser, StartEndCellDateGetter
from brokerage.validation import _assert_equal, GAS
from util.dateutils import date_to_datetime
from util.monthmath import Month
from util.units import unit_registry


class VolunteerMatrixParser(QuoteParser):
    NAME = 'volunteer'

    reader = PDFReader(tolerance=40)

    # used for validation and setting PDFReader offset to account for varying
    # positions of elements in each file, as well as extracting the volume
    # ranges
    PRICING_LEVEL_PATTERN = \
        'PRICING LEVEL\n(?P<low>\d+)-(?P<high>[\d,r]+) Mcf.*'

    # very tricky: this is usually all caps, except
    # "COLUMBIA GAS of OHIO (COH)" which has a lowercase "of". also, sometimes
    # "\nIndicative Price Offers" is appended to the end, while other times
    # that is a completely separate element that we must avoid matching instead
    # of the utility name. in some cases only the length distinguishes it.
    UTILITY_NAME_PATTERN = re.compile('^([A-Z\(\) of]{10,50}).*',
                                      flags=re.DOTALL)

    PRICE_PATTERN = '(\d*\.\d+)'

    # only these two have positions consistent enough to use the same
    # coordinates for every file
    EXPECTED_CELLS = [
        (1, 509, 70,  PRICING_LEVEL_PATTERN),
        (1, 422, 70, 'MARKET ULTRA'),
    ]

    START_ROW, START_COL = (539, 521)
    PRICE_ROWS = [487, 455, 422]
    TERM_ROW = 520
    TERM_COLS = [189, 324, 465]

    # prices (in the "Fixed" column) are a little bit right of the term even
    # though they look left, because "$" is a different text element
    # there are 3 columns of prices, but the middle and right columns have
    # invisible text that we're ignoring, so we only get 3 prices per file.
    PRICE_COLS = [
        189,
        #386,
        #456,
    ]

    # compromise values that work for all files except CON
    ADDER_COL = 291
    ADDER_ROWS = [225, 205, 190]

    date_getter = StartEndCellDateGetter(1, 538, 310, 538, 380, '(\d+/\d+/\d+)')
    EXPECTED_ENERGY_UNIT = unit_registry.Mcf

    def _after_load(self):
        # set global vertical and horizontal offset for each file based on the
        # position of the "PRICING LEVEL" box in that file relative to where
        # it was in the "Exchange_COH_2015\ 12-7-15.pdf" file. this may be
        # ugly but it allows enough tolerance of varying positions that the
        # same code can be used to parse all of Volunteer's PDF files.
        self._reader.set_offset_by_element_regex(
            self.PRICING_LEVEL_PATTERN, element_x=70, element_y=509)

    def _validate(self):
        # these can't go in EXPECTED_CELLS because their position varies too
        # much to use fixed coordinates for every file. instead, use the
        # fuzzy position behavior in PDFReader.get_matches.
        for page_number, y, x, regex in [
            (1, 569, 265, re.compile('.*Indicative Price Offers', re.DOTALL)),
            (1, 549, 391, 'To:'),
            (1, 549, 329, 'From:'),
            (1, 539, 470, 'Start\nMonth'),
            (1, 538, 189, 'Prices Effective for Week of:'),
            (1, 538, 189, 'Prices Effective for Week of:'),
            # column headers may say "Fixed", "Variable", or nothing
            (1, 509, 455, '(?:Fixed)?(?:\s+Variable\*\*)?'),
            (1, 509, 314, '(?:Fixed)?(?:\s+Variable\*\*)?'),
            (1, 509, 172, '(?:Fixed)?(?:\s+Variable\*\*)?'),
            (1, 477, 70, 'PREMIUM'),
            (1, 455, 70, 'MARKET MID'),

            # labels for the adder table at the bottom
            (1, 240, 237, 'Projected Fee:\s*'),
            (1, 240, self.ADDER_COL, 'Fixed'),
            (1, self.ADDER_ROWS[0], 231, 'Premium'),
            (1, self.ADDER_ROWS[1], 231, 'Market Mid'),
            (1, self.ADDER_ROWS[2], 231, 'Market Ultra'),
        ]:
            # types argument is [] because there are no groups; this is just
            # to check for matches rather than extract data
            self._reader.get_matches(page_number, y, x, regex, [], tolerance=40)

    def _extract_quotes(self):
        # utility name is the only rate class alias field.
        # getting this using the same code for every file is a lot harder than
        # it seems at first. here we pick the closest field within tolerance
        # of the given coordinates whose text matches the big ugly regex
        # defined above.
        rate_class_alias = self._reader.get_matches(
            1, 581, 241, self.UTILITY_NAME_PATTERN, str, tolerance=50)
        rate_class_alias = 'Volunteer-gas-%s' % rate_class_alias

        min_vol, limit_vol = self._extract_volume_range(
            1, 509, 70, self.PRICING_LEVEL_PATTERN,
            expected_unit=unit_registry.Mcf, target_unit=unit_registry.ccf)

        start_month_name, start_year = self._reader.get_matches(
            1, self.START_ROW, self.START_COL,
            '(?:Start\s+Month\s+)?(Jun)-(2016)\s*', (str, int))
        start_month = next(i for i, abbr in enumerate(calendar.month_abbr)
                           if abbr == start_month_name)
        start_from = datetime(start_year, start_month, 1)
        start_until = date_to_datetime((Month(start_from) + 1).first)

        # extract adders from the "Fixed" column of the small adder table at
        # the bottom. each row of prices has a corresponding adder which
        # should be subtracted from the price shown to get the real price.
        # make sure the 3 boxes are distinct because layout variations can make
        # box 1 and box 2 both the closest to expected coordinate 1, etc.
        # if this technique needs to be used anywhere else, turn it into a
        # method of PDFReader.
        adder_elements = []
        for row in self.ADDER_ROWS:
            all_elements = self.reader._find_matching_elements(
                1, row, self.ADDER_COL, self.PRICE_PATTERN)
            closest_element_not_already_picked = next(
                e for e in all_elements if e not in adder_elements)
            adder_elements.append(closest_element_not_already_picked)
        adders = [float(e.get_text().strip()) for e in adder_elements]
        if any(a == b for a, b in zip(adders, adders[1:])):
            raise ValidationError('Expected 3 different adders but some were '
                                  'the same: %s' % adders)

        for adder, row in zip(adders, self.PRICE_ROWS):
            for price_col, term_col in zip(self.PRICE_COLS, self.TERM_COLS):
                # term text may have other stuff prepended to it
                term_regex = re.compile(r'(?:.*\s+)?Term-(\d+) Month',
                                        flags=re.DOTALL)
                term = self._reader.get_matches(
                    1, self.TERM_ROW, term_col, term_regex, int)
                price = self._reader.get_matches(
                    1, row, price_col, self.PRICE_PATTERN, float, tolerance=20)
                yield MatrixQuote(
                    start_from=start_from, start_until=start_until,
                    term_months=term, valid_from=self._valid_from,
                    valid_until=self._valid_until, min_volume=min_vol,
                    limit_volume=limit_vol,
                    rate_class_alias=rate_class_alias,
                    purchase_of_receivables=False, price=price - adder,
                    service_type=GAS, file_reference='%s %s,%s,%s' % (
                        self.file_name, 1, row, price_col))
