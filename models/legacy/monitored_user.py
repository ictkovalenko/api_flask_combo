from sqlalchemy.orm import relationship
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from components import db


class MonitoredUser(db.Model):
    __tablename__ = "monitored_users"
    __bind_key__ = 'sensordata'

    STATUS_NOT_MONITORING = 0
    STATUS_MONITORING = 1

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), default="", nullable=False)
    external_key = db.Column(db.BigInteger)
    verify_key = db.Column(db.Integer)
    #assigned_sensors = relationship("MotionDevice")
    birthday = db.Column(db.Date)
    birthday_precision = db.Column(db.Integer, default=0)
    mobility = db.Column(db.Integer, default=0)
    height = db.Column(db.Integer)
    weight = db.Column(db.Integer)
    timezone = db.Column(db.String(50))

    in_groups = relationship("MonitoredUserGroup", secondary=lambda: monitored_user_group_monitored_user_table)

    @staticmethod
    def validate_field_values(**kwargs):
        # TODO: Expand this function to efficiently check all fields
        # For now we just check those which can be changed from the patient view
        try:
            for field, val in kwargs.iteritems():
                if field == 'name':
                    sname = str(val)
                    assert len(sname) <= 250
                elif field == 'mobility':
                    mobility = int(val)
                    assert mobility >= 0
                elif field == 'age':
                    age = int(val)
                    assert age >= 0
                elif field == 'weight':
                    weight = int(val)
                    assert weight >= 0
                elif field == 'timezone':
                    stz = str(val)
                    assert len(stz) <= 50
                else:
                    raise Exception('invalid property')
        except:
            return False
        return True

    @property
    def algorithm_meta(self):
        class Meta:
            pass
        meta = Meta()
        meta.mobility = self.mobility
        return meta

    def age(self, now=None):
        if self.birthday is None:
            return None
        if now is None:
            now = date.today()
        return relativedelta(now, self.birthday).years

    def get_app_key(self):
        return '%i' % self.external_key if self.external_key is not None else None


class MonitoredUserGroup(db.Model):
    __tablename__ = "monitored_user_groups"
    __bind_key__ = 'sensordata'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(250), default="", nullable=False)

    monitored_users = relationship("MonitoredUser", secondary=lambda: monitored_user_group_monitored_user_table)


class MonitoringMethod(db.Model):
    __tablename__ = "monitoring_method"
    __bind_key__ = 'sensordata'

    METHOD_ACTIVITY = 0
    METHOD_STRETCH = 1

    id = db.Column(db.Integer, primary_key=True)
    mon_user_id = db.Column(db.Integer, db.ForeignKey('monitored_users.id'))
    method = db.Column(db.Integer)
    mon_user = relationship("MonitoredUser", backref="monitoring")

    @property
    def descr(self):
        if self.method == self.METHOD_ACTIVITY:
            return "Activity"
        elif self.method == self.METHOD_STRETCH:
            return "Stretch"


# Only define table because there are no association
monitored_user_group_monitored_user_table = db.Table('monitored_user_group_monitored_user_associations',
                                                     db.Model.metadata,
                                                     db.Column('monitored_user_group_id', db.Integer, db.ForeignKey('monitored_user_groups.id')),
                                                     db.Column('monitored_user_id', db.Integer, db.ForeignKey('monitored_users.id')),
                                                     info={'bind_key': 'sensordata'}
                                                     )
