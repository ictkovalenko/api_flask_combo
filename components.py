from flask_caching import Cache
from flask_obscure import Obscure
from flask_sqlalchemy import SQLAlchemy
from flask_sslify import SSLify
from raven.contrib.flask import Sentry

from .flaskapp import app

db = SQLAlchemy(app)

obscure = Obscure()
obscure.init_app(app, app.id)

if app.config['FORCE_SSL'] is True:
    sslify = SSLify(app, skips=['/.well-known', '.well-known'])

internal_cache = Cache(app, config={'CACHE_TYPE': 'simple'})
ext_cache = internal_cache

if 'SENTRY_DNS' in app.config and app.config['SENTRY_DNS'] and app.config['SENTRY_DNS'] != '':
    sentry = Sentry(app, dsn=app.config['SENTRY_DNS'])
else:
    sentry = None

