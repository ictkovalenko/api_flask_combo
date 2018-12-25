from sqlalchemy import Table
from sqlalchemy.orm import relationship
from components import db

asso_table_org_project = Table(
    'asso__project_in_org',
    db.Model.metadata,
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id')),
    db.Column('org_id', db.Integer, db.ForeignKey('organizations.id')),
    info={'bind_key': 'structure'}
)


class Organization(db.Model):
    __tablename__ = "organizations"
    __bind_key__ = 'structure'

    # Fields
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(1024), nullable=False)
    short_name = db.Column(db.String(128), nullable=False, unique=True, index=True)
    member_group_id = db.Column(db.Integer, db.ForeignKey('user_groups2.id'), nullable=False)

    # Relationships
    projects = relationship("Project", secondary=asso_table_org_project, lazy='joined')
    member_group = relationship("UserGroup")


class Project(db.Model):
    __tablename__ = "projects"
    __bind_key__ = 'structure'

    # Fields
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(1024), nullable=False)
    short_name = db.Column(db.String(128), nullable=False, index=True)
    member_group_id = db.Column(db.Integer, db.ForeignKey('user_groups2.id'), nullable=False)
    created_time = db.Column(db.DateTime, nullable=False)
    active = db.Column('active', db.Boolean(), nullable=False, server_default='1')
    project_class = db.Column(db.String(1024), nullable=False, server_default='standard')

    # Backrefs
    # - sensor_pools (SensorPool.projects)
    # - all_sensors (SensorAccess.project)


    # Relationships
    orgs = relationship("Organization", secondary=asso_table_org_project)
    member_group = relationship("UserGroup")
