'''
Main file for Bill Entry (Flask web app for y UI).utility bill data entry).
This file contains the main 'Flask' object and code for things that affect the
application as a whole, such as authentication.

Here are some recommendations on how to structure a Python/Flask project.
http://as.ynchrono.us/2007/12/filesystem-structure-of-python-project_21.html
http://flask.pocoo.org/docs/0.10/patterns/packages/
http://flask-restful.readthedocs.org/en/0.3.1/intermediate-usage.html#project
-structure
'''
import json
import logging
import traceback
import urllib
import uuid
from datetime import datetime, timedelta
from urllib2 import Request, urlopen, URLError

import xkcdpass.xkcd_password  as xp
from flask import Flask, url_for, request, flash, session, redirect, \
    render_template, current_app
from flask.ext.kvsession import KVSessionExtension
from flask.ext.login import LoginManager, login_user, logout_user, current_user
from flask.ext.principal import identity_changed, Identity, AnonymousIdentity, \
    Principal, RoleNeed, identity_loaded, UserNeed, PermissionDenied
from flask_oauth import OAuth, OAuthException

from web import admin
from web.billentry_model import BillEntryUser, Role, BEUserSession
from web.common import get_bcrypt_object
from brokerage.model import Session
from brokerage import init_config

LOG_NAME = 'web'

app = Flask(__name__, static_url_path="")
bcrypt = get_bcrypt_object()


# Google OAuth URL parameters MUST be configurable because the
# 'consumer_key' and 'consumer_secret' are exclusive to a particular URL,
# meaning that different instances of the application need to have different
# values of these. Therefore, the 'config' object must be read and initialized
# at module scope (an import-time side effect, and also means that
# init_test_config can't be used to provide different values instead of these).
from brokerage import config

if config is None:
    # initialize 'config' only if it has not been initialized already (which
    # requires un-importing it and importing it again). this prevents
    # 'config' from getting re-initialized with non-test data if it was already
    # initialized with test data by calling 'init_test_config'.
    del config
    init_config()
    from brokerage import config

oauth = OAuth()
google = oauth.remote_app('google',
    base_url=config.get('web', 'base_url'),
    authorize_url=config.get('web', 'authorize_url'),
    request_token_url=config.get('web', 'request_token_url'),
    request_token_params={
        'scope': config.get('web', 'request_token_params_scope'),
        'response_type': config.get('web',
                                    'request_token_params_resp_type'),
        'hd': config.get('web', 'authorized_domain')},
    access_token_url=config.get('web', 'access_token_url'),
    access_token_method=config.get('web', 'access_token_method'),
    access_token_params={'grant_type': config.get('web',
                                                  'access_token_params_grant_type')},
    consumer_key=config.get('web', 'google_client_id'),
    consumer_secret=config.get('web', 'google_client_secret'))

app.secret_key = config.get('web', 'secret_key')
app.config['LOGIN_DISABLED'] = config.get('web', 'disable_authentication')

############
# KVSession
############
kvsession = KVSessionExtension(Session.bind, app)

login_manager = LoginManager()
login_manager.init_app(app)
principals = Principal(app)
app.permanent_session_lifetime = timedelta(
    seconds=config.get('web', 'timeout'))

if app.config['LOGIN_DISABLED']:
    login_manager.anonymous_user = BillEntryUser.get_anonymous_user

@principals.identity_loader
def load_identity_for_anonymous_user():
    if config.get('web', 'disable_authentication'):
        identity = AnonymousIdentity()
        identity.provides.add(RoleNeed('admin'))
        return identity


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Set the identity user object
    identity.user = current_user

    # Add the UserNeed to the identity
    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))

    # Assuming the User model has a list of roles, update the
    # identity with the roles that the user provides
    if hasattr(current_user, 'roles'):
        for role in current_user.roles:
            identity.provides.add(RoleNeed(role.name))


@login_manager.user_loader
def load_user(id):
    user = Session().query(BillEntryUser).filter_by(id=id).first()
    return user


