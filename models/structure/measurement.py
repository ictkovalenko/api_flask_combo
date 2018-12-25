from datetime import datetime
import hashlib
from sqlalchemy.orm import relationship, backref
from components import db
from math.algorithm.algorithms import Algorithms


class AlgProfile(db.Model):
    """Represents a specific algorith + parameters

    Fields:
        name

    """
    # todo: DB rename
    __tablename__ = 'alg_profile'
    __bind_key__ = 'structure'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(256), nullable=False)
    algorithm = db.Column(db.String(256), nullable=False)
    parameters = db.Column(db.String(1024*4), nullable=False)
    hash = db.Column(db.Integer, server_default='0', nullable=False)

    ALGORITHM_VALID = ['person/activity',
                       'person/stretch',
                       'person/activity2s',
                       'person/demos',
                       'acc/movement']

    def alg(self):
        alg = Algorithms.get(self.algorithm)
        assert(alg is not None), self.algorithm
        return alg

    def alghash(self):
        return hashlib.md5(self.alg().__vers__.encode()).hexdigest()


class Measurement(db.Model):
    """Represents a period of sensor data with attached meta data.

    Fields:
        id              DB id
        project         Project the measurement belongs to
        start_time      UTC time, start of period. Can be null of it is a CONFIG and not executed
        end_time        UTC time, end of period. Can be null if it is a CONFIG/OPEN
        profile         MeasurementProfile, metadata for measurement
        parameters      Custom parameters in JSON format. Algorithm specific.
        patient_profile Optional PatientProfile the measurement is linked to. Potentially overrides profile
        patient         Optional Patient the measurement is linked to. Potentially overrides profile/patient_profile
        state           Different states the Measurement can be in.

    External Dependents:
        sensors         MeasurementSensor

    """
    __tablename__ = 'measurement'
    __bind_key__ = 'structure'

    # Fields
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('alg_profile.id'), nullable=False)
    parameters = db.Column(db.String(4096), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=True, index=True)
    state = db.Column(db.Integer, nullable=False, server_default='0')
    #todo: DB update parent_id, remote patient_profile_id, parameters size

    # Relationships
    project = relationship('Project')
    patient = relationship('Patient', backref='measurements')
    profile = relationship('AlgProfile')

    # Backrefs
    # attached - MeasurementSensor

    STATE_CONFIG = 0
    STATE_OPEN = 1
    STATE_CLOSING = 2
    STATE_CLOSED = 3


    # Helpers
    def get_sensor_map(self):
        # todo: sql improve
        return {s.place: s.sensor.remote_details for s in self.attached}

    def end_time_or_now(self):
        return self.end_time if self.end_time else datetime.utcnow()


class MeasurementSensor(db.Model):
    """Represents a period of sensor data with attached meta data.

    Fields:
        id              Integer - database id
        measurement     Measurement - parent measurement
        sensor          SensorAccess - the sensor
        place           String - describing where the sensor is mounted
        parameters      String - custom parameters in JSON format. Algorithm specific

    """
    __tablename__ = 'measurement_sensor'
    __bind_key__ = 'structure'

    # Fields
    measurement_id = db.Column(db.Integer, db.ForeignKey('measurement.id'), nullable=False, primary_key=True, index=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey('sensor_access.id'), nullable=False, primary_key=True, index=True)
    place = db.Column(db.String(256), nullable=False)
    parameters = db.Column(db.String(1024), nullable=False)

    # Relationships
    measurement = relationship('Measurement', backref=backref('attached', lazy='joined'))
    sensor = relationship('SensorAccess', lazy='joined')

    PLACE_VALID = ['person/thigh', 'person/chest', 'person/lower_leg']
