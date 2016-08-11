"""
SQLALchemy classes that represent database tables.
"""
from datetime import datetime
from itertools import chain

import sqlalchemy
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, MetaData, \
    DateTime, Boolean, Numeric, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.base import class_mapper
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.orm.state import InstanceState
from sqlalchemy.types import Integer, String, Enum
from sqlalchemy.util.langhelpers import symbol

from brokerage.validation import MatrixQuoteValidator
from util.units import unit_registry

__all__ = ['Address', 'Base', 'AltitudeBase', 'MYSQLDB_DATETIME_MIN',
           'Session', 'AltitudeSession', 'altitude_metadata',
           'Supplier']

# Python's datetime.min is too early for the MySQLdb module; including it in a
# query to mean "the beginning of time" causes a strptime failure, so this
# value should be used instead.
MYSQLDB_DATETIME_MIN = datetime(1900, 1, 1)

Session = scoped_session(sessionmaker())
AltitudeSession = scoped_session(sessionmaker())
altitude_metadata = MetaData()

# allowed units for register quantities.
# UnitRegistry attributes are used in the values to ensure that there's an
# entry for every one of the allowed units (otherwise unit conversion would
# fail, as it has in past bugs.)
PHYSICAL_UNITS = {
    'BTU': unit_registry.BTU,
    'MMBTU': unit_registry.MMBTU,
    'kWD': unit_registry.kWD,
    'kWh': unit_registry.kWh,
    'therms': unit_registry.therms,
}

# this type should be used for database columns whose values can be the unit
# names above
physical_unit_type = Enum(*PHYSICAL_UNITS.keys(), name='physical_unit')


class _Base(object):
    """Common methods for all SQLAlchemy model classes, for use both here
    and in consumers that define their own model classes.
    """
    @classmethod
    def column_names(cls):
        """Return list of attributes names in the class that correspond to
        database columns. These are NOT necessarily the names of actual
        database columns.
        """
        return [prop.key for prop in class_mapper(cls).iterate_properties if
                isinstance(prop, sqlalchemy.orm.ColumnProperty)]

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return all([getattr(self, x) == getattr(other, x) for x in
                    self.column_names()])

    def __hash__(self):
        """Must be consistent with __eq__: if x == y, then hash(x) == hash(y)
        """
        # NOTE: do not assign non-hashable objects (such as lists) as
        # attributes!
        return hash((self.__class__.__name__,) + tuple(
            getattr(self, x) for x in self.column_names()))

    def _get_primary_key_names(self):
        """:return: set of names of primary key columns.
        """
        return {c.key for c in class_mapper(self.__class__).primary_key}

    def clone(self):
        """Return an object identical to this one except for primary keys and
        foreign keys.
        """
        # recommended way to clone a SQLAlchemy mapped object according to
        # Michael Bayer, the author:
        # https://www.mail-archive.com/sqlalchemy@googlegroups.com/msg10895.html
        # (this code does not completely follow those instructions)
        cls = self.__class__
        foreign_key_columns = chain.from_iterable(
            c.columns for c in self.__table__.constraints if
            isinstance(c, ForeignKeyConstraint))
        foreign_keys = set(col.key for col in foreign_key_columns)

        relevant_attr_names = [x for x in self.column_names() if
                               x not in self._get_primary_key_names() and
                               x not in foreign_keys]

        # NOTE it is necessary to use __new__ to avoid calling the
        # constructor here (because the constructor arguments are not known,
        # and are different for different classes).
        # MB says to create the object with __new__, but when i do that, i get
        # a "no attribute '_sa_instance_state'" AttributeError when assigning
        # the regular attributes below. creating an InstanceState like this
        # seems to fix the problem, but might not be right way.
        new_obj = cls.__new__(cls)
        class_manager = cls._sa_class_manager
        new_obj._sa_instance_state = InstanceState(new_obj, class_manager)

        # copy regular attributes from self to the new object
        for attr_name in relevant_attr_names:
            setattr(new_obj, attr_name, getattr(self, attr_name))
        return new_obj

    def raw_column_dict(self, exclude=set()):
        """
        :return: dictionary whose keys are column names in the database table
        and whose values are the corresponding column values, as in the
        dictionaries it passes to the DBAPI along with the SQL format strings.
        Primary key columns are excluded if their value is None.
        SQLAlchemy probably has an easy way to get this but I couldn't find it.
        """
        mapper = self._sa_instance_state.mapper
        return {column_property.columns[0].name: getattr(self, attr_name) for
                attr_name, column_property in mapper.column_attrs.items()
                if column_property.columns[0] not in mapper.primary_key and
                attr_name not in exclude}
                  
    def _copy_data_from(self, other):
        """Copy all column values from 'other' (except primary key),  replacing
        existing values.
        param other: object having same class as self.
        """
        assert other.__class__ == self.__class__
        # all attributes are either columns or relationships (note that some
        # relationship attributes, like charges, correspond to a foreign key
        # in a different table)
        for col_name in other.column_names():
            if col_name not in self._get_primary_key_names():
                setattr(self, col_name, getattr(other, col_name))
        for name, property in inspect(self.__class__).relationships.items():
            other_value = getattr(other, name)
            # for a relationship attribute where this object is the parent
            # (i.e. the other object's table contains the foreign key), copy the
            # child object (or its contents, if it's a list).
            # this only goes one level into the object graph but should be OK
            # for most uses.
            # i'm sure there's a much better way to do this buried in
            # SQLAlchemy somewhere but this appears to work.
            if property.direction == symbol('ONETOMANY'):
                if isinstance(other_value, Base):
                    other_value = other_value.clone()
                elif isinstance(other_value, InstrumentedList):
                    other_value = [element.clone() for element in other_value]
            else:
                assert property.direction == symbol('MANYTOONE')
            setattr(self, name, other_value)


