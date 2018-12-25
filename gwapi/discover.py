import flask
from datetime import datetime
from flask_restful import Resource, reqparse
from werkzeug.exceptions import BadRequest
from api.error_codes import ApiStatus
from api.helpers import api_resource, build_parameter_error_respose, build_response
from components import db
from models import MotionDevice, Session2, SyncEvent, GatewayDevice, GatewayScanReport, \
    GatewaySensorActionRequest, GatewaySensorDiscovered


class ApiSensorCommand:
    UNKNOW = 0
    START = 1
    STOP = 2
    INTERROGATE = 3
    SYNC = 4
    IGNORESYNC = 5
    IGNORE = 6


def get_sensor_action(sensor_mac, sensor_state, sensor_type, g):

    # Lookup Sensor
    mac_int = MotionDevice.mac_int(sensor_mac)
    d = MotionDevice.query.filter(MotionDevice.mac == mac_int).filter((MotionDevice.terminated == 0) | (MotionDevice.terminated == None)).first()
    if not d:
        d = MotionDevice(mac=mac_int, type=sensor_type, sensor_state=sensor_state, activated=False)
        db.session.add(d)
        db.session.commit()
    else:
        if d.sensor_state != sensor_state and (sensor_state == 1 or sensor_state == 0) : d.sensor_state = sensor_state
        if d.type != sensor_type: d.type = sensor_type
    d.last_seen = datetime.utcnow()

    session_id = None
    # Check if state should be updated
    if (d.status() == MotionDevice.PENDING_START and d.sensor_state == MotionDevice.SENSOR_STATE_STOPPED):
        session = Session2.query.filter(Session2.motion_device_id == d.id).filter(Session2.closed == False).first()
        if (session != None and session.end_time != None and (datetime.utcnow() - session.created).total_seconds() > 60):
            session.closed = True
            session = None
        if (session == None):
            session2 = Session2(created=datetime.utcnow(), start_time=datetime.utcnow(), motion_device_id = d.id)
            db.session.add(session2)
            db.session.commit()
        command = ApiSensorCommand.START  # START
    elif (d.status() == MotionDevice.PENDING_STOP and d.sensor_state == MotionDevice.SENSOR_STATE_RUNNING):
        session = Session2.query.filter(Session2.motion_device_id == d.id).filter(Session2.closed == False).first()
        if (session != None and session.end_time != None and (datetime.utcnow() - session.end_time).total_seconds() > 60*5):
            # Dont stop yet, sync rest of data
            command = ApiSensorCommand.SYNC  # SYNC
            session_id = session.id
        else:
            command = ApiSensorCommand.STOP
            if session != None:
                session.closed = True
                db.session.commit()
    elif d.status() == MotionDevice.RUNNING and d.sensor_state == MotionDevice.SENSOR_STATE_RUNNING:
        if d.seconds_pending_data() > 60*30:
            command = ApiSensorCommand.SYNC  # SYNC
        else:
            command = ApiSensorCommand.IGNORESYNC
        session = Session2.query.filter(Session2.motion_device_id == d.id).filter(Session2.closed == False).first()
        if session == None: # Might happen with legacy transition
            session = Session2(created=datetime.utcnow(), start_time=datetime.utcnow(), motion_device_id = d.id)
            db.session.add(session)
            db.session.commit()
        session_id = session.id

    elif d.sensor_state is None or d.sensor_state == MotionDevice.SENSOR_STATE_UNKNOWN or d.firmware_version is None:
        command = ApiSensorCommand.INTERROGATE  # INTERROGATE
    else:
        command = ApiSensorCommand.IGNORE  # IGNORE

    if command != 0:
        action = GatewaySensorActionRequest(
            sensor_id=d.id,
            timestamp=datetime.utcnow(),
            action_type=command,
            session_id=session_id)
        db.session.add(action)
    else:
        action = None

    return command, action, d


class DiscoveredDevice(object):
    def __init__(self, mac, device_state, device_type, connected_state, rssi):
        self.mac = mac
        self.device_state = device_state
        self.device_type = device_type
        self.connected_state = connected_state # 0 = not connected, 1 = connected to me, 2 = connected to other
        self.rssi = rssi


def discovered_device_type(value):
    try:
        x = DiscoveredDevice(**value)
    except Exception as e:
        raise ValueError(str(e))
    return x


def enforce_list(item):
    if item == None:
        return []
    elif type(item) == list:
        return item
    else:
        return [item]


@api_resource('/gwapi/1.0/gateway/scanresult')
class GatewayDeviceScanResultAPI(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('device_id', type=str, required=True)
        parser.add_argument('trigger', type=int, required=True)
        parser.add_argument('state_flags', type=int, required=True)
        parser.add_argument('devices', type=discovered_device_type, action='list', required=False)
        parser.add_argument('meta', type=str, required=False)
        return parser.parse_args()

    def post(self):
        """Discovered MotionDevice"""

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        # This request uses some extra sql queries. #todo: fix this
        flask.g.stats_sql_count_max = 50

        # Find GW device
        g = GatewayDevice.query.filter(GatewayDevice.local_id == args['device_id']).first()
        if not g:
            return build_response({}, status_code=ApiStatus.STATUS_DEVICE_NOT_FOUND)

        # Create Report
        report = GatewayScanReport(gateway_device_id=g.id, timestamp=datetime.utcnow(), triggertype=args['trigger'], gateway_state=args['state_flags'], meta=args['meta'])
        db.session.add(report)
        g.last_report = report

        reply = []
        devices = enforce_list(args["devices"])

        for d in devices:
            command, action, device = get_sensor_action(d.mac, d.device_state, d.device_type, g)
            seen = GatewaySensorDiscovered(scan_report=report,
                                           sensor_id=device.id,
                                           sensor_state=d.device_state,
                                           sensor_rssi=d.rssi,
                                           connected_state=d.connected_state,
                                           action_request=action)
            db.session.add(seen)
            reply.append({'sensor_id': device.short_name(),
                          'sensor_model': "SENS motion Plus",
                          'mac': device.mac_string(),
                          'command_id': command,
                          'pending_data': device.seconds_pending_data() if (command == ApiSensorCommand.SYNC or command == ApiSensorCommand.IGNORESYNC) else None,
                          'action_id': action})

        db.session.commit()

        # Replace action with action_id. Must be done after commit.
        for r in reply:
            if r['action_id'] is not None:
                r['action_id'] = r['action_id'].id

        return build_response({'sensors': reply})
