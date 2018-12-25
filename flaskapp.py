import boto3
import flask
from flask import Flask
import logging
from flask_mail import Mail
from flask_restful import Api
from flask_redis import Redis
from slacker import Slacker
import os

import sys

assert sys.version_info[:2] == (3, 6) or sys.version_info[:2] == (3, 7), "Python 3.6 required, got %s" % str(sys.version_info)

SENS_CONFIG = os.getenv('SENS_CONFIG', False)

app = Flask('sens-backend')
api = Api(app)
mail = Mail(app)
app.config.update(
    MAIL_DEBUG=os.getenv('MAIL_DEBUG', True),
    MAIL_SERVER=os.getenv('MAIL_SERVER', 'localhost'),
    MAIL_PORT=os.getenv('MAIL_PORT', 25),
    MAIL_USE_SSL=os.getenv('MAIL_USE_SSL', False),
    MAIL_USE_TLS=os.getenv('MAIL_USE_TLS', False),
    MAIL_USERNAME=os.getenv('MAIL_USERNAME', ''),
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD', '')
)

mail = Mail(app)

# app.config.from_object('config.ProductionConfig')
if SENS_CONFIG == 'unittest':
    app.config.from_object('config.UnittestConfig')
elif SENS_CONFIG == 'production':
    app.config.from_object('config.ProductionConfig')
elif SENS_CONFIG == 'edge':
    app.config.from_object('config.EdgeConfig')
elif SENS_CONFIG == 'devel_local':
    app.config.from_object('config.DevLocalConfig')
else:
    assert False, "Please specify config"

# db = SQLAlchemy(app)

"""
Logging
"""

logger = logging.getLogger('sens.logapp')
logger.setLevel(logging.INFO)

slack = Slacker('{{ id }}')

#slack.chat.post_message('#aws-status',
#                        "Started app",
#                        attachments=None,
#                        username='AWS')

# Create an SNS client
client = boto3.client(
    "sns",
    aws_access_key_id=os.getenv('AWS_ACCES_KEY', ''),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY', ''),
    region_name=os.getenv('AWS_REGION', 'us-west-1')
)


@app.template_filter('autoversion')
def autoversion_filter(filename):
    fullpath = os.path.join('', filename[1:])
    try:
        timestamp = str(os.path.getmtime(fullpath))
    except OSError as e:
        return filename
    newfilename = "{0}?v={1}".format(filename, timestamp)
    return newfilename

"""
Test Routes
"""

import hooks
from api import api
from gwapi import gwapi
import views
