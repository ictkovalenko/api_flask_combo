# -*- coding: UTF-8 -*-
from time import time
import base64
import numpy
from http import HTTPStatus
from io import BytesIO
from datetime import timedelta
from flask import request, abort, json
from api.helpers import id_argument
from flaskapp import app
from models import MotionDevice, Session2, SensorRecord2, load_all_bindata, TimeSync
from query.sensordata.sensordata_query import fetch_sensor_data_bundle_for_sensor
from utils import parse_date_string, json_isoformat
from views.util import download_view, text_view


def json_b64(data):
    return base64.b64encode(data).decode('ASCII')


def record_to_json(r):
    return {'timestamp_tx': r.timestamp_tx,
            'timestamp_tx_end': r.timestamp_tx_end,
            'stream_cnt_begin': r.stream_cnt_begin,
            'stream_cnt_end': r.stream_cnt_end,
            'bindata': json_b64(r.bindata_cached.bin_data)
            }


def stream_to_json(s):
    return {'stream_type': s.stream_type,
            'data_format': s.data_format,
            'last_record_added_tx': s.last_record_added_tx,
            'open_record_tx': s.open_record_tx,
            'properties': s.properties,
            }


def session_to_json(s):
    return {'created': json_isoformat(s.created),
            'start_time': json_isoformat(s.start_time),
            'end_time': json_isoformat(s.end_time),
            'closed': s.closed,
            'deleted': s.deleted}


def sensor_device_to_json(s):
    return {'created': json_isoformat(s.created_date),
            'mac': s.mac,
            'mac_string': s.mac_string()}


def timesync_to_json(s):

    return {'timestamp_tx': s.timestamp_tx,
            'server_time': json_isoformat(s.server_time)}


# test with
@app.route('/internal/records/export_session/<tame:session_id>')
@download_view
def internal_records_export_session(session_id):

    session = Session2.query.get(session_id)

    if session is None:
        abort(HTTPStatus.NOT_ACCEPTABLE)

    session_json = session_to_json(session)
    session_json['streams'] = []

    json_timesyncs = [timesync_to_json(ts) for ts in TimeSync.query.filter(TimeSync.session_id == session.id)]
    session_json['timesyncs'] = json_timesyncs

    for stream in session.streams:
        records = SensorRecord2.query.filter(SensorRecord2.stream_id == stream.id).all()

        load_all_bindata(records)
        records_json = [record_to_json(r) for r in records]

        stream_json = stream_to_json(stream)
        stream_json['records'] = records_json
        session_json['streams'] += [stream_json]

    return json.dumps({'session': session_json, 'sensor_device': sensor_device_to_json(session.motion_device)}),\
           'application/json',\
           'exported_session_%d_%s_%s.json' % (session_id, session.motion_device.short_name(), session.start_time.isoformat())
