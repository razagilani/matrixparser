"""Code to set up the "Admin" UI for the billing database, using Flask-Admin.
This lets people view or edit anythihg in the database and has nothing to do
with Bill Entry, but it's part of Bill Entry because that is currently the
only application that uses Flask.
"""
from flask import url_for, redirect, request
from flask.ext import login
from flask.ext.admin import AdminIndexView, expose, Admin
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.principal import Permission, RoleNeed

from billentry.common import get_bcrypt_object
from brokerage.model import MatrixFormat
from brokerage.model import Supplier, Session, MatrixFormat

# Create a permission with a single Need, in this case a RoleNeed.
admin_permission = Permission(RoleNeed('admin'))
bcrypt = get_bcrypt_object()

class MyAdminIndexView(AdminIndexView):

    @expose('/')
    def index(self):
        from brokerage import config
        if config.get('billentry', 'disable_authentication'):
                return super(MyAdminIndexView, self).index()
        if login.current_user.is_authenticated():
            with admin_permission.require():
                return super(MyAdminIndexView, self).index()
        return redirect(url_for('login', next=request.url))


class LoginModelView(ModelView):
    def is_accessible(self):
        from brokerage import config
        if config.get('billentry', 'disable_authentication'):
            return True
        return login.current_user.is_authenticated()

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('login', next=request.url))

    def __init__(self, model, session, **kwargs):
        super(LoginModelView, self).__init__(model, session, **kwargs)


class SupplierModelView(LoginModelView):
    form_columns = (
        'name',
        'matrix_email_recipient',
    )
    def __init__(self, session, **kwargs):
        super(SupplierModelView, self).__init__(Supplier, session, **kwargs)


class MatrixFormatView(LoginModelView):
    column_list = ('matrix_format_id', 'supplier', 'name',
                    'matrix_attachment_name')

    def __init__(self, session, **kwargs):
        super(MatrixFormatView, self).__init__(MatrixFormat, session, **kwargs)


def make_admin(app):
    '''Return a new Flask 'Admin' object associated with 'app' representing
    the admin UI.
    '''
    # supposedly you can change the root URL to / as described here:
    # https://flask-admin.readthedocs.org/en/latest/api/mod_base/#default-view
    admin = Admin(app, index_view=MyAdminIndexView())
    admin.add_view(MatrixFormatView(Session))
    admin.add_view(SupplierModelView(Session))
    return admin
