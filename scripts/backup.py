#!/usr/bin/env python
'''
Back up/restore database to/from S3.
'''
import argparse
import os
import sys
from StringIO import StringIO
from gzip import GzipFile
import zlib

from boto.s3.connection import S3Connection

from brokerage import init_config, init_model, get_scrub_sql, get_db_params
from util.shell import run_command

init_config()
from brokerage import config

# all backups are stored with the same key name. a new version is created every
# time the database is backed up, the latest version is used automatically
# whenever the key is accessed without specifying a version.
# TODO change name to something like "quote_db.gz". do not make backups until
# the name is changed.
BACKUP_FILE_NAME = 'billing_db.gz'

# force no password prompt because it shouldn't be necessary and isn't
# entered through the subprocess stdin
DROP_COMMAND = 'dropdb --if-exists %(db)s -h %(host)s -U %(user)s -w'
CREATE_COMMAND = 'createdb %(db)s %(host)s -U %(user)s -w'
DUMP_COMMAND = 'pg_dump %(db)s -h %(host)s -U %(user)s -w -O'
DB_SHELL_COMMAND = 'psql %(db)s -h %(host)s -U %(user)s -w'
TEMP_DB_NAME = 'template1'

# extract database connection parameters from URI in config file
db_params = get_db_params()
superuser_db_params = dict(get_db_params(),
                           user=config.get('db', 'superuser_name'))

# amount of data to read and compress at one time in bytes
GZIP_CHUNK_SIZE_BYTES = 128 * 1024


def _write_gzipped_chunk(in_file, out_file):
    '''Write gzipped data from 'in_file' to 'out_file' until 'out_file'
    contains 'chunk_size' of gzipped data (or until reaching the end of
    'in_file'). Note that more than 'chunk_size' may be read from 'in_file' to
    get 'chunk_size' bytes of data after compression.
    Return True if the end of 'in_file' has been reached, False otherwise.
    '''
    out_file.seek(0)
    out_file.truncate()

    # A GzipFile wraps another file object (its 'fileobj') and implements the
    # same interface as a regular file. when you write to the GzipFile, it
    # writes a compressed version of what you wrote to its 'fileobj'.
    gzipper = GzipFile(fileobj=out_file, mode='w')

    while True:
        data = in_file.read(GZIP_CHUNK_SIZE_BYTES)
        if data == '':
            return True
        gzipper.write(data)

class UnGzipFile(object):
    '''File object wrapper that un-gzips data written to it--like the built-in
    'GzipFile' class, but for un-compressing data. GzipFile's "read" mode
    won't work here because boto doesn't provide a file object to read from.
    '''
    def __init__(self, fileobj):
        '''fileobj: file object to receive uncompressed data when 'write' is
        called with compressed data.
        '''
        # see http://stackoverflow.com/a/22310760
        self._decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
        self._fileobj = fileobj

    def write(self, data):
        '''Decompress 'data' and write the result to 'fileobj'.
        '''
        uncompressed_data = self._decompressor.decompress(data)
        self._fileobj.write(uncompressed_data)

def write_gzipped_to_s3(in_file, s3_key, call_before_complete=lambda: None):
    '''Write the file 'in_file' to 's3_key' (boto.s3.key.Key object). A
    multipart upload is used so that 'in_file' does not have to support seeking
    (meaning it can be a file with indeterminate length, like the stdout of a
    process).

    'call_before_complete': optional callable that can raise an exception to
    cancel the upload instead of completing it. (boto's documentation suggests
    that Amazon may charge for storage of incomplete upload parts.)
    '''
    multipart_upload = s3_key.bucket.initiate_multipart_upload(s3_key)

    # write a chunk of gzipped data into 'temp_file', then
    # upload the contents of 'chunk_buffer' to S3
    temp_file = StringIO()
    _write_gzipped_chunk(in_file, temp_file)
    temp_file.seek(0)
    multipart_upload.upload_part_from_file(temp_file, 1)

    try:
        call_before_complete()
    except:
        multipart_upload.cancel_upload()
        raise
    multipart_upload.complete_upload()

def write_gzipped_to_file(in_file, out_file):
    '''Write the file 'in_file' to 's3_key' (boto.s3.key.Key object). A
    multipart upload is used so that 'in_file' does not have to support seeking
    (meaning it can be a file with indeterminate length, like the stdout of a
    process).

    'call_before_complete': optional callable that can raise an exception to
    cancel the upload instead of completing it. (boto's documentation suggests
    that Amazon may charge for storage of incomplete upload parts.)
    '''
    _write_gzipped_chunk(in_file, out_file)