@app.route('/logout')
def logout():
    current_user.authenticated = False
    logout_user()
    # Remove session keys set by Flask-Principal
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    # Tell Flask-Principal the user is anonymous
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())
    flash('You Logged out successfully')
    return redirect(url_for('login_page'))


@app.route('/oauth2callback')
@google.authorized_handler
def oauth2callback(resp):
    next_url = session.pop('next_url', url_for('index'))
    if resp is None:
        # this means that the user didn't allow the OAuth provider
        # the required access, or the redirect request from the OAuth
        # provider was invalid
        return redirect(url_for('login_page'))

    session['access_token'] = resp['access_token']
    # any user who logs in through OAuth gets automatically created
    # (with a random password) if there is no existing user with
    # the same email address.
    user_email = create_user_in_db(resp['access_token'])
    user = Session().query(BillEntryUser).filter_by(email=user_email).first()
    # start keeping track of user session
    start_user_session(user)
    return redirect(next_url)


@app.route('/')
def index():
    # not sure how to map admin to "/"
    return redirect('/admin')


def create_user_in_db(access_token):
    headers = {'Authorization': 'OAuth ' + access_token}
    req = Request(config.get('web', 'google_user_info_url'), None,
                  headers)
    try:
        # get info about currently logged in user
        res = urlopen(req)
    except URLError, e:
        if e.code == 401:
            # Unauthorized - bad token
            session.pop('access_token', None)
            return redirect(url_for('oauth_login'))
    # TODO: display googleEmail as Username in the bottom panel
    userInfoFromGoogle = res.read()
    userInfo = json.loads(userInfoFromGoogle)
    s = Session()
    session['email'] = userInfo['email']
    user = s.query(BillEntryUser).filter_by(email=userInfo['email']).first()
    # if user coming through google auth is not already present in local
    # database, then create it in the local db and assign the 'admin' role
    # to the user for proividing access to the Admin UI.
    # This assumes that internal users are authenticating using google auth.
    if user is None:
        # generate a random password
        wordfile = xp.locate_wordfile()
        mywords = xp.generate_wordlist(wordfile=wordfile, min_length=6,
                                       max_length=8)
        user = BillEntryUser(email=session['email'],
            password=get_hashed_password(
                xp.generate_xkcdpassword(mywords, acrostic="face")))
        # add user to the admin role
        admin_role = s.query(Role).filter_by(name='admin').first()
        user.roles = [admin_role]
        s.add(user)
        s.commit()
    user.authenticated = True
    s.commit()
    # Tell Flask-Principal the identity changed
    login_user(user)
    identity_changed.send(current_app._get_current_object(),
                          identity=Identity(user.id))
    return userInfo['email']


@app.before_request
def before_request():
    if app.config['LOGIN_DISABLED']:
        return

    user = current_user
    # this is for diaplaying the nextility logo on the
    # login_page when user is not logged in
    ALLOWED_ENDPOINTS = ['oauth_login', 'oauth2callback', 'logout',
        'login_page', 'locallogin',
        # special endpoint name for all static files--not a URL
        'static']

    if not user.is_authenticated():
        if request.endpoint in ALLOWED_ENDPOINTS:
            return
        set_next_url()
        return redirect(url_for('login_page'))


def set_next_url():
    next_path = request.args.get('next') or request.path
    if next_path:
        # Since passing along the "next" URL as a GET param requires
        # a different callback for each page, and Google requires
        # whitelisting each allowed callback page, therefore, it can't pass it
        # as a GET param. Instead, the url is sanitized and put into the
        # session.
        path = urllib.unquote(next_path)
        if path[0] == '/':
            # This first slash is unnecessary since we force it in when we
            # format next_url.
            path = path[1:]

        next_url = "{path}".format(path=path, )
        session['next_url'] = next_url


@app.after_request
def db_commit(response):
    # commit the transaction after every request that should change data.
    # this might work equally well in 'teardown_appcontext' as long as it comes
    # before Session.remove().
    if request.method in ('POST', 'PUT', 'DELETE'):
        # the Admin UI calls commit() by itself, so whenever a POST/PUT/DELETE
        # request is made to the Admin UI, commit() will be called twice, but
        # the second call will have no effect.
        Session.commit()
    return response


