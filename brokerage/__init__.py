import os
import os.path as path
import re
from os.path import dirname, realpath

import statsd

from brokerage import configuration as config_file_schema
from util.validated_config_parser import ValidatedConfigParser

__all__ = ['util', 'processing', 'init_logging', 'init_config', 'init_model',
           'initialize', 'config', 'import_all_model_modules', 'ROOT_PATH']

ROOT_PATH = dirname(dirname(realpath(__file__)))

# import this object after calling 'init_config' to get values from the
# config file
config = None

def init_config(filepath='settings.cfg', fp=None):
    """Sets `billing.config` to an instance of
    :class:`billing.lib.config.ValidatedConfigParser`.

    :param filepath: The configuration file path; default `settings.cfg`.
    :param fp: A configuration file pointer to be used in place of filename
    """
    import logging

    log = logging.getLogger(__name__)

    global config
    config = ValidatedConfigParser(config_file_schema)
    if fp:
        log.debug('Reading configuration fp')
        config.readfp(fp)
    else:
        absolute_path = path.join(ROOT_PATH, filepath)
        log.debug('Reading configuration file %s' % absolute_path)
        config.read(absolute_path)

    if not config.has_section('main'):
        config.add_section('main')
    config.set('main', 'appdir', dirname(realpath(__file__)))
    log.debug('Initialized configuration')

    # set boto's options for AWS HTTP requests according to the aws_s3
    # section of the config file.
    # it is necessary to override boto's defaults because the default
    # behavior is to repeat every request 6 times with an extremely long
    # timeout and extremely long interval between attempts, making it hard to
    # tell when the server is not responding.
    # this will override ~/.boto and/or /etc/boto.cfg if they exist (though we
    # should not have those files).
    import boto
    if not boto.config.has_section('Boto'):
        boto.config.add_section('Boto')
    for key in ['num_retries', 'max_retry_delay', 'http_socket_timeout']:
        value = config.get('aws_s3', key)
        if value is not None:
            boto.config.set('Boto', key, str(value))

    # all statsd.Client objects will use these connection parameters by default
    statsd.Connection.set_defaults(
        host=config.get('monitoring', 'metrics_host'),
        port=config.get('monitoring', 'metrics_port'))

def get_db_params():
    """:return a dictionary of parameters for connecting to the main
    database, taken from the URI in the config file."""
    assert config is not None
    db_uri = config.get('db', 'uri')
    PG_FORMAT = r'^\S+://(\S+):(\S+)@(\S+)/(\S+)$'
    m = re.match(PG_FORMAT, db_uri)
    db_params = dict(zip(['user', 'password', 'host', 'db'], m.groups()))
    return db_params

def init_logging(filepath='settings.cfg'):
    """Initializes logging"""
    import logging, logging.config
    absolute_path = path.join(ROOT_PATH, filepath)
    logging.config.fileConfig(absolute_path)
    log = logging.getLogger(__name__)
    log.debug('Initialized logging')


def import_all_model_modules():
    """Import all modules that contain SQLAlchemy model classes. In some
    cases SQLAlchemy requires these classes to be imported so it can be aware
    of them, even if they are not used.
    """
    import brokerage.model
    # ensure that these imports don't get auto-deleted! they have side effects.
    brokerage.model


def get_scrub_sql():
    """Return SQL code (string) that can be executed to transform a copy of a
    production database into one that can be used into a development
    environment, by replacing certain data with substitute values.
    """
    # it seems incredibly hard to get SQLAlchemy to emit a fully-compiled SQL
    # string that including data values. i gave up after trying this method with
    # the "dialect" sqlalchemy.dialects.mysql.mysqldb.MySQLDialect()
    # https://sqlalchemy.readthedocs.org/en/latest/faq/sqlexpressions.html
    # #how-do-i-render-sql-expressions-as-strings-possibly-with-bound
    # -parameters-inlined
    sql_format = ("update %(table)s set %(col)s = %(sub_value)s "
                  "where %(col)s is not null;")
    return '\n'.join(
        sql_format % dict(table=c.table.name, col=c.name, sub_value=v)
        for c, v in get_scrub_columns().iteritems())


def get_scrub_columns():
    # This only contained reebill things, which we no longer need.
    return {}

def init_model(uri=None, schema_revision=None):
    """Initializes the sqlalchemy data model.
    """
    from brokerage.model import Session, Base
    from sqlalchemy import create_engine
    import logging
    log = logging.getLogger(__name__)

    import_all_model_modules()

    uri = uri if uri else config.get('db', 'uri')
    engine = create_engine(uri, #echo=config.get('db', 'echo'),
                           # recreate database connections every hour, to avoid
                           # "MySQL server has gone away" error when they get
                           # closed due to inactivity
                           pool_recycle=3600,
                           isolation_level='SERIALIZABLE'
                           )
    if config.get('db', 'echo'):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    Session.configure(bind=engine)
    # TODO: unclear why the above does not work and Session.bind must be
    # directly assigned
    Session.bind = engine
    Base.metadata.bind = engine

    Session.remove()

    log.debug('Initialized database: %s' % engine)

def init_altitude_db(uri=None):
    """Initialize the Altitude SQL Server database. This is a separate function
    from init_model because the two databases are not necessarily used at the
    same time.
    """
    from brokerage.model import AltitudeSession, AltitudeBase, altitude_metadata
    from sqlalchemy import create_engine
    import logging
    log = logging.getLogger(__name__)

    import_all_model_modules()

    uri = uri if uri else config.get('db', 'altitude_uri')
    engine = create_engine(uri, echo=config.get('db', 'echo'),
        pool_recycle=3600)

    altitude_metadata.bind = engine
    AltitudeSession.configure(bind=engine)
    AltitudeSession.bind = engine
    AltitudeBase.metadata.bind = engine
    AltitudeSession.remove()

    log.debug('Initialized database: %s' % engine)


def initialize():
    init_logging()
    init_config()
    init_model()
    init_altitude_db()
