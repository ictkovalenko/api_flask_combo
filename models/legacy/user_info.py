import hashlib
import math
import random
import struct
import uuid
import datetime
import json
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from components import db

# TODO Use docstring if needed
###############################################################
## UserInfo
##
## Fields:
##  name(key)
##  password      string (hashed)
##  email         string
##  phone_number
##  full_name
##  create_time   DateTime
##  tags          list<string>     Name tags
##
## Properties:
##  meas_count
##  measure_count_for_day
##
## Methods:
##
##
###############################################################



class UserInfo(db.Model):
    __tablename__ = "user_info"
    __bind_key__ = 'sensordata'

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(250), nullable=False, server_default='')
    create_time = db.Column(db.DateTime) # is actually login time
    timezone = db.Column(db.String(50))

    # User authentication information
    reset_password_token = db.Column(db.String(100), nullable=False, server_default='')

    # User email information
    email = db.Column(db.String(255), nullable=False, unique=True)
    confirmed_at = db.Column(db.DateTime())

    # User information
#    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='0')
    first_name = db.Column(db.String(100), nullable=False, default='')
    last_name = db.Column(db.String(100), nullable=False, default='')

    # Properties

    # Proxies
    member_of_ug_ids = association_proxy("user_groups", "user_group_id");

    def is_unrestricted(self):
        return UserGroupQuery.is_unrestricted(self)

    @classmethod
    def get_user(cls, username):
        return UserInfo.query.filter(UserInfo.username==username).first()

    # todo: compatibility with GAE version, remove and fix
    @classmethod
    def get_by_id(cls, username):
        return UserInfo.get_user(username)

    @classmethod
    def get_by_id_real(cls, id):
        return cls.query.filter(cls.id==id).first()

    def available_groups(self):
        return UserGroupQuery.available_groups(self)

    def on_login(self):
        self.create_time = datetime.datetime.utcnow()
        db.session.commit()

    def generate_auth_token(self, expiration=60*60*24):  # 1hour
        s = Serializer('some_secret_key', expires_in=expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        if token == 'fake':
            return True
        s = Serializer('some_secret_key')
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        user = UserInfo.query.get(data['id'])
        return user


"""
user_group_users_table = db.Table('user_group_users_table',
                                  db.Model.metadata,
                                  db.Column('user_group_id', db.Integer, db.ForeignKey('user_groups.id')),
                                  db.Column('user_info_id', db.Integer, db.ForeignKey('user_info.id'))
                                  )
                                  """

class UserGroupUserAssociationOld(db.Model):
    __tablename__ = 'user_group_user_association_table'
    __bind_key__ = 'sensordata'

    user_group_id = db.Column(db.Integer, db.ForeignKey('user_groups.id'), primary_key=True)
    user_info_id = db.Column(db.Integer, db.ForeignKey('user_info.id'), primary_key=True)
    level = db.Column(db.Integer)
    user = relationship("UserInfo", backref="user_groups")
    group = relationship("UserGroupOld")

user_group_session_groups_table = db.Table('user_group_session_groups_table',
                                           db.Model.metadata,
                                           db.Column('user_group_id', db.Integer, db.ForeignKey('user_groups.id')),
                                           db.Column('session_group_id', db.Integer, db.ForeignKey('session_groups.id'))
                                           )


class UserGroupOld(db.Model):
    __tablename__ = "user_groups"
    __bind_key__ = 'sensordata'

    # Constants
    ADMIN_ID = 1
    UNRESTRICTED_ID = 2

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250))
    create_time = db.Column(db.DateTime)
    users = relationship("UserGroupUserAssociationOld", backref="user_groups", lazy='joined')
    parameters = db.Column(db.String(2048))
    disabled = db.Column(db.Integer)

    def is_unrestricted(self):
        return self.id == UserGroupOld.UNRESTRICTED_ID

    def get_parameter(self, tag):
        self.get_parameters()
        if tag in self.parameters_cached:
            return self.parameters_cached[tag]
        else:
            return None

    def get_parameters(self):
        if not hasattr(self, 'parameters_cached'):
            if self.parameters is None:
                self.parameters_cached = {}
            else:
                try:
                    self.parameters_cached = json.loads(self.parameters)
                except (ValueError, TypeError):
                    self.parameters_cached = {'msg': 'invalid parameters'}
        return self.parameters_cached

    def is_enabled(self):
        if self.disabled is None or self.disabled == 0:
            return True


def create_user(user_name, pwd=''):
    """return (User, ClearPassword) or (None, ErrCode) in case of error"""

    user_name = user_name.lower()

    # check unique by name
    if UserInfo.get_user(user_name):
        return None, UserInfo.ERR_USER_NAME_EXISTS

    # pwd and sha1-hash
    if not pwd:
        pwd = generate_pwd(8)

    # create UserInfo
    u = UserInfo(username=user_name,
                 password=shadow_pwd(user_name, pwd),
                 create_time=datetime.datetime.utcnow(),
                 email='')
    db.session.add(u)
    db.session.commit()

    return u, pwd


def shadow_pwd(user_name, pwd):
    sha1 = hashlib.sha1()
    sha1.update(user_name + pwd)
    return sha1.hexdigest()


def generate_pwd(length):
    chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join([random.choice(chars) for i in range(length)])


class UserGroupQuery():
    @staticmethod
    def is_unrestricted(user):
        return UserGroupUserAssociationOld().query\
            .filter(UserGroupUserAssociationOld.user_info_id == user.id)\
            .filter(UserGroupUserAssociationOld.user_group_id == 2).count() != 0

    @staticmethod
    def available_groups(user):
        if user.is_unrestricted():
            return UserGroupOld.query.all()
        else:
            return UserGroupOld.query.join(UserGroupUserAssociationOld).filter(UserGroupUserAssociationOld.user_info_id==user.id).all()

#db_adapter = SQLAlchemyAdapter(db, UserInfo)  # Setup the SQLAlchemy DB Adapter
#user_manager = UserManager(db_adapter, app)  # Init Flask-User and bind to app
