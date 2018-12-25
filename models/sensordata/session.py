from datetime import datetime
from sqlalchemy.orm import relationship
from components import db
import json


class Session2(db.Model):
    __tablename__ = "sessions2"
    __bind_key__ = 'sensordata'

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, nullable=False)
    start_time = db.Column(db.DateTime, nullable=True) # Null when never synced
    end_time = db.Column(db.DateTime, nullable=True)
    motion_device_id = db.Column(db.Integer(), db.ForeignKey('motion_devices.id'), nullable=False)
    closed = db.Column(db.Boolean(), default=False)
    deleted = db.Column(db.Boolean, default=False)

    # Relationships
    motion_device = relationship('MotionDevice', backref='sessions')

    # Helper
    def end_time_or_now(self):
        if self.end_time is None:
            return datetime.utcnow()
        else:
            return self.end_time


class Stream2(db.Model):
    __tablename__ = "streams2"
    __bind_key__ = 'sensordata'

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions2.id'), nullable=False, index=True)
    stream_type = db.Column(db.String(256), nullable=False)
    data_format = db.Column(db.Integer, nullable=False)
    last_record_added_tx = db.Column(db.BigInteger, nullable=True)
    open_record_tx = db.Column(db.BigInteger, nullable=True)
    properties = db.Column(db.String(2048), nullable=True)

    # Relationships
    session = relationship('Session2', backref='streams')

    MAP = {0: ['acc/3ax/4g',         '{"rate": "10/125"}'],
           1: ['volt/system/mv',     '{"rate": "60"}'],
           2: ['temp/acc/scalar',    '{"rate": "60"}'],
           3: ['cap/stretch/scalar', '{"rate": "10"}'],
           4: ['cap/prox/scalar',    '{"rate": "5"]}'],
           5: ['acc/3ax/4g',         '{"rate": "10/125"}'],
           6: ['acc/3ax/4g',         '{"rate": "1/100"}']}

    @staticmethod
    def legacy_stream_type(value):
        return Stream2.MAP[value][0]

    @staticmethod
    def legacy_properties(value):
        return Stream2.MAP[value][1]

    def get_rate(self):
        if self.properties is not None:
            rate = json.loads(self.properties)["rate"].split('/')
            if len(rate) == 1:
                return float(rate[0])
            else:
                return float(rate[0])/float(rate[1])

    FORMAT_SINGLE_UINT16 = 0
    FORMAT_LEGACY_3INT12 = 1
    FORMAT_COMPRESS_3INT12 = 2

    # back-compat
    # 0 = acc/3ax/4g
    # 1 = tmp/acc/scalar
    # 2 = volt/mcu/mv
    # 3 = cap/stretch/scalar
    # 4 = cap/proxA/scalar
    # 5 = tmp/mcu/scalar+volt/mcu/mv

