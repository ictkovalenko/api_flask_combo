import flask
import json
from datetime import datetime
from flask import request
from sqlalchemy import event
from sqlalchemy.orm import deferred
from components import db, sentry
from flaskapp import app
from models.logging.apicall_log import ApiCallLog


@app.before_request
def set_defaults():
    flask.g.user = None


@event.listens_for(db.get_engine(bind='sensordata'), 'after_execute', named=True)
def receive_after_execute(**kw):
    "listen for the 'after_execute' event"
    #conn = kw['conn']
    #clauseelement = kw['clauseelement']
    if hasattr(flask.g, 'stats_sql_count'):
        flask.g.stats_sql_count += 1


@event.listens_for(db.get_engine(bind='structure'), 'after_execute', named=True)
def receive_after_execute(**kw):
    "listen for the 'after_execute' event"
    #conn = kw['conn']
    #clauseelement = kw['clauseelement']
    if hasattr(flask.g, 'stats_sql_count'):
        flask.g.stats_sql_count += 1


@app.before_request
def set_stats_defaults():
    flask.g.stats_start_time = datetime.utcnow()
    flask.g.stats_sql_count = 0
    flask.g.stats_sql_count_max = 10


@app.after_request
def check_request_sentry(response):
    # Sometimes before_request is not called
    if not hasattr(flask.g, 'stats_start_time'):
        return response

    if not request.path.startswith('/api') and not request.path.startswith('/gwapi') and not request.path.startswith('/exapi'):
        return response

    request_elapsed_s = (datetime.utcnow() - flask.g.stats_start_time).total_seconds()
    if sentry:
        sentry.extra_context({'sql_count': flask.g.stats_sql_count})
        sentry.extra_context({'request_time': request_elapsed_s})
        sentry.extra_context({'request_url': flask.request.url})
    if request_elapsed_s > 3.0:
        if sentry:
            sentry.captureMessage('Long Running Request %s' % flask.request.base_url)
    if flask.g.stats_sql_count > flask.g.stats_sql_count_max:
        if sentry:
            sentry.captureMessage('High SQL Count %s' % flask.request.base_url)

    ##############################
    # Api Call Logging

    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        ip = request.environ['REMOTE_ADDR']
    else:
        ip = request.environ['HTTP_X_FORWARDED_FOR']

    if request.method == 'POST':
        copy = request.get_json()
        if copy is None:
            request_json_string = ""
        else:
            for key in copy:
                value = copy[key]
                if hasattr(value, '__len__'):
                    length = len(json.dumps(copy[key]))
                else:
                    length = 0
                if key == 'password' or length > 128:
                    copy[key] = '(%d bytes)' % length
            request_json_string = json.dumps(copy)
        method = ApiCallLog.METHOD_POST
    elif request.method == 'GET':
        request_json_string = request.full_path[len(request.path)+1:]
        method = ApiCallLog.METHOD_GET
    elif request.method == 'HEAD':
        request_json_string = ""
        method = ApiCallLog.METHOD_HEAD
    else:
        request_json_string = ""
        method = -1

    response_json_string = response.data
    if len(response_json_string) > 1024:
        response_json_string = '(%d bytes' % len(response_json_string)

    call_log = ApiCallLog(deployment_id=app.config['DEPLOYMENT_ID'],
                          timestamp=flask.g.stats_start_time,
                          process_time_ms=request_elapsed_s * 1000,
                          sql_count=flask.g.stats_sql_count,
                          remote_ip=ip,
                          method=method,
                          response_code=int(response.status_code),
                          request_url=request.path,
                          request_args=request_json_string,
                          response_args=response_json_string,
                          resolved_user=flask.g.user.email if flask.g.user else None)
    db.session.add(call_log)
    db.session.commit()

    return response
