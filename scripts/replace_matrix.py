#!/usr/bin/env python
"""Script to update matrix quote parsers and their tests with new example files.
"""
import inspect
import pkgutil
import re
import shutil
from importlib import import_module
from os.path import join, basename, splitext
from subprocess import check_call

import click
import desktop

from brokerage import quote_parsers
from test import test_quote_parsers
from test.test_quote_parsers import QuoteParserTest

QUOTE_FILES_DIR = 'test/quote_files/'

def get_parser_class_by_name(name):
    # TODO could also use module name
    for attr_name, attr in quote_parsers.__dict__.iteritems():
        if isinstance(attr, type) and attr.NAME == name:
            return attr
    raise KeyError("No parser named %s" % name)

def get_test_classes_for_parser_class(parser_class):
    test_classes = []
    for _, module_name, _ in pkgutil.iter_modules(test_quote_parsers.__path__):
        # simple getattr does not work here
        module = import_module('test.test_quote_parsers.' + module_name)
        for name, member in inspect.getmembers(module):
            if inspect.isclass(member) and issubclass(member, QuoteParserTest) \
                    and member.PARSER_CLASS is parser_class:
                test_classes.append(member)
    return test_classes

@click.command(help='Update test code for a new matrix format.')
@click.argument('parser-name')
@click.argument('example-file-paths', nargs=-1)
def main(parser_name, example_file_paths):
    # first find parser class using NAME, then find test classes whose PARSER_CLASS is that
    main_class = get_parser_class_by_name(parser_name)
    print 'Main class:', main_class.__name__
    test_classes = get_test_classes_for_parser_class(main_class)
    if test_classes == []:
        print "Couldn't find test class for main class %s" % main_class.__name__
        exit(1)
    print 'Test classes:', ', '.join(c.__name__ for c in test_classes)

    # there's no way to determine which test goes with which example file,
    # but it doesn't matter--any test should be able to go with any file

    for test_class, example_file_path in zip(test_classes, example_file_paths):
        # replace old example file with new one
        # (shell instead of hg library since we may not be using hg in the future)
        old_example_file_path = join(QUOTE_FILES_DIR, test_class.FILE_NAME)
        new_example_file_name = basename(example_file_path)
        new_example_file_path = join(QUOTE_FILES_DIR, new_example_file_name)
        shutil.copy(example_file_path, new_example_file_path)
        for command in ('hg add "%s"' % new_example_file_path,
                        'hg remove "%s"' % old_example_file_path):
            print command
            check_call(['/bin/bash', '--login', '-c', command])

    # TODO: ensure all tests are in the same file, otherwise this may not work
    test_module = import_module(test_class.__module__)
    test_file_path = test_module.__file__
    if test_file_path.endswith('.pyc'):
        test_file_path = splitext(test_file_path)[0] + '.py'
    print 'Test file:', test_file_path
    assert test_file_path.endswith('.py')

    # update test file. a class is chosen arbitrarily for each
    # example file since there's no way to tell which class goes
    # with which file
    # TODO: does not handle file names spread across more than one line
    with open(test_file_path, 'r') as test_file:
        test_lines = test_file.read().splitlines()
    j = 0
    for i, line in enumerate(test_lines):
        m = re.match('^(\s+)FILE_NAME = ', line)
        if m:
            test_lines[i] = "%sFILE_NAME = '%s'" % (
                m.group(1), basename(example_file_paths[j]))
            j += 1
    with open(test_file_path, 'w') as test_file:
        test_file.write('\n'.join(test_lines))
        test_file.write('\n')

    # open new example file in whatever program is used to view it
    for example_file_path in example_file_paths:
        desktop.open(example_file_path)

if __name__ == '__main__':
    main()
