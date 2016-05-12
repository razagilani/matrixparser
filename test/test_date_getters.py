from datetime import datetime

import pytest
from mock import Mock

from brokerage.exceptions import ValidationError
from brokerage.quote_parser import FileNameDateGetter

@pytest.fixture
def file_name_date_getter():
    return FileNameDateGetter()

def test_file_name_date_getter_success(file_name_date_getter):
    parser = Mock(file_name='Whatever 01-01-2000   .pdf')
    parser.matrix_format = Mock(
        matrix_attachment_name=r'Whatever (?P<date>\d+-\d+-\d\d\d\d)\s*\..+')
    start, end = file_name_date_getter.get_dates(parser)
    assert start == datetime(2000, 1, 1)
    assert end == datetime(2000, 1, 2)

def test_file_name_date_getter_no_match(file_name_date_getter):
    parser = Mock(file_name='Something else.pdf')
    parser.matrix_format = Mock(
        matrix_attachment_name=r'Whatever (?P<date>\d+-\d+-\d\d\d\d)\s*\..+')
    with pytest.raises(ValidationError):
        file_name_date_getter.get_dates(parser)

def test_file_name_date_getter_invalid_regex(file_name_date_getter):
    parser = Mock(file_name="Doesn't matter")
    # file name regex has a group, but not a named one
    parser.matrix_format = Mock(
        matrix_attachment_name=r'Whatever (\d+-\d+-\d\d\d\d)\s*\..+')
    with pytest.raises(ValueError):
        file_name_date_getter.get_dates(parser)

