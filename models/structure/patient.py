from sqlalchemy import Table
from sqlalchemy.orm import relationship
from components import db


class PatientProfile(db.Model):
    __tablename__ = "patient_profiles"
    __bind_key__ = 'structure'

    # Fields
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True, index=True)
    short_name = db.Column(db.String(128), nullable=False, unique=True)
    parent = db.Column(db.String(128), nullable=True)
    description = db.Column(db.String(1024), nullable=False, server_default='')
    meta = db.Column(db.String(1024*10), nullable=False, server_default='')


def add_patient_profile(p):
    if PatientProfile.query.filter(PatientProfile.short_name == p.short_name).first() is None:
        db.session.add(p)
        db.session.commit()


def create_patient_profiles():
    add_patient_profile(PatientProfile(short_name='person/default', meta=''))
    add_patient_profile(PatientProfile(short_name='person/mobility/full', meta='{"mobility": "a+"}'))
    add_patient_profile(PatientProfile(short_name='person/mobility/a', meta='{"mobility": "a"}'))
    add_patient_profile(PatientProfile(short_name='person/mobility/b', meta='{"mobility": "b"}'))
    add_patient_profile(PatientProfile(short_name='person/mobility/c', meta='{"mobility": "c"}'))
    add_patient_profile(PatientProfile(short_name='patient/hospital/h1', meta='{"hospital_mobility": "h1"}'))
    add_patient_profile(PatientProfile(short_name='patient/hospital/h2', meta='{"hospital_mobility": "h2"}'))
    add_patient_profile(PatientProfile(short_name='patient/hospital/h3', meta='{"hospital_mobility": "h3"}'))


class Patient(db.Model):
    __tablename__ = "patients"
    __bind_key__ = 'structure'

    # Fields
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True, index=True)
    short_name = db.Column(db.String(128), nullable=False, unique=False, index=True)
    classtype = db.Column(db.String(128), nullable=False, server_default='patient/anonymous')
    description = db.Column(db.String(1024), nullable=False, server_default='')
    meta = db.Column(db.String(1024*10), nullable=False, server_default='')
    timezone = db.Column(db.String(256), nullable=False, server_default='Europe/Copenhagen')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    deleted = db.Column(db.Integer, nullable=False, server_default='0')
    profile_id = db.Column(db.Integer, db.ForeignKey('patient_profiles.id'), nullable=True)

    # A patient belongs to one, and only one, project.
    project = relationship('Project', backref='all_patients')
    profile = relationship('PatientProfile')

    CLASSTYPE_VALID = ['patient/anonymous', 'patient/hospital1']