Base = declarative_base(cls=_Base)
AltitudeBase = declarative_base(cls=_Base)


class Supplier(Base):
    """A company that supplies energy and is responsible for the supply
    charges on utility bills. This may be the same as the utility in the
    case of SOS.
    """
    __tablename__ = 'supplier'
    id = Column(Integer, primary_key=True)
    name = Column(String(1000), nullable=False, unique=True)

    # for importing matrix quotes from emailed files. file name is a regular
    # expression because file names can contain the current date or other
    # varying text.
    matrix_email_recipient = Column(String, unique=True)

    def __repr__(self):
        return '<Supplier(%s)>' % self.name

    def __str__(self):
        return self.name


class Company(AltitudeBase):
    __tablename__ = 'Supplier'
    company_id = Column('Supplier_ID', Integer, primary_key=True)
    name = Column('Supplier_Name', String, unique=True)


class RateClassAlias(AltitudeBase):
    __tablename__ = 'Rate_Class_Alias'
    rate_class_alias_id = Column('Rate_Class_Alias_ID', Integer,
                                 primary_key=True)
    rate_class_id = Column('Rate_Class_ID', Integer)
    rate_class_alias = Column('Rate_Class_Alias_Name', String, nullable=False)


def count_active_matrix_quotes():
    """Return the number of matrix quotes that are valid right now.
    """
    now = datetime.utcnow()
    s = AltitudeSession()
    return s.query(MatrixQuote).filter(MatrixQuote.valid_from <= now,
                                       MatrixQuote.valid_until < now).count()


class MatrixFormat(Base):
    """Represents the format of a matrix file. Related many-1 to
    suppliers (because each supplier may have many formats, even in the same
    email), and 1-1 to QuoteParser classes.

    Could also store any data specific to a file format that needs to be
    user-editable (such as regular expressions for extracting dates from file
    names, so file name changes can be handled without modifying code).
    """
    __tablename__ = 'matrix_format'

    matrix_format_id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey('supplier.id'), nullable=False)
    name = Column(String)

    # True if the matrix_attachment_name is supposed to match an email
    # subject, false if it matches an attachment name
    match_email_body = Column(Boolean, default=False)

    supplier = relationship(Supplier, backref='matrix_formats')

    # regular expression matching names of files that are expected to have
    # this format. should be unique, but may be null if all files from this
    # supplier have this format (for suppliers that send only one file).
    matrix_attachment_name = Column(String)