def _refresh_s3_key(key):
    '''Return a new boto.s3.key.Key object so it reflects what is actually in
    s3 corresponding to the given Key object. If a new version has been
    created, this must be called in order for key.version_id and
    key.last_modified to be correct.
    '''
    return key.bucket.get_key(key.name)

def backup_main_db(s3_key):
    command = DUMP_COMMAND % db_params
    _, stdout, check_exit_status = run_command(command)
    write_gzipped_to_s3(stdout, s3_key, check_exit_status)
    s3_key = _refresh_s3_key(s3_key)
    print 'created S3 key %s/%s version %s at %s' % (
            s3_key.bucket.name, s3_key.name, s3_key.version_id,
            s3_key.last_modified)

def backup_main_db_local(file_path):
    command = DUMP_COMMAND % db_params
    _, stdout, check_exit_status = run_command(command)
    with open(file_path,'wb') as out_file:
        write_gzipped_to_file(stdout, out_file)

def _recreate_main_db():
    '''Drop and re-create the main database because pg_dump only includes drop
    commands for tables that already exist in the backup.
    '''
    # Postgres requires you to connect to a different database while dropping
    # the current database. the "template1" database is always guaranteed to
    # exist.
    #command = DB_SHELL_COMMAND % dict(superuser_db_params, db=TEMP_DB_NAME)
    command = DB_SHELL_COMMAND % dict(db_params, db=TEMP_DB_NAME)
    stdin, _, check_exit_status = run_command(command)
    # TODO: this was meant to disconnect other users of the database but is temporarily disabled
    ## Don't allow new connections
    #stdin.write(
        #"update pg_database set datallowconn = 'false' where datname = '%(db)s';" % db_params)
    ## Disconnect all existing connections
    #stdin.write(
        #"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '%(db)s';" % db_params)
    # Drop and create database
    stdin.write(
        'drop database if exists %(db)s; create database %(db)s with owner %(user)s;' % db_params)
    ## Re-allow new connections
    #stdin.write(
        #"update pg_database set datallowconn = 'true' where datname = '%(db)s;'" % db_params)
    stdin.close()
    check_exit_status()

def restore_main_db_s3(bucket):
    _recreate_main_db()
    command = DB_SHELL_COMMAND % superuser_db_params
    stdin, _, check_exit_status = run_command(command)
    ungzip_file = UnGzipFile(stdin)

    key = bucket.get_key(BACKUP_FILE_NAME)
    if not key or not key.exists():
        raise ValueError('The key "%s" does not exist in the bucket "%s"' % (
                BACKUP_FILE_NAME, bucket.name))
    print 'restoring main database from %s/%s version %s (modified %s)' % (
            bucket.name, key.name, key.version_id, key.last_modified)
    key.get_contents_to_file(ungzip_file)
    stdin.write('reassign owned by %s to %s' % (
        superuser_db_params['user'], db_params['user']))

    # stdin pipe must be closed to make the process exit
    stdin.close()
    check_exit_status()

def restore_main_db_local(dump_file_path):
    _recreate_main_db()
    command = DB_SHELL_COMMAND % superuser_db_params
    stdin, _, check_exit_status = run_command(command)
    ungzip_file = UnGzipFile(stdin)

    print 'restoring main database from local file %s' % dump_file_path
    # TODO: maybe bad to read whole file at once
    with open(dump_file_path) as dump_file:
        ungzip_file.write(dump_file.read())
    stdin.write('reassign owned by %s to %s' % (
        superuser_db_params['user'], db_params['user']))

    stdin.close()
    check_exit_status()

def scrub_dev_data():
    '''Replace some data with placeholder values for development environment.
    Obviously this should not be used in production.
    TODO: the right way to do this is to scrub the data before it even gets
    into a development environment, just in case.
    '''
    command = DB_SHELL_COMMAND % db_params
    stdin, _, check_exit_status = run_command(command)
    sql = get_scrub_sql()
    print 'scrub commands:\n%s' % sql
    stdin.write(sql)
    stdin.close()
    check_exit_status()

def get_bucket(bucket_name, connection, enforce_versioning=True):
    bucket = connection.get_bucket(bucket_name)
    # make sure this bucket has versioning turned on; if not, it's probably
    # the wrong bucket
    if enforce_versioning:
        versioning_status = bucket.get_versioning_status()
        if versioning_status != {'Versioning': 'Enabled'}:
            print >> sys.stderr, ("Can't use a bucket without versioning for "
                    "backups. The bucket \"%s\" has versioning status: %s") % (
                    bucket.name, versioning_status)
            # TODO not good to sys.exit outside main
            sys.exit(1)
    return bucket

