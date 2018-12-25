from sqlalchemy.orm import relationship
from components import db


class GatewayDevice(db.Model):
    __tablename__ = "gateway_devices"
    __bind_key__ = 'sensordata'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    local_id = db.Column(db.String(1024), nullable=False, index=True)
    name = db.Column(db.String(1024), nullable=False)
    version = db.Column(db.String(1024), nullable=True)
    build = db.Column(db.String(256), nullable=True)
    apns = db.Column(db.String(1024), nullable=True)
    last_online = db.Column(db.DateTime, nullable=False)
    state_info = db.Column(db.String(4048), nullable=True)
    parameters = db.Column(db.String(4048), nullable=True)
    platform = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.String(1024), nullable=True)
    last_report_id = db.Column(db.Integer, db.ForeignKey('gateway_scan_reports.id'), nullable=True)

    PLATFORM = {0: "iOS", 1: "Android", 2: "Test", None: "Unknown"}

    last_report = relationship('GatewayScanReport', lazy='joined', foreign_keys=[last_report_id])


class GatewayScanReport(db.Model):
    __tablename__ = "gateway_scan_reports"
    __bind_key__ = 'sensordata'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gateway_device_id = db.Column(db.Integer, db.ForeignKey('gateway_devices.id'))
    gateway_device = relationship('GatewayDevice', foreign_keys=[gateway_device_id])
    triggertype = db.Column(db.Integer, nullable=False) # 0 = startup, 1 = high performance period, 2 = low power period
    gateway_state = db.Column(db.Integer, nullable=False) # Index 0 = powered; Index 1 = foreground
    timestamp = db.Column(db.DateTime, nullable=False)
    meta = db.Column(db.String(2048), nullable=True)

    # Backrefs
    # seen - GatewaySensorDiscovered

    # Field values
    GATEWAY_STATE_FLAGS = {0: ["Not Powered", "Powered"],
                           1: ["Background", "Foreground"],
                           2: ["Normal", "Dedicated"],
                           3: ["BLE Off", "BLE On"],
                           4: ["Scan OK", "Scan Error"],
                           5: ["Idle", "Busy"],
                           6: ["Perm OK", "Perm Missing"]}

    TRIGGER = {0: "Unknown",
               1: "Startup",
               2: "Alarm",
               3: "Alarm2",
               4: "Powered",
               5: "BLE On",
               6: "Boot",
               7: "Manual",
               8: "Auto Enabled",
               9: "Foreground",
               None: "Other"}


class GatewaySensorDiscovered(db.Model):
    __tablename__ = "gateway_seen_device"  # rename
    __bind_key__ = 'sensordata'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    scan_report_id = db.Column(db.Integer, db.ForeignKey('gateway_scan_reports.id'), nullable=False)
    sensor_id = db.Column('motion_device_id', db.Integer, db.ForeignKey('motion_devices.id'), nullable=False)
    sensor_state = db.Column('motion_device_state', db.Integer)
    sensor_rssi = db.Column('motion_device_rssi', db.Integer)
    action_request_id = db.Column(db.Integer, db.ForeignKey('gateway_sensor_action_request.id'), nullable=True)
    connected_state = db.Column(db.Integer, default=0)

    # Field values
    SENSOR_STATE = {0: "Running",
                    1: "Stopped"}

    # Relationships
    scan_report = relationship('GatewayScanReport', backref='seen')
    action_request = relationship('GatewaySensorActionRequest', backref='discover')
    sensor = relationship('MotionDevice', lazy='joined')


class GatewaySensorActionRequest(db.Model):
    __tablename__ = "gateway_sensor_action_request"
    __bind_key__ = 'sensordata'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey('motion_devices.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    action_type = db.Column(db.Integer, nullable=False)
    status_accepted = db.Column(db.Integer, nullable=False, server_default='0')
    status_connected = db.Column(db.Integer, nullable=False, server_default='0')
    status_completed = db.Column(db.Integer, nullable=False, server_default='0')
    status_interrupted = db.Column(db.Integer, nullable=False, server_default='0')
    state_pending_records = db.Column(db.Integer, nullable=True)
    state_tx = db.Column(db.BigInteger, nullable=True)
    synced_record_first = db.Column(db.Integer, nullable=True)
    synced_record_last = db.Column(db.Integer, nullable=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions2.id'), nullable=True)
    msg = db.Column(db.String(1024), nullable=True)

    ACTION_NONE = 0
    ACTION_ACTIVATE = 1
    ACTION_DEACTIVATE = 2
    ACTION_INTERROGATE = 3
    ACTION_SYNC = 4
    ACTION_IGNORE_SYNC = 5
    ACTION_IGNORE = 6

    # Field values
    ACTION_TYPE = {ACTION_NONE:        "None",
                   ACTION_ACTIVATE:    "Activate",
                   ACTION_DEACTIVATE:  "Deactivate",
                   ACTION_INTERROGATE: "Interrogate",
                   ACTION_SYNC:        "Sync"
                   }

    STATUS_UNKNOWN = 0

    STATUS = {0: "Unknown",
              1: "Ignored",
              2: "Success",
              3: "Partial",
              4: "Failed"
              }
