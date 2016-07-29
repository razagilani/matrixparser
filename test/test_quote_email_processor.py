import os
from cStringIO import StringIO
from email.message import Message
from unittest import TestCase

import statsd
from boto.s3.bucket import Bucket
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from mock import Mock

from brokerage import init_altitude_db, init_model, ROOT_PATH
from brokerage.exceptions import ValidationError
from brokerage.model import Company, Quote, MatrixQuote, MatrixFormat
from brokerage.model import Supplier, Session, AltitudeSession
from brokerage.quote_email_processor import QuoteEmailProcessor, EmailError, \
    UnknownSupplierError, QuoteDAO, MultipleErrors, NoFilesError, NoQuotesError, \
    UnknownFormatError
from brokerage.quote_parser import QuoteParser
from brokerage.quote_parsers import CLASSES_FOR_FORMATS
from test import init_test_config, clear_db, create_tables
from test.setup_teardown import FakeS3Manager

EMAIL_FILE_PATH = os.path.join(ROOT_PATH, 'test', 'quote_files',
                               'example_email_usge.txt')

def setUpModule():
    init_test_config()

class TestQuoteEmailProcessor(TestCase):
    """Unit tests for QuoteEmailProcessor.
    """
    def setUp(self):

        self.supplier = Supplier(id=1, name='The Supplier')
        self.format_1 = MatrixFormat(matrix_format_id=1)
        self.quote_dao = Mock(autospec=QuoteDAO)
        self.quote_dao.get_supplier_objects_for_message.return_value = (
            self.supplier, Company(company_id=2, name='The Supplier'))

        def get_matrix_format_side_effect(supplier, file_name, match_email_body):
            # matrix_attachment_name matches either an attachment name or an email
            # subject but not both, depending on match_email_body
            if match_email_body:
                raise UnknownFormatError('No formats matched file name "%s"' %
                                 file_name)
            return self.format_1
        self.quote_dao.get_matrix_format_for_file.side_effect = get_matrix_format_side_effect

        self.quotes = [Mock(autospec=Quote), Mock(autospec=Quote)]
        self.quote_parser = Mock(autospec = QuoteParser)
        # QuoteEmailProcessor expects QuoteParser.extract_quotes to return a
        # generator, not a list
        self.quote_parser.extract_quotes.return_value = (q for q in self.quotes)
        self.quote_parser.get_count.return_value = len(self.quotes)
        QuoteParserClass1 = Mock()
        QuoteParserClass1.return_value = self.quote_parser

        # a second QuoteParser for testing handing of multiple file formats
        # in the same email
        QuoteParserClass2 = Mock()
        self.quote_parser_2 = Mock(autospec=QuoteParser)
        QuoteParserClass2.return_value = self.quote_parser_2
        self.quote_parser_2.extract_quotes.return_value = (
            q for q in self.quotes)
        self.quote_parser_2.get_count.return_value = len(self.quotes)
        self.format_2 = MatrixFormat(matrix_format_id=2)
        self.supplier.matrix_formats = [self.format_1, self.format_2]

        # might as well use real objects for StatsD metrics; they don't need
        # to connect to a server
        self.email_counter = statsd.Counter('email')
        self.quote_counter = statsd.Counter('quote')

        self.s3_connection = Mock(autospec=S3Connection)
        self.s3_bucket = Mock(autospec=Bucket)
        self.s3_connection.get_bucket.return_value = self.s3_bucket
        self.s3_key = Mock(autospec=Key)
        self.s3_bucket.new_key.return_value = self.s3_key
        self.s3_bucket_name = 'test-bucket'

        self.qep = QuoteEmailProcessor(
            {1: QuoteParserClass1, 2: QuoteParserClass2}, self.quote_dao,
            self.s3_connection, self.s3_bucket_name)

        self.message = Message()
        self.sender, self.recipient, self.subject = (
            'Sender', 'Recipient', 'Subject')
        self.message['From'] = self.sender
        self.message['To'] = 'Original Recipient'
        self.message['Delivered-To'] = self.recipient
        self.message['Subject'] = self.subject


    def test_process_email_malformed(self):
        with self.assertRaises(EmailError):
            self.qep.process_email(StringIO('wtf'))

        self.assertEqual(
            0, self.quote_dao.get_supplier_objects_for_message.call_count)
        self.assertEqual(0, self.quote_dao.begin.call_count)
        self.assertEqual(0, self.quote_dao.insert_quotes.call_count)
        self.assertEqual(0, self.quote_parser.load_file.call_count)
        self.assertEqual(0, self.quote_parser.extract_quotes.call_count)
        self.assertEqual(0, self.quote_dao.rollback.call_count)
        self.assertEqual(0, self.quote_dao.commit.call_count)

    def test_process_email_no_supplier(self):
        self.quote_dao.get_supplier_objects_for_message.side_effect = \
            UnknownSupplierError

        with self.assertRaises(UnknownSupplierError):
            self.qep.process_email(StringIO(self.message.as_string()))

        self.quote_dao.get_supplier_objects_for_message.assert_called_once_with(
            self.recipient)
        self.assertEqual(0, self.quote_dao.begin.call_count)
        self.assertEqual(0, self.quote_dao.insert_quotes.call_count)
        self.assertEqual(0, self.quote_dao.rollback.call_count)
        self.assertEqual(0, self.quote_dao.commit.call_count)

        # nothing happens in S3
        self.assertEqual(0, self.s3_connection.get_bucket.call_count)
        self.assertEqual(0, self.s3_bucket.new_key.call_count)
        self.assertEqual(0, self.s3_key.set_contents_from_string.call_count)

    def test_process_email_no_attachment(self):
        # email has no attachment in it
        with self.assertRaises(NoFilesError):
            self.qep.process_email(StringIO(self.message.as_string()))

        # supplier objects are looked up and found, but there is nothing else
        # to do
        self.assertEqual(
            1, self.quote_dao.get_supplier_objects_for_message.call_count)
        self.assertEqual(0, self.quote_dao.begin.call_count)
        self.assertEqual(0, self.quote_dao.insert_quotes.call_count)
        self.assertEqual(0, self.quote_parser.load_file.call_count)
        self.assertEqual(0, self.quote_parser.extract_quotes.call_count)
        self.assertEqual(0, self.quote_dao.rollback.call_count)
        self.assertEqual(0, self.quote_dao.commit.call_count)

        # nothing happens in S3
        self.assertEqual(0, self.s3_connection.get_bucket.call_count)
        self.assertEqual(0, self.s3_bucket.new_key.call_count)
        self.assertEqual(0, self.s3_key.set_contents_from_string.call_count)

    def test_process_email_non_matching_attachment(self):
        self.message.add_header('Content-Disposition', 'attachment',
                                filename='filename.xls')
        self.quote_dao.get_matrix_format_for_file.side_effect = \
            UnknownFormatError
        email_file = StringIO(self.message.as_string())
        with self.assertRaises(NoFilesError):
            self.qep.process_email(email_file)

        # supplier objects are looked up and found, but nothing else happens
        # because the file is ignored. the transaction is committed because
        # there could be other files that are not ignored.
        self.assertEqual(
            1, self.quote_dao.get_supplier_objects_for_message.call_count)
        self.assertEqual(1, self.quote_dao.begin.call_count)
        self.assertEqual(0, self.quote_parser.load_file.call_count)
        self.assertEqual(0, self.quote_parser.extract_quotes.call_count)
        self.assertEqual(1, self.quote_dao.rollback.call_count)
        self.assertEqual(0, self.quote_dao.commit.call_count)

        # nothing happens in S3
        self.assertEqual(0, self.s3_connection.get_bucket.call_count)
        self.assertEqual(0, self.s3_bucket.new_key.call_count)
        self.assertEqual(0, self.s3_key.set_contents_from_string.call_count)

    def test_process_email_invalid_attachment(self):
        self.message.add_header('Content-Disposition', 'attachment',
                                filename='filename.xls')
        email_file = StringIO(self.message.as_string())
        self.quote_parser.extract_quotes.side_effect = ValidationError

        with self.assertRaises(MultipleErrors):
            self.qep.process_email(email_file)

        # quote parser doesn't like the file format, so no quotes are extracted
        self.assertEqual(
            1, self.quote_dao.get_supplier_objects_for_message.call_count)
        self.assertEqual(1, self.quote_dao.begin.call_count)
        self.assertEqual(0, self.quote_dao.insert_quotes.call_count)
        self.assertEqual(1, self.quote_parser.load_file.call_count)
        self.quote_parser.extract_quotes.assert_called_once_with()
        self.quote_dao.rollback.assert_called_once_with()
        self.assertEqual(0, self.quote_dao.commit.call_count)

        # the file DOES get stored in S3
        self.assertEqual(1, self.s3_connection.get_bucket.call_count)
        self.assertEqual(1, self.s3_bucket.new_key.call_count)
        self.assertEqual(1, self.s3_key.set_contents_from_string.call_count)

    def test_process_email_base64encoded_attachment_name(self):
        '''
        This test checks if a base64 encoded attachment name of the format
        =?utf-8?B?RGFpbHkgTWF0cml4IFByaWNlLnhscw==?= can be decoded
        '''
        self.format_1.matrix_attachment_name = 'Daily Matrix Price.xls'
        name ='Daily Matrix Price.xls'
        self.message.add_header('Content-Disposition', 'attachment',
                                filename='=?utf-8?B?RGFpbHkgTWF0cml4IFByaWNlLnhscw==?=')
        email_file = StringIO(self.message.as_string())

        self.qep.process_email(email_file)

        # normal situation: quotes are extracted from the file and committed
        # in a nested transaction
        self.assertEqual(
            1, self.quote_dao.get_supplier_objects_for_message.call_count)
        self.assertEqual(1, self.quote_dao.begin.call_count)
        self.assertEqual(len(self.quotes),
                         self.quote_dao.insert_quotes.call_count)
        self.assertEqual(1, self.quote_parser.load_file.call_count)
        self.quote_parser.extract_quotes.assert_called_once_with()
        self.assertEqual(0, self.quote_dao.rollback.call_count)
        self.assertEqual(1, self.quote_dao.commit.call_count)

        # file should have been uploaded to S3
        # (not checking actual file contents)
        self.s3_connection.get_bucket.assert_called_once_with(
            self.s3_bucket_name)
        self.s3_bucket.new_key.assert_called_once_with(name)
        self.assertEqual(1, self.s3_key.set_contents_from_string.call_count)

    def test_process_email_bad_and_good_attachments(self):
        """Two files, one with a ValidationError and the other valid. The bad
        file should not stop the good one from being processed.
        """
        # 1st call to extract_quotes fails, 2nd succeeds
        self.quote_parser.extract_quotes.side_effect = [ValidationError, (q for q in self.quotes)]

        # can't figure out how to create a well-formed email with 2 attachments
        # using the Python "email" module, so here's one from a file
        with open('test/quote_files/quote_email.txt') as f:
            with self.assertRaises(MultipleErrors) as e:
                self.qep.process_email(f)

            # out of 3 files, 2 failed with a ValidationError
            self.assertEqual(3, e.exception.file_count)
            self.assertEqual(1, len(e.exception.messages))
            self.assertIn('ValidationError', e.exception.messages[0])

        # 1st file fails so its transaction gets rolled back; 2nd file
        # succeeds so it gets committed.
        self.assertEqual(
            1, self.quote_dao.get_supplier_objects_for_message.call_count)
        self.assertEqual(
            3, self.quote_dao.get_matrix_format_for_file.call_count)
        self.assertEqual(3, self.quote_dao.begin.call_count)
        self.assertEqual(1 * len(self.quotes),
                         self.quote_dao.insert_quotes.call_count)
        self.assertEqual(2, self.quote_parser.load_file.call_count)
        self.assertEqual(2, self.quote_parser.extract_quotes.call_count)
        self.assertEqual(2, self.quote_dao.rollback.call_count)
        self.assertEqual(1, self.quote_dao.commit.call_count)

        # 2 files should be uploaded to s3
        # (not checking file names or contents)
        self.assertEqual(2, self.s3_connection.get_bucket.call_count)
        self.assertEqual(2, self.s3_bucket.new_key.call_count)
        self.assertEqual(2, self.s3_key.set_contents_from_string.call_count)

    def test_process_email_good_attachment(self):
        self.format_1.matrix_attachment_name = 'filename.xls'
        name ='fileNAME.XLS'
        self.message.add_header('Content-Disposition', 'attachment',
                                filename=name)
        email_file = StringIO(self.message.as_string())

        self.qep.process_email(email_file)

        # normal situation: quotes are extracted from the file and committed
        # in a nested transaction
        self.assertEqual(
            1, self.quote_dao.get_supplier_objects_for_message.call_count)
        self.assertEqual(1, self.quote_dao.begin.call_count)
        self.assertEqual(len(self.quotes),
                         self.quote_dao.insert_quotes.call_count)
        self.assertEqual(1, self.quote_parser.load_file.call_count)
        self.quote_parser.extract_quotes.assert_called_once_with()
        self.assertEqual(0, self.quote_dao.rollback.call_count)
        self.assertEqual(1, self.quote_dao.commit.call_count)

        # file should have been uploaded to S3
        # (not checking actual file contents)
        self.s3_connection.get_bucket.assert_called_once_with(
            self.s3_bucket_name)
        self.s3_bucket.new_key.assert_called_once_with(name)
        self.assertEqual(1, self.s3_key.set_contents_from_string.call_count)

    def test_process_email_body(self):
        self.quote_dao.get_matrix_format_for_file = Mock()
        self.quote_dao.get_matrix_format_for_file.return_value = self.format_1

        self.message.add_header('Content-Type', 'text/html')
        contents = 'Body of <b>message</b>'
        self.message.set_payload(contents)
        email_file = StringIO(self.message.as_string())

        self.qep.process_email(email_file)

        # normal situation: quotes are extracted from the file and committed
        # in a nested transaction
        self.assertEqual(
            1, self.quote_dao.get_supplier_objects_for_message.call_count)
        self.assertEqual(1, self.quote_dao.begin.call_count)
        self.assertEqual(len(self.quotes),
                         self.quote_dao.insert_quotes.call_count)
        self.assertEqual(1, self.quote_parser.load_file.call_count)
        self.assertEqual(self.quote_parser.load_file.call_args_list[0][0][0]
                         .getvalue(), contents)
        self.assertEqual(self.quote_parser.load_file.call_args_list[0][0][1]
                         , self.message['Subject'])
        self.assertEqual(self.quote_parser.load_file.call_args_list[0][0][2]
                         , self.format_1)
        self.quote_parser.extract_quotes.assert_called_once_with()
        self.assertEqual(0, self.quote_dao.rollback.call_count)
        self.assertEqual(1, self.quote_dao.commit.call_count)

        # file should have been uploaded to S3
        # (not checking actual file contents)
        self.s3_connection.get_bucket.assert_called_once_with(
            self.s3_bucket_name)
        self.s3_bucket.new_key.assert_called_once_with(self.message['Subject'])
        self.assertEqual(1, self.s3_key.set_contents_from_string.call_count)

    def test_process_email_no_quotes(self):
        self.message.add_header('Content-Disposition', 'attachment',
                                filename='filename.xls')
        email_file = StringIO(self.message.as_string())

        self.quote_parser.extract_quotes.return_value = []
        self.quote_parser.get_count.return_value = 0

        with self.assertRaises(NoQuotesError):
            self.qep.process_email(email_file)

        self.assertEqual(
            1, self.quote_dao.get_supplier_objects_for_message.call_count)
        self.assertEqual(1, self.quote_dao.begin.call_count)
        self.assertEqual(1, self.quote_dao.insert_quotes.call_count)
        self.assertEqual(1, self.quote_parser.load_file.call_count)
        self.quote_parser.extract_quotes.assert_called_once_with()
        self.assertEqual(0, self.quote_dao.rollback.call_count)
        self.assertEqual(1, self.quote_dao.commit.call_count)

        # the file DOES get stored in S3
        self.assertEqual(1, self.s3_connection.get_bucket.call_count)
        self.assertEqual(1, self.s3_bucket.new_key.call_count)
        self.assertEqual(1, self.s3_key.set_contents_from_string.call_count)

    def test_multiple_formats(self):
        """One email with 2 attachments, each of which should be read by a
        different QuoteParser class depending on the file name.
        """
        self.quote_dao.get_matrix_format_for_file.side_effect = [
            self.format_1, self.format_2]

        # can't figure out how to create a well-formed email with 2 attachments
        # using the Python "email" module, so here's one from a file
        with open('test/quote_files/quote_email.txt') as f:
            # this error is raised because of the text/html
            # is returned as an attachement
            with self.assertRaises(MultipleErrors):
                self.qep.process_email(f)

        # the 2 files are processed by 2 separate QuoteParsers
        self.assertEqual(
            1, self.quote_dao.get_supplier_objects_for_message.call_count)
        self.assertEqual(
            3, self.quote_dao.get_matrix_format_for_file.call_count)
        self.assertEqual(3, self.quote_dao.begin.call_count)
        self.assertEqual(2 * len(self.quotes),
                         self.quote_dao.insert_quotes.call_count)
        self.assertEqual(1, self.quote_parser.load_file.call_count)
        self.quote_parser.extract_quotes.assert_called_once_with()
        self.quote_parser_2.extract_quotes.assert_called_once_with()
        self.assertEqual(1, self.quote_parser_2.load_file.call_count)
        self.assertEqual(1, self.quote_dao.rollback.call_count)
        self.assertEqual(2, self.quote_dao.commit.call_count)

        # 2 files should be uploaded to s3
        # (not checking file names or contents)
        self.assertEqual(2, self.s3_connection.get_bucket.call_count)
        self.assertEqual(2, self.s3_bucket.new_key.call_count)
        self.assertEqual(2, self.s3_key.set_contents_from_string.call_count)


