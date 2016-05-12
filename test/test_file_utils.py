from io import BytesIO
from unittest import TestCase
from zipfile import ZipFile

from brokerage.exceptions import BillingError
from brokerage.file_utils import extract_zip


class UnzipFileTest(TestCase):

    def setUp(self):
        self.fp = BytesIO()
        self.zip_file = ZipFile(self.fp, 'w')

    def test_extract_zip_empty(self):
        self.zip_file.close()
        self.fp.seek(0)

        with self.assertRaises(BillingError):
            extract_zip(self.fp)

    def test_extract_zip_1_file(self):
        self.zip_file.writestr('example_file.txt', 'hello')
        self.zip_file.close()
        self.fp.seek(0)

        unzipped_file = extract_zip(self.fp)
        self.assertEqual('hello', unzipped_file.read())

    def test_extract_zip_2_files(self):
        self.zip_file.writestr('example_file.txt', 'hello')
        self.zip_file.writestr('another_file.txt', 'text')
        self.zip_file.close()
        self.fp.seek(0)

        with self.assertRaises(BillingError):
            extract_zip(self.fp)
