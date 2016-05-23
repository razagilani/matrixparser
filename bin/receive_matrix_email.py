#!/usr/bin/env python
"""Receive quotes from suppliers' "matrix" spreadsheets in email attachments.
Pipe an email into stdin to process it.
"""
import logging
import traceback
from fcntl import flock, LOCK_EX
from sys import stdin

from boto.s3.connection import S3Connection

from brokerage import initialize
from brokerage.model import AltitudeSession, Session
from brokerage.quote_email_processor import QuoteEmailProcessor, QuoteDAO, \
    LOG_NAME
from brokerage.quote_parsers import CLASSES_FOR_FORMATS


def split_altitude_uri(altitude_uri):
    protocol, host_str = altitude_uri.split("://")
    auth, server = host_str.split("@")
    username, password = auth.split(":")
    server, _  = server.split('?')
    server, database = server.split('/')

    return server, username, password, database


if __name__ == '__main__':
    # temporary hack: the giant SQL statement below is believed to
    # cause performance problems when run in MS SQL Server, which
    # could be reduced by only running instance of this script at a time.
    # however, the SQL statement is not necessary.
    f = open(__file__)
    flock(f, LOCK_EX)

    try:
        # logger initially has no handlers; initialize() adds them according
        # to config file
        logger = logging.getLogger(LOG_NAME)
        logger.setLevel(logging.DEBUG)
        initialize()

        from brokerage import config
        logger.info('HELLO')
        s3_connection = S3Connection(
            config.get('aws_s3', 'aws_access_key_id'),
            config.get('aws_s3', 'aws_secret_access_key'),
            is_secure=config.get('aws_s3', 'is_secure'),
            port=config.get('aws_s3', 'port'),
            host=config.get('aws_s3', 'host'),
            calling_format=config.get('aws_s3', 'calling_format'))
        s3_bucket_name = config.get('brokerage', 'quote_file_bucket')
        qep = QuoteEmailProcessor(CLASSES_FOR_FORMATS, QuoteDAO(),
                                  s3_connection, s3_bucket_name)
        qep.process_email(stdin)
    except Exception as e:
        logger.error('Error when processing email:\n%s' % (
            traceback.format_exc()))
        # it is important to exit with non-0 status when an error happened,
        # because that causes Postfix to send a bounce email with the error
        # message
        raise
    finally:
        Session.remove()
        AltitudeSession.remove()