class TestQuoteDAO(TestCase):
    @classmethod
    def setUpClass(self):
        create_tables()
        init_model()
        clear_db()

    def setUp(self):
        self.dao = QuoteDAO()
        self.format1 = MatrixFormat(match_email_body=False)
        self.format2 = MatrixFormat(match_email_body=False)
        self.supplier = Supplier(name='Supplier',
                                 matrix_formats=[self.format1, self.format2])
        Session().add(self.supplier)

    def tearDown(self):
        clear_db()

    def test_get_matrix_format_for_file(self):
        # multiple matches with blank file name pattern
        with self.assertRaises(UnknownFormatError):
            self.dao.get_matrix_format_for_file(self.supplier, 'a', False)

        # multiple matches: note that both "a" and None match "a"
        self.format1.matrix_attachment_name = 'a'
        with self.assertRaises(UnknownFormatError):
            self.dao.get_matrix_format_for_file(self.supplier, 'a', False)

        # exactly one match
        self.format2.matrix_attachment_name = 'b'
        self.assertEqual(self.format1, self.dao.get_matrix_format_for_file(
            self.supplier, 'a', False))

        # no matches
        with self.assertRaises(UnknownFormatError):
            self.dao.get_matrix_format_for_file(self.supplier, 'c', False)

        # multiple matches with non-blank file name patterns
        self.format2.matrix_attachment_name = 'a'
        with self.assertRaises(UnknownFormatError):
            self.dao.get_matrix_format_for_file(self.supplier, 'a', False)


