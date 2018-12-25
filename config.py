import os

DB_PWORD = os.getenv('SENS_DB_PWORD', '')
ENV_DEPLOYMENT_ID = os.getenv('SENS_DEPLOYMENT_ID', 50)
ENV_APIDOC_ADDR = os.getenv('SENS_APIDOC_ADDR', 'http://localhost:5000')


class Config(object):
    """
    Configuration base, for all environments.
    """
    DEBUG = False
    TESTING = False
    BOOTSTRAP_FONTAWESOME = True
    SECRET_KEY = "{{ sec_key }}"
    CSRF_ENABLED = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    FORCE_SSL = False

    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 0

    CACHE_SERVER_ID = 0
    DEPLOYMENT_ID = ENV_DEPLOYMENT_ID

    DESCRIPTION = 'default'

    APIDOC_ADDR = ENV_APIDOC_ADDR


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_BINDS = {'sensordata': 'mysql+mysqldb://%s:%s@%s' % ('web', DB_PWORD, '{{  }}.eu-central-1.rds.amazonaws.com:3306/motiondb'),
                        'structure': 'mysql+mysqldb://%s:%s@%s' % ('web', DB_PWORD, '{{  }}.eu-central-1.rds.amazonaws.com:3306/structuredb')}
    DESCRIPTION = 'production'
    ALLOW_BOOTSTRAP = False
    ALLOW_MIGRATE = False
    SESSION_COOKIE_SECURE = True
    FORCE_SSL = True
    SENTRY_DNS = 'https://{{ : }}@sentry.io/{{ }}'


class EdgeConfig(Config):
    DEBUG = False
    SQLALCHEMY_BINDS = {'sensordata': 'mysql+mysqldb://%s:%s@%s' % (
    'web', DB_PWORD, '{{  }}.eu-central-1.rds.amazonaws.com:3306/motiondb'),
                        'structure': 'mysql+mysqldb://%s:%s@%s' % (
                        'web', DB_PWORD, '{{  }}.eu-central-1.rds.amazonaws.com:3306/structuredb')}
    DESCRIPTION = 'production'
    ALLOW_BOOTSTRAP = False
    ALLOW_MIGRATE = False
    SESSION_COOKIE_SECURE = True
    FORCE_SSL = True
    SENTRY_DNS = 'https://{{ : }}@sentry.io/{{ }}'


class DevProductionConfig(ProductionConfig):
    DEBUG = False
    DESCRIPTION = 'dev_production'
    ALLOW_BOOTSTRAP = False
    ALLOW_MIGRATE = True
    SESSION_COOKIE_SECURE = False
    FORCE_SSL = False
    SQLALCHEMY_ECHO = False
    CACHE_SERVER_ID = 5
    SENTRY_DNS = None
    DEPLOYMENT_ID = 1


class DevLocalConfig(Config):
    DEBUG = True
    SQLALCHEMY_BINDS = {'sensordata': 'sqlite:///sqlite/local_dev_sensordata.db',
                        'structure': 'sqlite:///sqlite/local_dev_structure.db'}
    DESCRIPTION = 'dev_local'
    ALLOW_BOOTSTRAP = True
    ALLOW_MIGRATE = False
    CACHE_SERVER_ID = 6
    SENTRY_DNS = None
    DEPLOYMENT_ID = 1


class DevEdgeLocalStructureConfig(Config):
    DEBUG = True
    SQLALCHEMY_BINDS = {'sensordata': 'mysql+mysqldb://%s:%s@%s' % ('web', DB_PWORD, '{{ }}.eu-central-1.rds.amazonaws.com:3306/motiondb'),
                        'structure': 'sqlite:///sqlite/local_structure.db'}
    DESCRIPTION = 'dev_edge_local_structure'
    ALLOW_BOOTSTRAP = False
    ALLOW_MIGRATE = True
    CACHE_SERVER_ID = 5
    SENTRY_DNS = None
    DEPLOYMENT_ID = 1


class DevProdLocalStructureConfig(Config):
    DEBUG = True
    SQLALCHEMY_BINDS = {'sensordata': 'mysql+mysqldb://%s:%s@%s' % (
    'web', DB_PWORD, '{{ }}.eu-central-1.rds.amazonaws.com:3306/motiondb'),
                        'structure': 'sqlite:///sqlite/local_structure.db'}
    DESCRIPTION = 'dev_edge_local_structure'
    ALLOW_BOOTSTRAP = False
    ALLOW_MIGRATE = True
    CACHE_SERVER_ID = 5
    SENTRY_DNS = None
    DEPLOYMENT_ID = 1


class UnittestConfig(Config):
    DEBUG = True
    SQLALCHEMY_BINDS = {'sensordata': 'mysql+mysqldb://%s:%s@%s' % (
    'web', DB_PWORD, '{{ }}.eu-central-1.rds.amazonaws.com:3306/motiondb'),
                        'structure': 'sqlite:///sqlite/local_structure.db'}
    DESCRIPTION = 'dev_edge_local_structure'
    ALLOW_BOOTSTRAP = False
    ALLOW_MIGRATE = True
    CACHE_SERVER_ID = 5
    SENTRY_DNS = None
    DEPLOYMENT_ID = 0

