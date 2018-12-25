from flask import json
from components import db


class CacheQueueEntry(db.Model):
    __tablename__ = 'cache_queue_entry'
    __bind_key__ = 'structure'

    id = db.Column(db.String(128), primary_key=True)
    priority = db.Column(db.Integer, nullable=False, server_default='0')

    start_time = db.Column(db.DateTime, nullable=False)
    server = db.Column(db.Integer, nullable=False, server_default='0')
    sensor_map = db.Column(db.String(128), nullable=False)
    measurement_id = db.Column(db.Integer, db.ForeignKey('measurement.id'), nullable=True)
    alg_profile_id = db.Column(db.Integer, db.ForeignKey('alg_profile.id'), nullable=False)
    parameters = db.Column(db.String(1024), nullable=False)
    scheduled = db.Column(db.DateTime, nullable=False)

    def parameters_json(self):
        if self.parameters == "":
            return {}
        else:
            return json.loads(self.parameters)
