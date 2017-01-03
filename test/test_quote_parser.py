import re
from collections import defaultdict
from datetime import datetime
from os.path import join, basename
from unittest import TestCase

from mock import Mock

from brokerage import ROOT_PATH, init_altitude_db, init_model
from brokerage.model import AltitudeSession
from brokerage.validation import ELECTRIC
from brokerage.quote_parser import QuoteParser, SpreadsheetReader
from brokerage.quote_parsers import (
    AEPMatrixParser, EntrustMatrixParser,
    ChampionMatrixParser, GEEGasNJParser)
from brokerage.quote_parsers.guttman_electric import GuttmanElectric
from brokerage.quote_parsers.guttman_gas import GuttmanGas
from brokerage.quote_parsers.spark import SparkMatrixParser
from test import create_tables, init_test_config, clear_db
from util.units import unit_registry


def setUpModule():
    init_test_config()


class QuoteParserTest(TestCase):
    def setUp(self):
        reader = Mock(autospec=SpreadsheetReader)

        class ExampleQuoteParser(QuoteParser):
            NAME = 'example'
            reader = Mock()
            def __init__(self):
                super(ExampleQuoteParser, self).__init__()
                self.reader = reader
            def _extract_quotes(self):
                pass

        self.qp = ExampleQuoteParser()
        self.qp.EXPECTED_ENERGY_UNIT = unit_registry.MWh
        self.qp.TARGET_ENERGY_UNIT = unit_registry.kWh
        self.reader = reader
        self.regex = re.compile(r'from (?P<low>\d+) to (?P<high>\d+)')

    def test_extract_volume_range_normal(self):
        self.reader.get_matches.return_value = 1, 2
        low, high = self.qp._extract_volume_range(0, 0, 0, self.regex)
        self.assertEqual((1000, 2000), (low, high))
        self.reader.get_matches.assert_called_once_with(0, 0, 0, self.regex,
                                                        (int, int))

    def test_extract_volume_range_fudge(self):
        self.reader.get_matches.return_value = 11, 20
        low, high = self.qp._extract_volume_range(
            0, 0, 0, self.regex, fudge_low=True, fudge_high=True)
        self.assertEqual((10000, 20000), (low, high))
        self.reader.get_matches.assert_called_once_with(0, 0, 0, self.regex,
                                                        (int, int))

        self.reader.reset_mock()
        self.reader.get_matches.return_value = 10, 19
        low, high = self.qp._extract_volume_range(
            0, 0, 0, self.regex, fudge_low=True, fudge_high=True)
        self.assertEqual((10000, 20000), (low, high))
        self.reader.get_matches.assert_called_once_with(0, 0, 0, self.regex,
                                                        (int, int))


