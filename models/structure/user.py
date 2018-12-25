import hashlib
import json
import random
from sqlalchemy.orm import relationship
from components import db
from flaskapp import app
from datetime import datetime
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)


class User(db.Model):
    __tablename__ = 'users'
    __bind_key__ = 'structure'

    # Fields
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(250), nullable=False, unique=True, index=True)
    password = db.Column(db.String(250), nullable=False, server_default='')
    password_time = db.Column(db.DateTime(), nullable=False)

    # User authentication information
    signup_token = db.Column(db.String(100), nullable=False, server_default='')
    reset_password_token = db.Column(db.String(100), nullable=False, server_default='')
    email_confirmed_at = db.Column(db.DateTime(), nullable=True)

    # Management information
    disabled = db.Column('disabled', db.Boolean(), nullable=False, server_default='0')
    activity_time = db.Column(db.DateTime)

    # Personal information
    first_name = db.Column(db.String(250), nullable=False, default='')
    last_name = db.Column(db.String(250), nullable=False, default='')
    timezone = db.Column(db.String(50), nullable=False, default='Europe/Copenhagen')

    # Relationships

    # Helper Methods
    @staticmethod
    def get_from_email(email):
        return User.query.filter(User.email == email).first()

    def on_login(self):
        self.activity_time = datetime.utcnow()
        db.session.commit()

    def generate_auth_token(self, expiration=3600*24*30):
        s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id})

    def is_unrestricted(self):
        if not hasattr(self, '_cached_is_unrestricted'):
            self._cached_is_unrestricted = (UserGroupUserAssociation.query.filter(UserGroupUserAssociation.user_id == self.id, UserGroupUserAssociation.user_group_id==UserGroup.UNRESTRICTED_ID).count() != 0)
        return self._cached_is_unrestricted

    SIGNATURE_OK = 0
    SIGNATURE_EXPIRED = 1
    SIGNATURE_INVALID = 2

    @staticmethod
    def get_from_token(token):
        if token == 'fake:api@gmail.com' and app.config['DEBUG'] is True:
            return User.get_from_email('api@gmail.com'), User.SIGNATURE_OK
        if token is None:
            return None, User.SIGNATURE_INVALID  # no token
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None, User.SIGNATURE_EXPIRED  # valid token, but expired
        except BadSignature:
            return None, User.SIGNATURE_INVALID  # invalid token
        user = User.query.get(data['id'])
        return user, User.SIGNATURE_OK

    def shadow_pwd(self, password):
        sha1 = hashlib.sha1()
        sha1.update((self.email + password).encode('ascii'))
        print(self.email, password, sha1.hexdigest())
        return sha1.hexdigest()


class UserGroupUserAssociation(db.Model):
    __tablename__ = 'open__user_in_usergroup'
    __bind_key__ = 'structure'

    user_group_id = db.Column(db.Integer, db.ForeignKey('user_groups2.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    level = db.Column(db.Integer)

    # Relationships
    user = relationship("User", backref="user_groups")
    group = relationship("UserGroup")


class UserGroup(db.Model):
    __tablename__ = 'user_groups2'
    __bind_key__ = 'structure'

    # Constants
    SITEADMIN_ID = 1
    UNRESTRICTED_ID = 2

    # Fields
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(250))
    create_time = db.Column(db.DateTime)
    users = relationship("UserGroupUserAssociation")
    parameters = db.Column(db.String(2048))
    disabled = db.Column('disabled', db.Boolean(), nullable=False, server_default='0')

    def has_user(self, user):
        for asso in self.users:
            if asso.user == user:
                return True
        return False

    def is_unrestricted(self):
        return self.id == UserGroup.UNRESTRICTED_ID

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
        return self.disabled is False


def create_user(email, pwd=None):
    """return (User, ClearPassword) or (None, ErrCode) in case of error"""

    email = email.lower()

    # check unique by name
    if User.get_from_email(email):
        return None, User.ERR_USER_EXISTS

    # pwd and sha1-hash
    if not pwd:
        pwd = generate_pwd(28)

    # create UserInfo
    u = User(email=email,
             password=shadow_pwd(email, pwd),
             password_time=datetime.utcnow(),
             activity_time=datetime.utcnow())
    db.session.add(u)
    db.session.commit()

    return u, pwd


def shadow_pwd(email, pwd):
    sha1 = hashlib.sha1()
    sha1.update((email + pwd).encode('utf_8'))
    return sha1.hexdigest()


def generate_pwd(length):
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join([random.choice(chars) for _ in range(length)])
