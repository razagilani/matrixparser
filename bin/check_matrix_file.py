#!/usr/bin/env python
import os
from sys import stderr

import click
from sqlalchemy.orm.exc import NoResultFound

from brokerage import init_config, init_altitude_db, init_model
from brokerage.model import MatrixFormat
from brokerage.model import Session, MatrixFormat
from brokerage.quote_parsers import CLASSES_FOR_FORMATS


@click.command(
    help='Check validation and parsing of a matrix quote file. SUPPLIER NAME '
         'can be any part of a name of one of the parser classes in the '
         'quote_parsers module (case insensitive).')
@click.argument('format_name')
@click.argument('file_path')
@click.option('--verbose', '-v', is_flag=True)
def read_file(format_name, file_path, verbose):
    def clean_name(name):
        return name.lower().replace(' ', '')

    with open(file_path, 'rb') as matrix_file:
        init_config()
        init_model()
        s = Session()
        search_string = r'%' + format_name + r'%'
        q = s.query(MatrixFormat).filter(MatrixFormat.name.ilike(search_string))
        try:
            matrix_format = q.one()
        except NoResultFound:
            print "Matrix format not found. Known names are:"
            print '\n'.join(m.name for m in s.query(MatrixFormat)
                            .order_by(MatrixFormat.name).all())
            exit(1)
        print 'MatrixFormat:', matrix_format.name
        print 'Supplier:', matrix_format.supplier.name
        Session.remove()

        try:
            parser_class = CLASSES_FOR_FORMATS[matrix_format.matrix_format_id]
        except KeyError:
            print >> stderr, 'No parser class for matrix format:', matrix_format
            exit(1)
        print 'Parser class:', parser_class.__name__

        parser = parser_class()
        parser.load_file(matrix_file, os.path.basename(file_path), matrix_format)
        parser.validate()
        print 'Validated'

        for quote in parser.extract_quotes():
            if verbose:
                print quote
            quote.validate()
        print 'Got %s quotes' % parser.get_count()


if __name__ == '__main__':
    init_config()
    init_altitude_db()
    read_file()