class TestQuoteEmailProcessorWithDB(TestCase):
    """Integration test using a real email with QuoteEmailProcessor,
    QuoteDAO, and QuoteParser, including the database.
    """
    @classmethod
    def setUpClass(self):
        FakeS3Manager.start()

        create_tables()
        init_model()
        init_altitude_db()

    @classmethod
    def tearDownClass(cls):
        FakeS3Manager.stop()

    def setUp(self):
        # example email containing a USGE matrix spreadsheet, matches the
        # Supplier object below. this has 2 quote file attachments but only 1
        #  has a corresponding QuoteParser class.
        self.email_file = open(EMAIL_FILE_PATH)
        self.quote_dao = QuoteDAO()

        from brokerage import config
        self.s3_connection = S3Connection(
            config.get('aws_s3', 'aws_access_key_id'),
            config.get('aws_s3', 'aws_secret_access_key'),
            is_secure=config.get('aws_s3', 'is_secure'),
            port=config.get('aws_s3', 'port'),
            host=config.get('aws_s3', 'host'),
            calling_format=config.get('aws_s3', 'calling_format'))
        s3_bucket_name = 'test-bucket'
        self.s3_bucket = self.s3_connection.create_bucket(s3_bucket_name)
        self.qep = QuoteEmailProcessor(
            CLASSES_FOR_FORMATS, self.quote_dao,
            # could use a real S3 connection with FakeS3, but that's not
            # really the point of this test
            self.s3_connection, s3_bucket_name)

        # add a supplier to match the example email
        clear_db()
        self.supplier = Supplier(
            id=199, name='USGE',
            matrix_email_recipient='recipient1@nextility.example.com',
            matrix_formats=[
                # these IDs must correspond to the 2 USGE parser classes in
                # 'quote_parsers.CLASSES_FOR_FORMATS'
                MatrixFormat(matrix_format_id=4,
                             matrix_attachment_name='.*GAS.*\.xlsx'),
                MatrixFormat(matrix_format_id=14,
                             matrix_attachment_name='.*ELEC.*\.xlsx'),
            ])
        self.altitude_supplier = Company(company_id=1, name=self.supplier.name)

        # extra supplier that will never match any email, to make sure the
        # right one is chosen
        Session().add(Supplier(name='Wrong Supplier',
                               matrix_email_recipient='wrong@example.com'))

    def tearDown(self):
        self.email_file.close()
        clear_db()

    def test_process_email(self):
        s = Session()
        s.add(self.supplier)
        a = AltitudeSession()
        a.add(self.altitude_supplier)
        self.assertEqual(0, a.query(Quote).count())

        # s3 bucket should start out empty
        self.assertEqual(0, len(self.s3_bucket.get_all_keys()))

        self.qep.process_email(self.email_file)
        self.assertGreater(a.query(Quote).count(), 0)

        # example email has 2 attachments in it, so 2 files are uploaded
        self.assertEqual(2, len(self.s3_bucket.get_all_keys()))

        # TODO: tests block forever without this here. it doesn't even work
        # when this is moved to tearDown because AltitudeSession (unlike
        # Session) returns a different object each time it is called. i
        # haven't figured out why that is yet.
        a.rollback()

    def test_process_email_no_supplier_match(self):
        # supplier is missing but altitude_supplier is present
        AltitudeSession().add(self.altitude_supplier)
        with self.assertRaises(UnknownSupplierError):
            self.qep.process_email(self.email_file)

        # both are present but supplier doesn't match the email's recipient
        # address
        self.email_file.seek(0)
        Session().add(self.supplier)
        self.supplier.matrix_email_recipient = 'nobody@example.com'
        with self.assertRaises(UnknownSupplierError):
            self.qep.process_email(self.email_file)

    def test_process_email_no_altitude_supplier(self):
        # TODO: this should not be necessary here--clear_db() should take
        # care of it. but without these lines, the test fails except when run
        #  by itself (presumably because of data left over from previous tests)
        a = AltitudeSession()
        a.query(MatrixQuote).delete()
        a.query(Company).delete()

        Session().add(self.supplier)
        self.qep.process_email(self.email_file)
        self.assertGreater(a.query(Quote).count(), 0)
