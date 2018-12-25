from components import db
import textwrap
from datetime import datetime, timedelta


class MotionDevice(db.Model):
    __tablename__ = "motion_devices"
    __bind_key__ = 'sensordata'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    mac = db.Column(db.BigInteger, nullable=False)
    expire_date = db.Column(db.DateTime)
    type = db.Column(db.Integer)
    cycle = db.Column(db.Integer)
    sensor_state = db.Column(db.Integer)
    firmware_version = db.Column(db.String(250))
    last_seen = db.Column(db.DateTime, nullable=False)
    #last_seen_by_id = db.Column(db.Integer, db.ForeignKey('gateway_devices.id'), nullable=True) # deprecated
    #last_seen_by = relationship("GatewayDevice", backref="observed_sensors")
    activated = db.Column(db.Integer, nullable=True, default=False)
    description = db.Column(db.String(2048), nullable=True)
    last_record_received = db.Column(db.DateTime, nullable=True)
    last_record_timestamp = db.Column(db.DateTime, nullable=True)
    terminated = db.Column(db.Integer, nullable=True)
    created_date = db.Column(db.DateTime, nullable=True)
    delivery = db.Column(db.Integer, nullable=True)
    #boost = db.Column(db.DateTime, nullable=True)

    def mac_string(self):
        return ":".join(textwrap.wrap("%012X" % self.mac, 2))

    def short_name(self):
        if self.created_date is None:
            return "00-%s" % self.mac_string()[12:].replace(':', '.')
        else:
            pre_num = (self.created_date.year - 2017)*12 + self.created_date.month
            return "%02d-%s" % (pre_num, self.mac_string()[12:].replace(':', '.'))

    def run_time(self):
        accumulated_time = timedelta(seconds=0)
        for s in self.sessions:
            if s.start_time is not None:
                if s.end_time is None:
                    accumulated_time += datetime.utcnow() - s.start_time
                else:
                    accumulated_time += s.end_time - s.start_time
        return accumulated_time


    DEEP_SLEEP = 0
    RUNNING = 1
    #ASSIGNED_AND_STOPPED = 2
    EXPIRED = 3
    PENDING_START = 4
    PENDING_STOP = 5

    SENSOR_STATE_RUNNING = 0
    SENSOR_STATE_STOPPED = 1
    SENSOR_STATE_UNKNOWN = -1
    SENSOR_STATE_NOT_SEEN = None

    SENSOR_STATE_TYPE = {SENSOR_STATE_RUNNING:     "Running",
                         SENSOR_STATE_STOPPED:     "DeepSleep",
                         SENSOR_STATE_UNKNOWN:     "Unknown",
                         SENSOR_STATE_NOT_SEEN:    "NotSeen"
                   }

    def is_activated(self):
        return self.activated

    def seconds_pending_data(self):
        if self.last_record_timestamp is None:
            return 3600*24
        else:
            return int((datetime.utcnow() - self.last_record_timestamp).total_seconds())

    def get_description(self):
        if self.description == None:
            return ""
        else:
            return self.desription[:12]

    def status(self):
        if self.expire_date and self.expire_date < datetime.utcnow():
            return MotionDevice.EXPIRED
        elif self.is_activated():
            if self.sensor_state == MotionDevice.SENSOR_STATE_RUNNING:
                return MotionDevice.RUNNING
            else:
                return MotionDevice.PENDING_START
        else:
            # We have NO runnning sessions
            if self.sensor_state == MotionDevice.SENSOR_STATE_RUNNING:
                return MotionDevice.PENDING_STOP
            else:
                return MotionDevice.DEEP_SLEEP

    @classmethod
    def mac_int(cls, string):
        s = string.replace('.','').replace(':','').replace('-','')
        return int(s, 16)

    sensor_type_map = {0: "N/A",
                       1: "PLUS-1.3.0",
                       2: "PLUS-2.0.0",
                       0x21: "PLUS-2.1.0",
                       0x22: "PLUS-2.2.0",
                       0x61: "Stretch-1.0"}

    def sensor_type_name(self):
        try:
            return MotionDevice.sensor_type_map[self.type]
        except:
            return "Unknown"