class MatrixQuoteParsersTest(TestCase):
    """Deprecated. Don't put new tests in here; instead use the
    QuoteParserTest class, following the example in test_quote_parsers/*.py
    Instead of updating these tests, replace them with new ones that directory.
    """
    # paths to example spreadsheet files from each supplier
    DIRECTORY = join(ROOT_PATH, 'test', 'quote_files')
    AEP_FILE_PATH = join(DIRECTORY,
                         'AEP Energy Matrix 3.0 2015-11-12.xls')
    CHAMPION_FILE_PATH = join(
        DIRECTORY, 'Champion MM PJM Fixed-Index-24 Matrix 2015-10-30.xls')
    CONSTELLATION_FILE_PATH = join(
        DIRECTORY, 'Constellation - SMB Cost+ Matrix_Fully '
                   'Bundled_09_24_2015.xlsm')
    ENTRUST_FILE_PATH = join(
        DIRECTORY, 'Entrust Energy Commercial Matrix Pricing_10182016.xlsx')

    GUTTMAN_DEO_FILE_PATH = join(DIRECTORY, 'Guttman', 'DEO_Matrix_02242016.xlsx')
    GUTTMAN_OH_DUKE_FILE_PATH = join(DIRECTORY, 'Guttman', 'OH_Duke_Gas_Matrix_02242016.xlsx')
    GUTTMAN_PEOPLE_TWP_FILE_PATH = join(DIRECTORY, 'Guttman', 'PeoplesTWP_Matrix_02242016.xlsx')
    GUTTMAN_CPA_MATRIX_FILE_PATH = join(DIRECTORY, 'Guttman', 'CPA_Matrix_02242016.xlsx')
    GUTTMAN_PEOPLE_MATRIX_FILE_PATH = join(DIRECTORY, 'Guttman', 'Peoples_Matrix_02242016.xlsx')
    GUTTMAN_COH_MATRIX_FILE_PATH = join(DIRECTORY, 'Guttman', 'COH_Matrix_02242016.xlsx')
    GUTTMAN_OH_POWER_FILE_PATH = join(DIRECTORY, 'Guttman', 'Guttman Energy OH Power Matrices 2.10.16.xlsx')
    GUTTMAN_PA_POWER_FILE_PATH = join(DIRECTORY, 'Guttman', 'Guttman Energy PA Power Matrices 2.10.16.xlsx')
    GEE_GAS_PATH_NJ = join(DIRECTORY, 'NJ Rack Rates_1.7.2016.pdf')
    GEE_GAS_PATH_NY = join(DIRECTORY, 'NY Rack Rates_2.2.2016.pdf')
    SPARK_FILE_PATH = join(DIRECTORY, 'Spark Custom_LED_MATRIX.xlsx')

    @classmethod
    def setUpClass(cls):
        init_test_config()
        create_tables()
        init_model()
        init_altitude_db()

    def setUp(self):
        clear_db()
        session = AltitudeSession()
        session.flush()

    def tearDown(self):
        clear_db()

    def test_guttman_electric(self):
        parser = GuttmanElectric()
        self.assertEqual(0, parser.get_count())
        with open(self.GUTTMAN_OH_POWER_FILE_PATH, 'rb') as \
                spreadsheet:
            parser.load_file(spreadsheet, None, None)
        parser.validate()
        self.assertEqual(0, parser.get_count())

        quotes = list(parser.extract_quotes())
        self.assertEqual(1440, len(quotes))
        self.assertEqual(1440, parser.get_count())

        for quote in quotes:
            quote.validate()

        q1 = quotes[0]
        self.assertEqual(datetime(2016, 04, 01), q1.start_from)
        self.assertEqual(datetime(2016, 05, 01), q1.start_until)
        self.assertEqual(12, q1.term_months)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(datetime(2016, 02, 10, 9, 1, 18), q1.valid_from)
        self.assertEqual(datetime(2016, 02, 11, 9, 1, 18), q1.valid_until)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(250000, q1.limit_volume)
        self.assertEqual('Guttman-electric-Ohio_AEP_OH_CS_GS-1', q1.rate_class_alias)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(0.0528741971111324, q1.price)

        q2 = quotes[1439]
        self.assertEqual(datetime(2017, 03, 01), q2.start_from)
        self.assertEqual(datetime(2017, 04, 01), q2.start_until)
        self.assertEqual(36, q2.term_months)
        self.assertEqual(datetime.utcnow().date(), q2.date_received.date())
        self.assertEqual(datetime(2016, 02, 10, 9, 1, 43), q2.valid_from)
        self.assertEqual(datetime(2016, 02, 11, 9, 1, 43), q2.valid_until)
        self.assertEqual(250001, q2.min_volume)
        self.assertEqual(500000, q2.limit_volume)
        self.assertEqual('Guttman-electric-Ohio_Toledo Edison_GS', q2.rate_class_alias)
        self.assertEqual(False, q2.purchase_of_receivables)
        self.assertEqual(0.0567758364630019, q2.price)

        parser = GuttmanElectric()
        self.assertEqual(0, parser.get_count())
        with open(self.GUTTMAN_PA_POWER_FILE_PATH, 'rb') as \
                spreadsheet:
            parser.load_file(spreadsheet, None, None)
        parser.validate()
        self.assertEqual(0, parser.get_count())

        quotes = list(parser.extract_quotes())
        self.assertEqual(1920, len(quotes))
        self.assertEqual(1920, parser.get_count())

        for quote in quotes:
            quote.validate()

        q1 = quotes[0]
        self.assertEqual(datetime(2016, 04, 01), q1.start_from)
        self.assertEqual(datetime(2016, 05, 01), q1.start_until)
        self.assertEqual(12, q1.term_months)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(datetime(2016, 2, 10, 9, 3, 34), q1.valid_from)
        self.assertEqual(datetime(2016, 2, 11, 9, 3, 34), q1.valid_until)
        self.assertEqual(125000, q1.min_volume)
        self.assertEqual(250000, q1.limit_volume)
        self.assertEqual('Guttman-electric-Pennsylvania_Duquesne_DQE_GS', q1.rate_class_alias)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(0.0668236284169137, q1.price)

        q2 = quotes[1919]
        self.assertEqual(datetime(2017, 03, 01), q2.start_from)
        self.assertEqual(datetime(2017, 04, 01), q2.start_until)
        self.assertEqual(36, q2.term_months)
        self.assertEqual(datetime.utcnow().date(), q2.date_received.date())
        self.assertEqual(datetime(2016, 2, 10, 9, 3, 58), q2.valid_from)
        self.assertEqual(datetime(2016, 2, 11, 9, 3, 58), q2.valid_until)
        self.assertEqual(250001, q2.min_volume)
        self.assertEqual(500000, q2.limit_volume)
        self.assertEqual('Guttman-electric-Pennsylvania_West Penn Power_30', q2.rate_class_alias)
        self.assertEqual(False, q2.purchase_of_receivables)
        self.assertEqual(0.0628765288123746, q2.price)

    def test_guttman_gas(self):
        parser = GuttmanGas()
        self.assertEqual(0, parser.get_count())
        with open(self.GUTTMAN_DEO_FILE_PATH, 'rb') as \
                spreadsheet:
            parser.load_file(spreadsheet,
                             basename(self.GUTTMAN_DEO_FILE_PATH), None)
        parser.validate()
        self.assertEqual(0, parser.get_count())

        quotes = list(parser.extract_quotes())
        self.assertEqual(170, len(quotes))
        self.assertEqual(170, parser.get_count())

        for quote in quotes:
            quote.validate()

        q1 = quotes[0]
        self.assertEqual(datetime(2017, 03, 16), q1.start_from)
        self.assertEqual(datetime(2017, 04, 01), q1.start_until)
        self.assertEqual(6, q1.term_months)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(datetime(2016, 2, 24, 8, 45, 18), q1.valid_from)
        self.assertEqual(datetime(2016, 2, 25, 8, 45, 18), q1.valid_until)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(5 * 1000, q1.limit_volume)
        self.assertEqual('Guttman-gas-Ohio_Dominion_OH_NG', q1.rate_class_alias)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(0.271975927644554, q1.price)

        parser = GuttmanGas()
        with open(self.GUTTMAN_OH_DUKE_FILE_PATH, 'rb') as \
                spreadsheet:
            parser.load_file(spreadsheet,
                             basename(self.GUTTMAN_OH_DUKE_FILE_PATH), None)
        parser.validate()
        self.assertEqual(0, parser.get_count())
        quotes = list(parser.extract_quotes())
        self.assertEqual(170, len(quotes))
        self.assertEqual(170, parser.get_count())

        q1 = quotes[0]
        self.assertEqual(datetime(2017, 03, 16), q1.start_from)
        self.assertEqual(datetime(2017, 04, 01), q1.start_until)
        self.assertEqual(6, q1.term_months)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(datetime(2016, 2, 24, 8, 45, 18), q1.valid_from)
        self.assertEqual(datetime(2016, 2, 25, 8, 45, 18), q1.valid_until)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(5 * 1000, q1.limit_volume)
        self.assertEqual('Guttman-gas-Ohio_Duke_OH_NG', q1.rate_class_alias)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(0.359067701778001, q1.price)

        parser = GuttmanGas()
        with open(self.GUTTMAN_PEOPLE_TWP_FILE_PATH, 'rb') as \
                spreadsheet:
            parser.load_file(spreadsheet, basename(
                self.GUTTMAN_PEOPLE_TWP_FILE_PATH), None)
        parser.validate()
        self.assertEqual(0, parser.get_count())
        quotes = list(parser.extract_quotes())
        self.assertEqual(170, len(quotes))
        self.assertEqual(170, parser.get_count())

        q1 = quotes[0]
        self.assertEqual(datetime(2017, 03, 16), q1.start_from)
        self.assertEqual(datetime(2017, 04, 01), q1.start_until)
        self.assertEqual(6, q1.term_months)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(datetime(2016, 2, 24, 8, 45, 18), q1.valid_from)
        self.assertEqual(datetime(2016, 2, 25, 8, 45, 18), q1.valid_until)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(5 * 1000, q1.limit_volume)
        self.assertEqual('Guttman-gas-Pennsylvania_PNG_PA-TWP', q1.rate_class_alias)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(0.23387397558386497, q1.price)

        parser = GuttmanGas()
        with open(self.GUTTMAN_CPA_MATRIX_FILE_PATH, 'rb') as \
                spreadsheet:
            parser.load_file(spreadsheet, basename(
                self.GUTTMAN_CPA_MATRIX_FILE_PATH), None)
        parser.validate()
        self.assertEqual(0, parser.get_count())
        quotes = list(parser.extract_quotes())
        self.assertEqual(340, len(quotes))
        self.assertEqual(340, parser.get_count())

        q1 = quotes[0]
        self.assertEqual(datetime(2017, 03, 16), q1.start_from)
        self.assertEqual(datetime(2017, 04, 01), q1.start_until)
        self.assertEqual(6, q1.term_months)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(datetime(2016, 2, 24, 8, 45, 18), q1.valid_from)
        self.assertEqual(datetime(2016, 2, 25, 8, 45, 18), q1.valid_until)
        self.assertEqual(3001, q1.min_volume)
        self.assertEqual(5 * 1000, q1.limit_volume)
        self.assertEqual('Guttman-gas-Pennsylvania_ColumbiaGas_PA', q1.rate_class_alias)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(0.311692133002453, q1.price)

        parser = GuttmanGas()
        with open(self.GUTTMAN_PEOPLE_MATRIX_FILE_PATH, 'rb') as \
                spreadsheet:
            parser.load_file(spreadsheet, basename(
                self.GUTTMAN_PEOPLE_MATRIX_FILE_PATH), None)
        parser.validate()
        self.assertEqual(0, parser.get_count())
        quotes = list(parser.extract_quotes())
        self.assertEqual(170, len(quotes))
        self.assertEqual(170, parser.get_count())

        q1 = quotes[0]
        self.assertEqual(datetime(2017, 03, 16), q1.start_from)
        self.assertEqual(datetime(2017, 04, 01), q1.start_until)
        self.assertEqual(6, q1.term_months)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(datetime(2016, 2, 24, 8, 45, 18), q1.valid_from)
        self.assertEqual(datetime(2016, 2, 25, 8, 45, 18), q1.valid_until)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(5 * 1000, q1.limit_volume)
        self.assertEqual('Guttman-gas-Pennsylvania_PNG_PA', q1.rate_class_alias)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(0.23321922357323302, q1.price)

        parser = GuttmanGas()
        with open(self.GUTTMAN_COH_MATRIX_FILE_PATH, 'rb') as \
                spreadsheet:
            parser.load_file(spreadsheet, basename(
                self.GUTTMAN_COH_MATRIX_FILE_PATH), None)
        parser.validate()
        self.assertEqual(0, parser.get_count())
        quotes = list(parser.extract_quotes())
        self.assertEqual(510, len(quotes))
        self.assertEqual(510, parser.get_count())

        q1 = quotes[0]
        self.assertEqual(datetime(2017, 03, 16), q1.start_from)
        self.assertEqual(datetime(2017, 04, 01), q1.start_until)
        self.assertEqual(6, q1.term_months)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(datetime(2016, 2, 24, 8, 45, 17), q1.valid_from)
        self.assertEqual(datetime(2016, 2, 25, 8, 45, 17), q1.valid_until)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(5 * 1000, q1.limit_volume)
        self.assertEqual('Guttman-gas-Ohio_ColumbiaGas_OH', q1.rate_class_alias)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(0.39786567696795805, q1.price)

    def test_aep(self):
        parser = AEPMatrixParser()
        self.assertEqual(0, parser.get_count())

        with open(self.AEP_FILE_PATH, 'rb') as spreadsheet:
            parser.load_file(spreadsheet, basename(self.AEP_FILE_PATH), None)
        parser.validate()
        self.assertEqual(0, parser.get_count())

        quotes = list(parser.extract_quotes())
        self.assertEqual(8415, len(quotes))
        self.assertEqual(8415, parser.get_count())
        for quote in quotes:
            quote.validate()

        # since there are so many, only check one
        q1 = quotes[0]
        self.assertEqual(datetime(2015, 11, 1), q1.start_from)
        self.assertEqual(datetime(2015, 12, 1), q1.start_until)
        self.assertEqual(12, q1.term_months)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(datetime(2015, 11, 12), q1.valid_from)
        self.assertEqual(datetime(2015, 11, 13), q1.valid_until)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(100 * 1000, q1.limit_volume)
        self.assertEqual('AEP-electric-IL-Ameren_Zone_1_CIPS-DS2-SECONDARY', q1.rate_class_alias)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(0.05628, q1.price)

    def test_champion(self):
        parser = ChampionMatrixParser()
        self.assertEqual(0, parser.get_count())

        with open(self.CHAMPION_FILE_PATH, 'rb') as spreadsheet:
            parser.load_file(spreadsheet, basename(self.CHAMPION_FILE_PATH), None)
        parser.validate()
        self.assertEqual(0, parser.get_count())

        quotes = list(parser.extract_quotes())
        self.assertEqual(3780, len(quotes))

        for quote in quotes:
            quote.validate()

        q1 = quotes[0]
        self.assertEqual(datetime(2015, 12, 1), q1.start_from)
        self.assertEqual(datetime(2016, 1, 1), q1.start_until)
        self.assertEqual(datetime.utcnow().date(), q1.date_received.date())
        self.assertEqual(12, q1.term_months)
        self.assertEqual(0, q1.min_volume)
        self.assertEqual(100000, q1.limit_volume)
        self.assertEqual('Champion-electric-PA-DQE-GS-General service', q1.rate_class_alias)
        self.assertEqual(False, q1.purchase_of_receivables)
        self.assertEqual(0.07063, q1.price)

    def test_gee_gas_nj(self):
        parser = GEEGasNJParser()

        with open(self.GEE_GAS_PATH_NJ, 'rb') as pdf_file:
            parser.load_file(pdf_file, None, None)
            parser.validate()
            quotes_nj = list(parser.extract_quotes())

        self.assertEqual(len(quotes_nj), 128)

        self.assertAlmostEqual(quotes_nj[0].price, 0.3591, delta=0.000001)
        self.assertEqual(quotes_nj[0].min_volume, 0)
        self.assertEqual(quotes_nj[0].limit_volume, 9999)
        self.assertEqual(quotes_nj[0].term_months, 6)
        self.assertEqual(quotes_nj[0].start_from, datetime(2016, 1, 1))
        self.assertEqual(quotes_nj[0].valid_from, datetime(2016, 1, 7))
        self.assertEqual(quotes_nj[0].valid_until, datetime(2016, 1, 8))
        self.assertEqual(quotes_nj[0].rate_class_alias, 'GEE-gas-NJ Commercial-Etown-Non-Heat')
        self.assertIn('NJ Commercial,Etown Non-Heat,start 2016-01-01,6 month,0.3591', quotes_nj[0].file_reference[0])

        self.assertEqual(quotes_nj[-22].min_volume, 0)
        self.assertEqual(quotes_nj[-22].limit_volume, 9999)
        self.assertEqual(quotes_nj[-22].term_months, 18)
        self.assertEqual(quotes_nj[-22].start_from, datetime(2016, 3, 1))
        self.assertEqual(quotes_nj[-22].start_until, datetime(2016, 4, 1))
        self.assertEqual(quotes_nj[-22].valid_from, datetime(2016, 1, 7))
        self.assertAlmostEqual(quotes_nj[-22].price, 0.5372, delta=0.000001)

        self.assertAlmostEqual(quotes_nj[-1].price, 0.5057, delta=0.000001)
        self.assertEqual(quotes_nj[-1].min_volume, 0)
        self.assertEqual(quotes_nj[-1].limit_volume, 9999)
        self.assertEqual(quotes_nj[-1].term_months, 24)
        self.assertEqual(quotes_nj[-1].start_from, datetime(2016, 4, 1))
        self.assertEqual(quotes_nj[-1].start_until, datetime(2016, 5, 1))
        self.assertEqual(quotes_nj[-1].valid_from, datetime(2016, 1, 7))

    def test_entrust(self):
        parser = EntrustMatrixParser()
        self.assertEqual(0, parser.get_count())

        with open(self.ENTRUST_FILE_PATH, 'rb') as spreadsheet:
            parser.load_file(spreadsheet, None, None)
        parser.validate()
        self.assertEqual(0, parser.get_count())

        quotes = list(parser.extract_quotes())
        self.assertEqual(14073, len(quotes))

        for quote in quotes:
            quote.validate()

        q = quotes[0]
        self.assertEqual(datetime(2016, 10, 1), q.start_from)
        self.assertEqual(datetime(2016, 11, 1), q.start_until)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(12, q.term_months)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(100000, q.limit_volume)
        self.assertEqual('Entrust-electric-Commonwealth Edison (C28) (0 -100 kw)', q.rate_class_alias)
        self.assertEqual(0.0658, q.price)
        self.assertEqual(q.service_type, ELECTRIC)

        # since this one is especially complicated and also missed a row,
        # check the last quote too. (this also checks the "sweet spot"
        # columns which work differently from the other ones)
        q = quotes[-1]
        self.assertEqual(datetime(2018, 3, 1), q.start_from)
        self.assertEqual(datetime(2018, 4, 1), q.start_until)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(24, q.term_months)
        self.assertEqual(600000, q.min_volume)
        self.assertEqual(1e6, q.limit_volume)
        self.assertEqual('Entrust-electric-Consolidated Edison - Zone J', q.rate_class_alias)
        self.assertEqual(0.0687, q.price)
        self.assertEqual(q.service_type, ELECTRIC)

    def test_spark(self):
        parser = SparkMatrixParser()
        self.assertEqual(0, parser.get_count())

        with open(self.SPARK_FILE_PATH, 'rb') as spreadsheet:
            parser.load_file(spreadsheet, None, None)
        parser.validate()
        self.assertEqual(0, parser.get_count())

        quotes = list(parser.extract_quotes())
        self.assertEqual(60 * 5, len(quotes))
        for quote in quotes:
            quote.validate()

        q = quotes[0]
        self.assertEqual(datetime(2016, 2, 1), q.start_from)
        self.assertEqual(datetime(2016, 3, 1), q.start_until)
        self.assertEqual(3, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(datetime(2016, 1, 25), q.valid_from)
        self.assertEqual(datetime(2016, 1, 26), q.valid_until)
        self.assertEqual(0, q.min_volume)
        self.assertEqual(50000, q.limit_volume)
        self.assertEqual('NJ-PSEG-PSEG-GLP', q.rate_class_alias)
        self.assertEqual(.1097, q.price)
        self.assertEqual(q.service_type, ELECTRIC)

        q = quotes[-1]
        self.assertEqual(datetime(2016, 5, 1), q.start_from)
        self.assertEqual(datetime(2016, 6, 1), q.start_until)
        self.assertEqual(36, q.term_months)
        self.assertEqual(datetime.utcnow().date(), q.date_received.date())
        self.assertEqual(datetime(2016, 1, 25), q.valid_from)
        self.assertEqual(datetime(2016, 1, 26), q.valid_until)
        self.assertEqual(2e5, q.min_volume)
        self.assertEqual(1e6, q.limit_volume)
        self.assertEqual('NY-CONED-ZONE J-SC9', q.rate_class_alias)
        self.assertEqual(.0766, q.price)
        self.assertEqual(q.service_type, ELECTRIC)
