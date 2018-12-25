from sqlalchemy.orm import deferred
from components import db


class ApiCallLog(db.Model):

    __tablename__ = 'log_apicall'
    __bind_key__ = 'structure'

    # Fields
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, index=True)
    deployment_id = db.Column(db.Integer, index=True)
    timestamp = db.Column(db.DateTime, nullable=True)
    process_time_ms = db.Column(db.Integer, nullable=False)
    sql_count = db.Column(db.Integer, nullable=False)
    remote_ip = db.Column(db.String(32), nullable=False)
    method = db.Column(db.Integer, nullable=False)
    response_code = db.Column(db.Integer, nullable=False)
    request_url = db.Column(db.String(1024), nullable=False)
    request_args = deferred(db.Column(db.String(1024*16), nullable=True), group='args')
    response_args = deferred(db.Column(db.String(1024*16), nullable=True), group='args')
    resolved_user = db.Column(db.String(128), nullable=True)

    METHOD_GET = 0
    METHOD_POST = 1
    METHOD_HEAD = 2
