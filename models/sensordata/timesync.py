from datetime import timedelta
from components import db


class SyncEvent(db.Model):
    __tablename__ = "sync_events"
    __bind_key__ = 'sensordata'

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions2.id'), nullable=False)
    motion_device_id = db.Column(db.Integer, db.ForeignKey('motion_devices.id'), nullable=False)
    status = db.Column(db.Integer, nullable=False)
    created = db.Column(db.DateTime, nullable=False)
    has_timesync = db.Column(db.Boolean, default=False) # Compat


class TimeSync(db.Model):
    __tablename__ = "sensor_time_syncs"
    __bind_key__ = 'sensordata'

    # Fields
    session_id = db.Column(db.Integer, db.ForeignKey('sessions2.id'), nullable=False, primary_key=True)
    timestamp_tx = db.Column(db.BigInteger, nullable=False, primary_key=True)
    server_time = db.Column(db.DateTime, nullable=False, index=True)

    def tx_to_utc(self, timestamp_tx):
        return self.server_time + timedelta(seconds=((timestamp_tx - self.timestamp_tx) * 0.01))
