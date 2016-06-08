import os

from sqlalchemy import create_engine

from brokerage.model import Session, Base, AltitudeBase, AltitudeSession
from brokerage import import_all_model_modules, ROOT_PATH


def init_test_config():
    from brokerage import init_config
    from os.path import realpath, join, dirname
    init_config(filepath=join(dirname(realpath(__file__)), 'tstsettings.cfg'))

__all__ = ['BillMailerTest', 'ReebillFileHandlerTest', 'ProcessTest',
           'ReebillProcessingTest', 'BillUploadTest', 'ChargeUnitTests',
           'RateStructureDAOTest', 'UtilBillTest', 'UtilbillLoaderTest',
           'UtilbillProcessingTest', 'ExporterTest', 'FetchTest',
           'JournalTest', 'ReebillTest', 'StateDBTest', 'DateUtilsTest',
           'HolidaysTest', 'MonthmathTest']


def create_tables():
    """Drop and (re-)create tables in the test database according to the
    SQLAlchemy schema.

    Call this after init_test_config() and before init_model(). Call this
    only once before running all tests; it doesn't need to be re-run before
    each test.
    """
    # there must be no open transactions in order to drop tables
    Session.remove()

    from brokerage import config
    uri = config.get('db', 'uri')
    engine = create_engine(uri, echo=config.get('db', 'echo'))

    import_all_model_modules()

    Base.metadata.bind = engine

    Base.metadata.drop_all()

    Base.metadata.create_all(checkfirst=True)

    cur_dir = os.getcwd()
    os.chdir(ROOT_PATH)

    os.chdir(cur_dir)
    Session().commit()


    # also create tables in the other database
    engine = create_engine(config.get('db', 'altitude_uri'))
    AltitudeBase.metadata.bind = engine
    AltitudeBase.metadata.create_all()


def clear_db():
    """Remove all data from the test database. This should be called before and
    after running any test that inserts data.
    """
    for S in [Session, AltitudeSession]:
        # OK to skip any database that is not initialized (in practice should
        # only apply to AltitudeSession)
        if S.bind is None:
            return

        s = S()

        S.rollback()

        if S is Session:
            base = Base
        else:
            assert S is AltitudeSession
            base = AltitudeBase
        for t in reversed(base.metadata.sorted_tables):
            s.execute(t.delete())
        s.commit()
