from components import db


"""
motion_device_user_group_table = db.Table('motion_device_user_group_table',
                                           db.Model.metadata,
                                           db.Column('user_group_id', db.Integer, db.ForeignKey('user_groups.id')),
                                           db.Column('motion_device_id', db.Integer, db.ForeignKey('motion_devices.id'))
                                           )
"""


class MotionDeviceUserGroup(db.Model):
    __tablename__ = "motion_device_user_group_table"
    __bind_key__ = 'sensordata'

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    user_group_id = db.Column(db.Integer, db.ForeignKey('user_groups.id'))
    motion_device_id = db.Column(db.Integer, db.ForeignKey('motion_devices.id'))
