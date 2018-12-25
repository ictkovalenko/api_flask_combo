import flask
from datetime import timedelta
import crc16 as crc16
import struct
from flask_restful import Resource, reqparse
from sqlalchemy.orm import joinedload
from werkzeug.exceptions import BadRequest
from api.error_codes import ApiStatus
from api.helpers import api_resource, build_parameter_error_respose, build_response, bindata_argument
from components import db
from models import GatewaySensorActionRequest, MotionDevice, datetime, TimeSync, Session2, Stream2, add_records


@api_resource('/gwapi/1.0/gateway/submit/state')
class GatewaySensorSubmitState(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('device_id', type=str, required=True)
        parser.add_argument('action_id', type=int, required=True)
        parser.add_argument('sensor_state', type=int, required=True)
        parser.add_argument('sensor_pending_records', type=int, required=True)
        parser.add_argument('sensor_tx', type=int, required=True)
        parser.add_argument('version_string', type=str, required=True)
        return parser.parse_args()

    def post(self):
        """Submit SensorState"""

        now = datetime.utcnow()

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        # Find SensorAction
        action = GatewaySensorActionRequest.query.get(args['action_id'])
        if not action:
            return build_response({}, status_code=ApiStatus.STATUS_INVALID_PARAMETER)

        sensor = MotionDevice.query.get(action.sensor_id)

        sensor.sensor_state = args['sensor_state']
        sensor.firmware_version = args["version_string"]

        if action.action_type == GatewaySensorActionRequest.ACTION_SYNC and action.session_id is not None:
            timesync = TimeSync(session_id=action.session_id, timestamp_tx=args['sensor_tx'], server_time=now)
            db.session.add(timesync)

        db.session.commit()

        return build_response({})


@api_resource('/gwapi/1.0/gateway/submit/actionevent')
class GatewaySensorSubmitActionEvent(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('device_id', type=str, required=True)
        parser.add_argument('action_id', type=int, required=True)
        parser.add_argument('accepted', type=bool, required=False)
        parser.add_argument('connected', type=bool, required=False)
        parser.add_argument('interrupted', type=bool, required=False)
        parser.add_argument('completed', type=bool, required=False)
        parser.add_argument('msg', type=str, required=False)
        return parser.parse_args()

    def post(self):
        """Submit ActionState"""

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        # Find SensorAction
        action = GatewaySensorActionRequest.query.get(args['action_id'])
        if not action:
            return build_response({}, status_code=ApiStatus.STATUS_INVALID_PARAMETER)

        def value_or(v, v2):
            if v is None:
                return v2
            else:
                return v

        if args['accepted'] is True:
            action.status_accepted = value_or(action.status_accepted, 0) + 1
        if args['connected'] is True:
            action.status_connected = value_or(action.status_connected, 0) + 1
        if args['interrupted'] is True:
            action.status_interrupted = value_or(action.status_interrupted, 0) + 1
        if args['completed'] is True:
            action.status_completed = value_or(action.status_completed, 0) + 1
        if args['msg'] is not None:
            action.msg = value_or(action.msg, "") + ';' + args['msg']

        db.session.commit()

        return build_response({})


# ID (16)
# Payload Len (16)
# CRC (16)
# StreamID (8)
# StreamCount (8)
# Timestamp 100th (32)
RECORD_STRUCT = struct.Struct('< H H H B B L')


@api_resource('/gwapi/1.0/gateway/submit/records')
class GatewaySensorSubmitRecords(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('device_id', type=str, required=True)
        parser.add_argument('action_id', type=int, required=True)
        parser.add_argument('data', type=bindata_argument, required=True, action='append')
        return parser.parse_args()

    def post(self):
        """Submit SensorRecord"""

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        # This request uses some extra sql queries. #todo: fix this
        flask.g.stats_sql_count_max = 50

        print("Starting Submit")

        # Find SensorAction
        action = GatewaySensorActionRequest.query.get(args['action_id'])
        if not action:
            return build_response({}, status_code=ApiStatus.STATUS_INVALID_PARAMETER)

        if (action.action_type != GatewaySensorActionRequest.ACTION_SYNC and action.action_type != GatewaySensorActionRequest.ACTION_IGNORE_SYNC) or\
            action.session_id is None:
            print("Missing session_id in Action")
            return build_response({}, status_code=ApiStatus.STATUS_INVALID_PARAMETER)

        session = Session2.query.options(joinedload('motion_device')).get(action.session_id)
        session.motion_device.last_record_received = datetime.utcnow()

        # Stream Map
        streams = {s.stream_type: s for s in Stream2.query.filter(Stream2.session_id == session.id).all()}

        last_record_id = None

        # Empty array
        record_data = {}

        # Epoch
        timesync = TimeSync.query.filter(TimeSync.session_id==session.id).order_by(TimeSync.timestamp_tx.desc()).first()

        print("Submitting %d records" % len(args['data']))

        for d in args['data']:
            print("Record")
            # Calculate CRC, len is zero and crc is 0xFFFF
            dub = bytearray(d)
            dub[2] = 0x00
            dub[3] = 0x00
            dub[4] = 0xFF
            dub[5] = 0xFF
            calc_crc = crc16.crc16xmodem(bytes(dub), 0xFFFF)
            # CRC is only working on FW> 1.6.4, so ignore it for now

            meta = RECORD_STRUCT.unpack(d[:12])
            (record_id, payload_len, crc, stream_id, count, timestamp_tx) = meta
            data_len = payload_len - 8
            bin_data = bytearray(d[12:])
            last_record_id = record_id

            if action.synced_record_first is None:
                action.synced_record_first = record_id

            #print("STREAM TYPE", stream_id)

            # Find Stream based on id, backwards compat
            stream_type = Stream2.legacy_stream_type(stream_id)
            #print("STREAM", stream_type, stream_id)
            if stream_type is None:
                return build_response({}, status_code=ApiStatus.STATUS_INVALID_PARAMETER)

            # Find the stream object, if not create it
            if stream_type not in streams:
                data_format = Stream2.FORMAT_SINGLE_UINT16
                if stream_id == 0:
                    data_format = Stream2.FORMAT_LEGACY_3INT12
                elif stream_id == 5 or stream_id == 6:
                    data_format = Stream2.FORMAT_COMPRESS_3INT12
                stream = Stream2(session_id = session.id, stream_type = stream_type, data_format = data_format, properties = Stream2.legacy_properties(stream_id))
                db.session.add(stream)
                streams[stream_type] = stream

            if not stream_type in record_data:
                record_data[stream_type] = []

            # Save record under corresponding stream
            record_data[stream_type].append([timestamp_tx, count, bin_data])

            session.motion_device.last_record_timestamp = timesync.tx_to_utc(timestamp_tx)
            session.end_time = session.motion_device.last_record_timestamp
            if session.start_time is None or session.start_time > session.end_time:
                session.start_time = session.end_time

        db.session.commit()
        for s in record_data:
            add_records(session, streams[s], record_data[s], timesync)
        action.synced_record_last = last_record_id
        db.session.commit()

        return build_response(
            {'ack_record_id': last_record_id,
             'pending_data': session.motion_device.seconds_pending_data()
             })
