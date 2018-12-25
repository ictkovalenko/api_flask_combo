from sqlalchemy.orm import relationship
from components import db


class ROI(db.Model):
    __tablename__ = "roi"
    __bind_key__ = 'sensordata'

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    method = db.Column(db.String(1024), nullable=False)
    monitored_user_id = db.Column(db.Integer, db.ForeignKey('monitored_users.id'), nullable=False, index=True)
    hash = db.Column(db.Integer, nullable=True)

    # Relationships
    monitored_user = relationship('MonitoredUser', backref='roi')

    METHOD_VALID = ['person/activity',
                    'person/stretch',
                    'person/activity2s',
                    'person/demos']

    legacy = False

    def is_active(self):
        return self.start_time is not None and self.end_time is None


class ROISensor(db.Model):
    __tablename__ = "roi_sensor"
    __bind_key__ = 'sensordata'

    # Fields
    roi_id = db.Column(db.Integer, db.ForeignKey('roi.id'), nullable=False, primary_key=True)
    motion_device_id = db.Column(db.Integer, db.ForeignKey('motion_devices.id'), nullable=False, primary_key=True)
    place = db.Column(db.String(256), nullable=False)

    def duplicate(self):
        return ROISensor(motion_device_id = self.motion_device_id, place = self.place)

    # Relationships
    roi = relationship('ROI', backref='sensors')
    motion_device = relationship('MotionDevice')

    PLACE_VALID = ['person/thigh', 'person/chest', 'person/lower_leg']