def backup(args):
    conn = S3Connection(args.access_key, args.secret_key)
    bucket = get_bucket(args.bucket, conn)
    backup_main_db(bucket.get_key(BACKUP_FILE_NAME))

def restore(args):
    conn = S3Connection(args.access_key, args.secret_key)
    bucket = get_bucket(args.bucket, conn)
    restore_main_db_s3(bucket)
    if args.scrub:
        scrub_dev_data()

def download(args):
    if args.local_dir.startswith(os.path.sep):
        local_dir_absolute_path = args.local_dir
    else:
        local_dir_absolute_path = os.path.join(
            os.path.realpath(__file__), args.local_dir)
    # TODO actual error message
    assert os.access(local_dir_absolute_path, os.W_OK)

    conn = S3Connection(args.access_key, args.secret_key)
    bucket = get_bucket(args.bucket, conn)

    # download main database dump
    key = bucket.get_key(BACKUP_FILE_NAME)
    if not key or not key.exists():
        raise ValueError('The key "%s" does not exist in the bucket "%s"' % (
                key.name, bucket.name))
    key.get_contents_to_filename(os.path.join(
            local_dir_absolute_path, BACKUP_FILE_NAME))

def get_key_names_for_account(account_id):
    init_model()
    ubl = UtilBillLoader()
    utilbills = ubl.get_utilbills_for_account_id(account_id)
    return [BillFileHandler.get_key_name_for_utilbill(u) for u in utilbills]

def backup_local(args):
    backup_main_db_local(os.path.join(args.local_dir, BACKUP_FILE_NAME))

def restore_local(args):
    restore_main_db_local(os.path.join(args.local_dir, BACKUP_FILE_NAME))
    # TODO always scrub the data when restore-local is used because it's only for development?
    if args.scrub:
        scrub_dev_data()

if __name__ == '__main__':
    main_parser = argparse.ArgumentParser(description=(
        "Backup script for database. Database credentials are read from the "
        "application config file (settings.cfg). "))

    subparsers = main_parser.add_subparsers()
    backup_parser = subparsers.add_parser('backup',
            help='write database dump files to the given S3 bucket')
    restore_parser = subparsers.add_parser('restore',
            help='restore databases from existing dump files in S3 bucket')
    download_parser = subparsers.add_parser('download',
            help=('download database dump files so they can be used '
            'with "restore-local"'))
    restore_local_parser = subparsers.add_parser('restore-local', help=(
            'restore databases from existing dump files in local directory'))
    backup_local_parser = subparsers.add_parser('backup-local', help=(
            'backup databases to local directory'))

    # arguments for S3
    for parser in (backup_parser, restore_parser, download_parser):
        parser.add_argument(dest='bucket', type=str, help='S3 bucket name')

    # the environment variables that provide default values for these keys
    # come from Josh's bash script, documented here:
    # https://bitbucket.org/skylineitops/docs/wiki/EnvironmentSetup#markdown-header-setting-up-s3-access-keys-for-destaging-application-data
    for parser in (backup_parser, restore_parser, download_parser):
        parser.add_argument("--access-key", type=str,
                default=os.environ.get('AWS_ACCESS_KEY_ID', None),
                help=("AWS S3 access key. Default $AWS_ACCESS_KEY_ID if it is defined."))
        parser.add_argument("--secret-key", type=str,
                default=os.environ.get('AWS_SECRET_ACCESS_KEY', None),
                help=("AWS S3 secret key. Default $AWS_SECRET_ACCESS_KEY if "
                "it is defined."))

    # arguments for local backup files
    all_file_names = [BACKUP_FILE_NAME]
    for parser in (download_parser, restore_local_parser,
        backup_local_parser):
        parser.add_argument(dest='local_dir', type=str,
                help=('Local directory containing database dump files (%s)' %
                ', '.join(all_file_names)))

    # args for restoring databases
    for parser in (restore_parser, restore_local_parser):
        parser.add_argument('--scrub', action='store_true',
                help=('After restoring, replace parts of the data set with '
                'placeholder values (for development only).'))

    # each command corrsponds to the function with the same name defined above
    backup_parser.set_defaults(func=backup)
    restore_parser.set_defaults(func=restore)
    restore_parser.set_defaults(func=restore)
    download_parser.set_defaults(func=download)
    restore_local_parser.set_defaults(func=restore_local)
    backup_local_parser.set_defaults(func=backup_local)

    args = main_parser.parse_args()
    args.func(args)