class Quote(AltitudeBase):
    """Fixed-price candidate supply contract.
    """
    __tablename__ = 'Rate_Matrix'

    rate_id = Column('Rate_Matrix_ID', Integer, primary_key=True)

    rate_class_alias = Column('rate_class_alias', String, nullable=False)
    rate_class_alias_id = Column('rate_class_alias_id', Integer, nullable=True)

    # inclusive start and exclusive end of the period during which the
    # customer can start receiving energy from this supplier
    start_from = Column('Earliest_Contract_Start_Date', DateTime,
                        nullable=False)
    start_until = Column('Latest_Contract_Start_Date', DateTime, nullable=False)

    # term length in number of utility billing periods
    term_months = Column('Contract_Term_Months', Integer, nullable=False)

    # when this quote was received
    date_received = Column('Created_Date', DateTime, nullable=False)

    # inclusive start and exclusive end of the period during which this quote
    # is valid
    valid_from = Column('Valid_From', DateTime, nullable=False)
    valid_until = Column('Valid_Until', DateTime, nullable=False)

    # whether this quote involves "POR" (supplier is offering a discount
    # because credit risk is transferred to the utility)
    purchase_of_receivables = Column('Purchase_Of_Receivables', Boolean,
                                     nullable=False, server_default='0')

    # fixed price for energy in dollars/energy unit
    price = Column('Matrix_Price_Dollars_KWH_Therm',
                   Numeric(precision=10, scale=7), nullable=False)

    # dual billing
    dual_billing = Column('Dual_Billing', Boolean, nullable=False,
                          server_default='1')

    # Percent Swing Allowable
    percent_swing = Column('Percent_Swing_Allowable', Float)

    # should be "electric" or "gas"--unfortunately SQL Server has no enum type
    service_type = None #Column(String, nullable=False)

    # Note: "1" is the system user.
    created_by = Column('Created_By', Integer, nullable=False,
                        server_default="1")

    discriminator = Column('Discriminator', String(50), nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'quote',
        'polymorphic_on': discriminator,
    }

    def __init__(self, service_type=None, **kwargs):
        super(Quote, self).__init__(**kwargs)
        if self.date_received is None:
            self.date_received = datetime.utcnow()
        self.service_type = service_type
        self.created_by = 1

        # pick a MatrixQuoteValidator class based on service type (mandatory)
        assert self.service_type is not None
        assert isinstance(self.term_months, int)
        self._validator = MatrixQuoteValidator.get_instance(self.service_type)

    def validate(self):
        """Sanity check to catch any obviously-wrong values. Raise
        ValidationError if there are any.
        """
        self._validator.validate(self)


class MatrixQuote(Quote):
    """Fixed-price candidate supply contract that applies to any customer with
    a particular utility, rate class, and annual total energy usage, taken
    from a daily "matrix" spreadsheet.
    """
    __mapper_args__ = {
        'polymorphic_identity': 'matrixquote',
    }

    # lower and upper limits on annual total energy consumption for customers
    # that this quote applies to. nullable because there might be no
    # restrictions on energy usage.
    # (min_volume <= customer's energy consumption < limit_volume)
    min_volume = Column('Minimum_Annual_Volume_KWH_Therm', Float)
    limit_volume = Column('Maximum_Annual_Volume_KWH_Therm', Float)

    # optional string to identify which file and part of the file (eg
    # spreadsheet row and column, or PDF page and coordinates) this quote came
    # from, for troubleshooting
    # NOTE - Removed in new schema.

    def __init__(self, file_reference=None, *args,  **kwargs):
        super(MatrixQuote, self).__init__(*args, **kwargs)
        self.file_reference = file_reference

    def __str__(self):
        return '\n'.join(['Matrix quote'] +
                         ['%s: %s' % (name, getattr(self, name)) for name in
                          self.column_names()] + [''])
