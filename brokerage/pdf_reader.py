"""Code related to getting quotes out of PDF files.
"""
import re

from pdfminer.layout import LTTextBox

from brokerage.exceptions import ValidationError
from brokerage.reader import Reader
from util.pdf import PDFUtil


class PDFReader(Reader):
    """Implementation of Reader for extracting tabular data from PDFs.
    """
    @staticmethod
    def distance(element, x, y):
        """Return distance of the lower left corner of a PDF element from the
        given coordinates.
        :param element: any PDF element
        :return: float
        """
        return ((element.x0 - x) ** 2 + (element.y0 - y) ** 2)**.5

    def __init__(self, tolerance=30):
        """
        :param tolerance: max allowable distance between expected and actual
        coordinates of elements in the PDF.
        """
        super(PDFReader, self).__init__()
        self._tolerance = tolerance
        self._pages = None
        self._offset_x = 0
        self._offset_y = 0

    def load_file(self, quote_file, file_name=None):
        """Read from 'quote_file'.
        :param quote_file: file to read from.
        """
        self._file_name = file_name
        self._pages = PDFUtil().get_pdfminer_layout(quote_file)

    def is_loaded(self):
        return self._pages != None

    def _get_page(self, page_number):
        try:
            return self._pages[page_number - 1]
        except IndexError:
            raise ValidationError('No page %s: last page number is %s' % (
                page_number, len(self._pages)))

    def set_offset_by_element_regex(self, regex, element_y, element_x):
        """
        :param offset_by_element_regex: regular expression string.
        if given, look for a text element whose text matches the regular
        expression, then add the difference between that element's position
        and (element_x, offset_element_y) to all coordinates when
        getting data from the PDF file in get...() methods. use this to adapt
        a QuoteParser that works for one PDF file to other files with a
        similar but not identical layout.

        :param element_y: vertical coordinate of the expected position of the
        matching element (float).

        :param element_x: horizontal coordinate of the expected position of the
        matching element (float).
        """
        y0, x0 = self.find_element_coordinates(1, 0, 0, regex)
        self._offset_x = x0 - element_x
        self._offset_y = y0 - element_y

    def get_with_coordinates(self, page_number, y, x, the_type):
        """
        Extract a value from the text box in the PDF file whose upper left
        corner is closest to the given coordinates, within some tolerance.
        Return both the text and the coordinates of the box.

        :param page_number: PDF page number starting with 1.
        :param y: vertical coordinate (starting from bottom)
        :param x: horizontal coordinate (starting from left)
        :param the_type: ignored. all values are strings.

        :return: text box content (string with whitespace stripped), x0, y0,
        x1, y1
        """
        y += self._offset_y
        x += self._offset_x

        # get all text boxes on the page (there must be at least one)
        page = self._get_page(page_number)
        text_boxes = list(
            element for element in page if isinstance(element, LTTextBox))
        if text_boxes == []:
            raise ValidationError('No text elements on page %s' % page_number)

        # find closest box to the given coordinates, within tolerance
        closest_box = min(text_boxes, key=lambda box: self.distance(box, x, y))
        text = closest_box.get_text().strip()
        if self.distance(closest_box, x, y) > self._tolerance:
            raise ValidationError(
                'No text elements within %s of (%s,%s) in %s page %s: '
                'closest is "%s" at (%s,%s)' % (
                    self._tolerance, x, y, self._file_name, page_number, text,
                    closest_box.x0, closest_box.y0))
        return text, closest_box.x0, closest_box.y0, closest_box.x1, \
               closest_box.y1

    def get(self, page_number, y, x, the_type):
        """
        Extract a value from the text box in the PDF file whose upper left
        corner is closest to the given coordinates, within some tolerance.

        :param page_number: PDF page number starting with 1.
        :param y: vertical coordinate (starting from bottom)
        :param x: horizontal coordinate (starting from left)
        :param the_type: ignored. all values are strings.

        :return: text box content (string with whitespace stripped)
        """
        text, _, _, _, _ = self.get_with_coordinates(page_number, y, x,
                                                     the_type)
        return text

    def get_matches(self, page_number, y, x, regex, types, tolerance=None):
        """Get list of values extracted from the PDF element whose corner is
        closest to the given coordinates, optionally within 'tolerance',
        using groups (parentheses) in a regular expression. Values
        are converted from strings to the given types. Raise ValidationError
        if there are 0 matches or the wrong number of matches or any value
        could not be converted to the expected type.

        Commas are removed from strings before converting to 'int' or 'float'.

        Position is allowed to be fuzzy because the regular expression can
        ensure the right cell is picked if it's specific enough. So don't use
        this with a really vague regular expression unless tolerance is low.

        :param page_number: int
        :param y: vertical coordinate
        :param x: horizontal coordinate
        :param regex: regular expression string
        :param types: expected type of each match represented as a callable
        that converts a string to that type, or a list/tuple of them whose
        length corresponds to the number of matches.
        :param tolerance: allowable distance (float) between given coordinates
        and actual coordinates of the matching element.
        :return: resulting value or list of values
        """
        # to tolerate variations in the position of the element, find the
        # closest element within tolerance that matches the regex
        elements = self._find_matching_elements(page_number, y, x, regex)
        closest_element = elements[0]
        if tolerance is not None and self.distance(
                closest_element, x, y) > tolerance:
            raise ValidationError(
                'No text elements within %s of (%s,%s) on page %s: '
                'closest is "%s" at (%s,%s)' % (
                    tolerance, x, y, page_number, closest_element.get_text(),
                    closest_element.x0, closest_element.y0))

        text = closest_element.get_text().strip()
        return self._validate_and_convert_text(regex, text, types)

    def _find_matching_elements(self, page_number, y, x, regex):
        """Return list of text elements matching the given regular expression
        (ignoring surrounding whitespace) in increasing order of distance
        from the given coordinates.

        :param page_number: PDF page number starting with 1.
        :param y: y coordinate (float)
        :param x: x coordinate (float)
        :param regex: regular expression string
        """
        page = self._get_page(page_number)
        matching_elements = [
            e for e in page if isinstance(e, LTTextBox) and
            re.match(regex, e.get_text().strip())]
        if matching_elements == []:
            raise ValidationError(
                'No text elements on page %s match "%s"' % (page_number, regex))
        matching_elements.sort(key=lambda e: self.distance(e, x, y))
        return matching_elements

    def find_element_coordinates(self, page_number, y, x, regex):
        """Return coordinates of the text element closest to the given
        coordinates matching the given regular expression (ignoring
        surrounding whitespace).

        :param page_number: PDF page number starting with 1.
        :param y: y coordinate (float)
        :param x: x coordinate (float)
        :param regex: regular expression string
        """
        matching_elements = self._find_matching_elements(page_number, y, x,
                                                         regex)
        closest_element = matching_elements[0]
        return (closest_element.y0 - self._offset_y,
                closest_element.x0 - self._offset_x)
