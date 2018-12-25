import math
from datetime import timedelta
from components import db
from flaskapp import app
from math.algorithm.algorithms import Algorithms
from utils import unixts


class CacheDerivedData(db.Model):
    __tablename__ = 'cache_derived_data'
    __bind_key__ = 'structure'

    # Fields id should be enough to lookup
    id = db.Column(db.String(128), primary_key=True)

    # These fields are only for statistics and manual deletes
    start_time = db.Column(db.DateTime, nullable=False)
    server = db.Column(db.Integer, nullable=False, server_default='0')
    sensor_map = db.Column(db.String(128), nullable=False)
    measurement_id = db.Column(db.Integer, db.ForeignKey('measurement.id'), nullable=True)
    alg_profile_id = db.Column(db.Integer, db.ForeignKey('alg_profile.id'), nullable=False)
    parameter_hash = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    timeout = db.Column(db.DateTime, nullable=False)
    invalidated = db.Column(db.Boolean, nullable=False, server_default='0')

    data = db.Column(db.LargeBinary, nullable=False)

    @classmethod
    def sensor_window_factor(cls, sensor_device, start_hour):
        # Check if last received sensor_timestamp is withing +-30 minutes of the hour of interrest
        # and make a value called window_factor describing it for use with caching.
        start_padded = start_hour - timedelta(minutes=30)
        end_padded = start_hour + timedelta(minutes=90)
        if sensor_device.last_record_timestamp is None:
            return 0
        elif sensor_device.last_record_timestamp > end_padded:
            return 120*60
        elif sensor_device.last_record_timestamp < start_padded:
            return 0
        else:
            return math.floor((sensor_device.last_record_timestamp - start_padded).total_seconds())

        sensor_device.last_record_timestamp

    @classmethod
    def sensor_map_string(cls, sensor_map, alg_profile):
        assert(isinstance(sensor_map, dict))
        return ":".join(["%d" % sensor_map[d].id for d in alg_profile.alg().__place__ if d in sensor_map] )

    @classmethod
    def sensor_window_factor_string(cls, sensor_map, alg_profile, start_hour):
        assert(isinstance(sensor_map, dict))
        return ":".join(["%d" % cls.sensor_window_factor(sensor_map[d], start_hour) for d in alg_profile.alg().__place__ if d in sensor_map])

    @classmethod
    def make_cache_id(cls, sensor_map, alg_profile, start_hour):
        sensor_map_string = cls.sensor_map_string(sensor_map, alg_profile)
        key = "S." +\
              ("%d." % app.config['CACHE_SERVER_ID']) +\
              ("%07d." % (unixts(start_hour)/1000/3600)) +\
              ("%07d." % alg_profile.id) +\
              ("%s." % cls.sensor_window_factor_string(sensor_map, alg_profile, start_hour)) +\
              ("%s" % sensor_map_string)+\
              ("%s" % alg_profile.alghash())
        return key
