from components import db
from sqlalchemy import Table
from sqlalchemy.orm import relationship


class SensorAccess(db.Model):
    __tablename__ = "sensor_access"
    __bind_key__ = 'structure'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    remote_id = db.Column(db.Integer, nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=True, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    # A sensoraccess belongs to one, and only one, project.
    project = relationship('Project', backref='all_sensors')


asso_table_sensorpool_in_project = Table(
    'asso__sensorpool_in_project',
    db.Model.metadata,
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id')),
    db.Column('pool_id', db.Integer, db.ForeignKey('sensor_pools.id')),
    info={'bind_key': 'structure'}
)

asso_table_sensor_in_sensorpool = Table(
    'asso__sensor_in_sensorpool',
    db.Model.metadata,
    db.Column('sensor_id', db.Integer, db.ForeignKey('sensor_access.id')),
    db.Column('pool_id', db.Integer, db.ForeignKey('sensor_pools.id')),
    info={'bind_key': 'structure'}
)


class SensorPool(db.Model):
    __tablename__ = "sensor_pools"
    __bind_key__ = 'structure'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(1024), nullable=False)
    short_name = db.Column(db.String(128), nullable=False, unique=False, index=True)

    projects = relationship("Project", secondary=asso_table_sensorpool_in_project, backref='sensor_pools')
