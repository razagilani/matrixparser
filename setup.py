from setuptools import setup, find_packages

install_requires = [
    # "#" symbols after some package names below cause the package to be
    # installed from a URL in "dependency_links", not PyPI. apparently it's not
    # necessary to specify a version number or "egg" name after the "#".

    # boto 2.38 failed to upload files to S3 due to TCP reset. downgrading to
    # this version seemed to fix it.
    'boto==2.2.2',
    'billiard==3.3.0.20', # not sure what this is but may have to do with Flask/Bill Entry'
    'aniso8601', # not sure what this is but may have to do with Flask/Bill Entry'
    'SQLAlchemy==1.0.5',
    'click', # argument parsing for command-line scripts
    'ecdsa==0.11', # upgraded from 0.10 to match some other dependency that also uses it
    'formencode==1.3.0a1',
    'Flask==0.10.1',
    'Flask-RESTful==0.3.1',
    'flask-admin#',
    'Flask-Login==0.2.11',
    'Flask-Bcrypt==0.6.2',
    'Flask-OAuth==0.12',
    'Flask-Principal==0.4.0',
    'Flask-KVSession==0.6.2',
    'pdfminer==20140328',
    # pillow is a replacement for PIL, a dependency of reportlab that is not
    # maintained anymore. we used to install a copy of it that was available at
    # http://effbot.org/media/downloads/Imaging-1.1.7.tar.gz, but that can't be
    # compiled due to an issue described here:
    # https://stackoverflow.com/questions/20325473/error-installing-python-image-library-using-pip-on-mac-os-x-10-9
    'psycopg2==2.6',
    'py-bcrypt==0.4',
    'pyPdf==1.13',
    'pymssql#',
    'python-dateutil==2.2', # upgraded from 2.1 because "mq" uses this version
    'python-statsd',
    'pytz==2013.8',
    'regex==2015.7.19',
    'requests==0.14.0',
    'simplejson==2.6.0',
    # version number here must be greater than any version that actually
    # exists, in order to make pip choose it over the version from PyPI.
    # https://stackoverflow.com/questions/17366784/setuptools-unable-to-use-link-from-dependency-links
    'tablib<=123456',
    'tsort==0.0.1',
    'wsgiref==0.1.2',
    'xkcdpass==1.2.5',
    'xlwt==0.7.4',
    'testfixtures',
    'voluptuous==0.8.6',
    'Pint==0.6',

    'gunicorn==19.4.5',
]
tests_require=[
    # actually for tests
    'mock',
    'coverage',
    'pytest',
    'pytest-xdist',

    # general development tools
    'ipdb',
    'desktop',

    # for deployment
    'fabric',
    'awscli', # command-line tool from Amazon for working with AWS
]

setup(
    name="matrix",
    version="0",
    packages=find_packages(),
    scripts=[
        'bin/check_matrix_file.py',
        'bin/receive_matrix_email.py',
    ],
    # TODO: this can only be installed using
    # "pip install --process-dependency-links".
    # use of dependency_links seems to be deprecated or at least considered bad.
    dependency_links=[
        # Our forked repo of Flask-Admin
        'https://github.com/nextilityinc/flask-admin/archive/3ba9b936410d97839c99604dab25ba388e19cf1d.zip',

        'https://github.com/klothe/pymssql/archive/ba8c5f45f52ef3602a29604428dc831fab7f3af3.zip',

        # for Bitbucket repositories,
        # replace ":" with "/" Bitbucket SSH URL, append modulename-version.
        # modulename must match the one used in install_requires.
        'git+ssh://git@bitbucket.org/skylineitops/postal.git#egg=postal-0',
        # for zip files, URL format is like:
        # 'https://bitbucket.org/skylineitops/postal/get/6349bcb8e970.zip',
        # but this doesn't seem to work

        # see "tablib" above for explanation of fake version number
        'https://github.com/klothe/tablib/archive/ddf8cf8ecc75d3e13a44611324e63cfcb2a1b13a.zip#egg=tablib-123456',
    ],
    # install_requires includes test requirements. suggested by
    # https://stackoverflow.com/questions/4734292/specifying-where-to-install
    # -tests-require-dependencies-of-a-distribute-setupto
    install_requires=install_requires + tests_require,
    tests_require=tests_require,

    # TODO: what is this? remove or set to correct value
    test_suite="nose.collector",

    entry_points={
        'console_scripts': [
            # TODO: probably everything in bin/ goes here.
            # but how to include things that are not python module paths
            # starting from the root directory? bin is not and shouldn't be a
            # python package.
            # this only works if bin/__init__.py exists, making "bin" a module
            'check_matrix_file = bin.check_matrix_file:main',
            'receive_matrix_email = receive_matrix_email:main',
        ],
    }
)