@app.teardown_appcontext
def shutdown_session(exception=None):
    """This is called after every request (after the "after_request" callback).
    The database session is closed here following the example here:
    http://flask.pocoo.org/docs/0.10/patterns/sqlalchemy/#declarative
    """
    # The Session.remove() method first calls Session.close() on the
    # current Session, which has the effect of releasing any
    # connection/transactional resources owned by the Session first,
    # then discarding the Session itself. Releasing here means that
    # connections are returned to their connection pool and any transactional
    # state is rolled back, ultimately using the rollback() method of
    # the underlying DBAPI connection.
    # TODO: this is necessary to make the tests pass but it's not good to
    # have testing-related stuff in the main code
    if app.config['TESTING'] is not True:
        Session.remove()


@app.route('/login')
def oauth_login():
    callback_url = url_for('oauth2callback', _external=True)
    result = google.authorize(callback=callback_url)
    return result


@app.route('/login-page')
def login_page():
    return render_template('login_page.html')


@app.errorhandler(PermissionDenied)
@app.errorhandler(OAuthException)
def page_not_found(e):
    return render_template('403.html'), 403


@app.errorhandler(Exception)
def internal_server_error(e):
    # Flask is not supposed to run error handler functions
    # if these are true, but it does (even if they are set
    # before the "errorhandler" decorator is called).
    if (app.config['TRAP_HTTP_EXCEPTIONS'] or app.config[
        'PROPAGATE_EXCEPTIONS']):
        raise
    error_message = log_error('Internal Server Error', traceback)

    return error_message, 500


def log_error(exception_name, traceback):
    from brokerage import config
    # Generate a unique error token that can be used to uniquely identify the
    # errors stacktrace in a logfile
    token = str(uuid.uuid4())
    logger = logging.getLogger(LOG_NAME)
    logger.exception('Exception in BillEntry (Token: %s): ', token)
    error_message = "Internal Server Error: %s, Error Token: " \
                    "<b>%s</b>" % (exception_name, token)
    if config.get('web', 'show_traceback_on_error'):
        error_message += "<br><br><pre>" + traceback.format_exc() + "</pre>"
    return error_message


@app.route('/userlogin', methods=['GET', 'POST'])
def locallogin():
    email = request.form['email']
    password = request.form['password']
    user = Session().query(BillEntryUser).filter_by(email=email).first()
    if user is None:
        flash('Username or Password is invalid', 'error')
        return redirect(url_for('login_page'))
    if not check_password(password, user.password):
        flash('Username or Password is invalid', 'error')
        return redirect(url_for('login_page'))
    user.authenticated = True
    if 'rememberme' in request.form:
        login_user(user, remember=True)
    else:
        login_user(user)
    # Tell Flask-Principal the identity changed
    identity_changed.send(current_app._get_current_object(),
                          identity=Identity(user.id))
    session['user_name'] = str(user)
    start_user_session(user)
    next_url = session.pop('next_url', url_for('index'))
    return redirect(next_url)

def get_hashed_password(plain_text_password):
    # Hash a password for the first time
    #   (Using bcrypt, the salt is saved into the hash itself)
    return bcrypt.generate_password_hash(plain_text_password)


def start_user_session(beuser):
    """ This method should be called after user has logged in
    to create a new BEUserSession object that keeps track of the
    duration of user's session in web
    """
    s = Session()
    be_user_session = BEUserSession(session_start=datetime.utcnow(),
                                    last_request=datetime.utcnow(),
                                    beuser=beuser)
    s.add(be_user_session)
    s.commit()


def check_password(plain_text_password, hashed_password):
    # Check hased password. Using bcrypt, the salt is saved into the hash itself
    return bcrypt.check_password_hash(hashed_password, plain_text_password)

# enable admin UI
admin.make_admin(app)

# apparently needed for Apache
application = app

