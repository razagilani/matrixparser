"""SQLAlchemy model classes used only by the web UI.
"""
from datetime import datetime

import bcrypt
from flask.ext.login import UserMixin
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Boolean
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship, backref

from brokerage.model import Base


class User(Base, UserMixin):
    """Table for users of the application.
    """
    # name comes from the Bill Entry application that this was derived from
    __tablename__ = 'billentry_user'

    _anonymous_user = None

    @classmethod
    def get_anonymous_user(cls):
        """Return the anonymous user, which should only be used when
        authentication is disabled.
        """
        from brokerage import config
        # the anonymous user should never be created when authentication is
        # turned on
        assert config.get('web', 'disable_authentication') == True
        if cls._anonymous_user is None:
            cls._anonymous_user = User(email='anonymous@example.com')
            cls._anonymous_user.is_anonymous = lambda: True
        return cls._anonymous_user

    id = Column(Integer, primary_key=True)
    password = Column(String(60), nullable=False)
    email = Column(String(50),unique=True, index=True, nullable=False)
    registered_on = Column('registered_on', DateTime, nullable=False)
    authenticated = Column(Boolean, default=False)

    # association proxy of "role_beuser" collection
    # to "role" attribute
    roles = association_proxy('billentry_role_user', 'billentry_role')

    def __init__(self, email='', password=''):
        self.email = email
        self.password = self.get_hashed_password(password)
        self.registered_on = datetime.utcnow()

    def get_hashed_password(self, plain_text_password):
        # Hash a password for the first time
        #   (Using bcrypt, the salt is saved into the hash itself)
        return bcrypt.hashpw(plain_text_password, bcrypt.gensalt(10))

    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return self.authenticated

    def is_active(self):
        """True, as all users are active."""
        return True

    def is_anonymous(self):
        """False, as anonymous users aren't supported."""
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User %s>' % self.email

    def get_beuser_billentry_duration(self, start, end):
        """ Method to calculate the duration of user session between start and end times
        """
        duration = 0.0
        start = datetime(start.year, start.month, start.day)
        end = datetime(end.year, end.month, end.day)
        for user_session in self.be_user_session:
            if user_session.session_start >= start and user_session.last_request <= end:
                duration += (user_session.last_request - user_session.session_start).total_seconds()
        return duration


class RoleUser(Base):
    '''Class corresponding to the "roles_user" table which represents the
    many-to-many relationship between "billentry_user" and "roles"'''
    # name comes from the Bill Entry application that this was derived from
    __tablename__ = 'billentry_role_user'

    billentry_user_id = Column(Integer, ForeignKey('billentry_user.id'),
                               primary_key=True)
    billentry_role_id = Column(Integer, ForeignKey('billentry_role.id'),
                               primary_key=True)

    # bidirectional attribute/collection of "billentry_user"/"role_beuser"
    beuser = relationship(User,
                          backref=backref('billentry_role_user'))

    # reference to the "Role" object
    billentry_role = relationship("Role")

    def __init__(self, role=None, user=None):

        # RoleBEUSer has only 'role' in its __init__ because the
        # relationship goes Role -> RoleUser -> BILLEntryUser. NOTE if the
        # 'role' argument is actually a User, Role's relationship to
        # RoleUser will cause a stack overflow in SQLAlchemy code
        # (without this check).

        assert isinstance(role, (Role, type(None)))

        self.billentry_role = role
        self.beuser = user


class Role(Base):
    # name comes from the Bill Entry application that this was derived from
    __tablename__ = 'billentry_role'

    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True)
    description = Column(String(100))

    def __init__(self, name='', description=''):
        self.name = name
        self.description = description

    def __repr__(self):
        return '<Role %s>' % self.name


class UserSession(Base):
    """ A class to keep track of the duration of a User's session
    """
    # name comes from the Bill Entry application that this was derived from
    __tablename__ = 'be_user_session'

    id = Column(Integer, primary_key=True)
    session_start = Column(DateTime, nullable=False)
    last_request = Column(DateTime)
    billentry_user_id = Column(Integer, ForeignKey('billentry_user.id'))

    beuser = relationship(User, backref=backref('be_user_session'))

    def __init__(self, session_start=datetime.utcnow(),
            last_request=datetime.utcnow(), beuser=None):
        self.session_start = session_start
        self.last_request = last_request
        self.beuser = beuser
