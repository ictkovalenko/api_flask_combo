import random
from sqlalchemy.orm import relationship
from components import db


class ProjectAccessKey(db.Model):
    __tablename__ = "project_access_key"
    __bind_key__ = 'structure'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key_string = db.Column(db.String(128), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    # The project is allows access to
    project = relationship('Project')


class PatientAccessKey(db.Model):
    __tablename__ = "patient_access_key"
    __bind_key__ = 'structure'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key_string = db.Column(db.String(128), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)

    # A sensoraccess belongs to one, and only one, project.
    #  The patient it allows access to
    project = relationship('Project')
    patient = relationship('Patient')


def generate_ak():
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return ''.join([random.choice(chars) for _ in range(6)])
