"""Validation logic for the configuration file.
TODO: find someplace to put this other than the root directory.
"""
from boto.s3.connection import OrdinaryCallingFormat, S3Connection
from formencode.exc import FERuntimeWarning
from formencode.schema import Schema
from formencode.validators import (StringBool, String, URL, Int, Number, Email,
                                   OneOf, Empty)
from formencode.compound import All, Any
from os.path import isdir
from formencode.api import FancyValidator, Invalid


class InvalidDirectoryPath(Invalid):
    '''Special exception for directory paths, because errors about these are
    ignored when validating config files meant for deployment on a different
    host.
    '''

class TCPPort(Int):
    min = 1
    max = 65535

# class Directory(FancyValidator):
#     def _convert_to_python(self, value, state):
#         if isdir(value): return value
#         raise InvalidDirectoryPath("Please specify a valid directory",
#                                    value, state)
class Directory(String):
    # existence of directory paths has to be ignored in order to check
    # validity of a config file while not running on the host where those
    # directories exist.
    # also note that it is not possible to use a custom subclass of
    # Invalid because formencode will catch it and re-raise Invalid.
    pass

class CallingFormat(FancyValidator):
    def _convert_to_python(self, value, state):
        if value == 'OrdinaryCallingFormat':
            return OrdinaryCallingFormat()
        elif value == 'DefaultCallingFormat':
            return S3Connection.DefaultCallingFormat
        raise Invalid('Please specify a valid calling format.')

class db(Schema):
    # database connection URI
    uri = String()
    altitude_uri = String()
    echo = StringBool()
    # name of superuser for restoring from backup (can drop/create DB,
    # create extension)
    superuser_name = String()

class brokerage(Schema):
    # name of Amazon S3 bucket where quote files will be uploaded
    quote_file_bucket = String()

class aws_s3(Schema):
    # utility bill file storage in Amazon S3
    bucket = String()
    aws_access_key_id = String()
    aws_secret_access_key = String()
    host = String()
    port = TCPPort()
    is_secure = StringBool()
    calling_format = All(CallingFormat(),
                         OneOf(['OrdinaryCallingFormat',
                                'DefaultCallingFormat']))
    # optional settings for boto HTTP requests
    # note: empty values get converted to None
    num_retries = Any(validators=[Number(), Empty()])
    max_retry_delay = Any(validators=[Number(), Empty()])
    http_socket_timeout = Any(validators=[Number(), Empty()])


class monitoring(Schema):
    # for submitting application metrics to a collection daemon such as StatsD
    metrics_host = String()
    metrics_port = TCPPort()

class billentry(Schema):
    google_client_id = String()
    google_client_secret = String()
    google_user_info_url = URL()
    redirect_uri = String()
    base_url = URL()
    authorize_url = URL()
    request_token_url = URL()
    request_token_params_scope = String()
    request_token_params_resp_type = String()
    access_token_url = URL()
    access_token_method = String()
    access_token_params_grant_type = String()
    disable_authentication = StringBool()
    authorized_domain = String()
    show_traceback_on_error = StringBool()
    secret_key = String()
    wiki_url = String()
    timeout = Int()

#Logging

class loggers(Schema):
    keys = String()

class handlers(Schema):
    keys = String()

class formatters(Schema):
    keys = String()

class logger_root(Schema):
    level = String()
    handlers = String()

class logger_read_quotes(Schema):
    level = String()
    handlers = String()
    qualname = String()

class handler_consoleHandler(Schema):
    level = String()
    formatter = String()
    args = String()
handler_consoleHandler.add_field('class', String())

class handler_read_quotes_handler(Schema):
    level = String()
    formatter = String()
    args = String()
handler_read_quotes_handler.add_field('class', String())

class formatter_simpleFormatter(Schema):
    format = String()

