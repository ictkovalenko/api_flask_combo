from datetime import datetime, timedelta

from flask import json
from flask_restful import Resource, reqparse, abort
from sqlalchemy.orm import joinedload
from werkzeug.exceptions import BadRequest

from api.api_json import api_json_from_sensor, api_json_from_sensor_remote_details
from api.helpers import api_resource, build_parameter_error_respose, build_response, id_encoded, id_argument
from models import MotionDevice, GatewayDevice, GatewayScanReport, GatewaySensorActionRequest, \
    GatewaySensorDiscovered, db
from query.sensordata.sensor_query import extend_sensors_remote_details
from utils import time_ago, isoformat_or_none


@api_resource('/gwapi/1.0/adminx/sensors')
class AdminSensorsApi(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        return parser.parse_args()

    def get(self):
        """
        Admin Sensors

        Factory Methods
        ---
        responses:
          200:
            description: Data Accepted
            examples:

        """

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        sensors = MotionDevice.query.all()

        def build_json(s):
            return {
                'db_e': id_encoded(s.id),
                'db': s.id,
                'id': s.short_name(),
                'activated': s.activated,
                'state': s.sensor_state,
                'version': s.firmware_version,
                'last_seen': None if s.last_seen is None else s.last_seen.isoformat(),
                'delivery': s.delivery
            }

        sensors_json = [build_json(s) for s in sensors]

        return build_response({'sensors': sensors_json})


@api_resource('/gwapi/1.0/adminx/gateways')
class AdminGatewaysApi(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('hours', type=int, required=False, location='args', default=24*7)
        parser.add_argument('for_site', type=int, required=False, location='args', default=0)
        parser.add_argument('for_org', type=int, required=False, location='args', default=0)
        return parser.parse_args()

    def get(self):
        """
        Gateway Devices

        Factory Methods
        ---
        parameters:
          - name: hours
            in: query
            type: int
            default: 24
          - name: for_site
            in: query
            type: int
            default: 0
          - name: for_org
            in: query
            type: int
            default: 0
        responses:
          200:
            description: Data Accepted
            examples:

        """

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        if args['for_site'] == 413911:
            gateways = GatewayDevice.query \
                .filter(GatewayDevice.last_online > datetime.utcnow() - timedelta(hours=args['hours'])) \
                .filter(GatewayDevice.last_online != None) \
                .filter(GatewayDevice.parameters.contains('413911')) \
                .order_by(GatewayDevice.name) \
                .all()
        elif args['for_site'] == 0:
            gateways = GatewayDevice.query\
                .filter(GatewayDevice.last_online>datetime.utcnow()-timedelta(hours=args['hours']))\
                .filter(GatewayDevice.last_online!=None)\
                .order_by(GatewayDevice.name)\
                .all()
        else:
            gateways = []

        reports = GatewayScanReport.query\
            .filter(GatewayScanReport.gateway_device_id.in_([g.id for g in gateways]))\
            .filter(GatewayScanReport.timestamp > time_ago(hours=1))\
            .options(joinedload(GatewayScanReport.seen))\
            .all()

        gateway_extra = {
            g.id: {'nearby': set(), 'last_report': None}
            for g in gateways
        }
        for r in reports:
            extra = gateway_extra[r.gateway_device_id]
            for s in r.seen:
                extra['nearby'].add(s.sensor)

        print(json.dumps({'a': 'b'}))

        def build_json(d):
            last_report = d.last_report
            s = d.state_info.decode('utf-8').replace("\'", "\"")
            return {
                'id': id_encoded(d.id),
                'name': d.name,
                'platform': d.platform,
                'version': d.version,
                'build': d.build,
                'last_online': isoformat_or_none(d.last_online),
                'last_report': None if last_report is None else {'timestamp': last_report.timestamp.isoformat(), 'meta': json.loads(last_report.meta.replace('\'', '"'))},
                'nearby': [{'id': id_encoded(d.id), 'name': d.short_name()} for d in sorted(gateway_extra[d.id]['nearby'], key=lambda x: x.id)],
                'stats': json.loads(s) if s != '' else {}
            }

        sensors_json = [build_json(s) for s in gateways]

        return build_response({'gateways': sensors_json})


@api_resource('/gwapi/1.0/adminx/gateway/details')
class AdminGatewayDetailsApi(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('gateway_id', type=id_argument, required=True, location='args')
        return parser.parse_args()

    def get(self):
        """
        Gateway Details

        Factory Methods
        ---
        parameters:
          - name: gateway_id
            in: query
            type: string
            default: ZHP0N45
        responses:
          200:
            description: Data Accepted
            examples:

        """

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        gateway = GatewayDevice.query\
            .get(args['gateway_id'])

        if gateway is None:
            abort(500) # proper error

        reports = GatewayScanReport.query\
            .filter(GatewayScanReport.gateway_device_id.in_([gateway.id]))\
            .filter(GatewayScanReport.timestamp > time_ago(hours=2))\
            .options(joinedload(GatewayScanReport.seen))\
            .all()

        gateway_extra = {
            g.id: {'nearby': set(), 'last_report': None}
            for g in [gateway]
        }
        for r in reports:
            extra = gateway_extra[r.gateway_device_id]
            for s in r.seen:
                extra['nearby'].add(s.sensor)

        def build_json(d):
            last_report = d.last_report

            # todo: Since the DB has state_info as BLOB. Change it to VARCHAR
            def ensure_str(v):
                if isinstance(v, str):
                    return v
                else:
                    return v.decode('utf-8')

            s = ensure_str(d.state_info).replace("\'", "\"")
            p = ensure_str(d.parameters).replace("\'", "\"")
            return {
                'id': id_encoded(d.id),
                'local_id': d.local_id,
                'name': d.name,
                'platform': d.platform,
                'version': d.version,
                'build': d.build,
                'last_online': isoformat_or_none(d.last_online),
                'last_report': None if last_report is None else {'timestamp': last_report.timestamp.isoformat(), 'meta': json.loads(last_report.meta.replace('\'', '"'))},
                'nearby': [{'id': id_encoded(d.id), 'name': d.short_name()} for d in sorted(gateway_extra[d.id]['nearby'], key=lambda x: x.id)],
                'stats': json.loads(s) if s != '' else {},
                'parameters': json.loads(p) if s != '' else {}
            }

        return build_response({'gateway': build_json(gateway)})


def api_helper_nearby_devices(gateway_id_list):
    reports = GatewayScanReport.query \
        .filter(GatewayScanReport.gateway_device_id.in_(gateway_id_list)) \
        .filter(GatewayScanReport.timestamp > time_ago(hours=2)) \
        .options(joinedload(GatewayScanReport.seen)) \
        .all()

    gateway_extra = {
        g_id: {'nearby': set(), 'last_report': None}
        for g_id in gateway_id_list
    }

    for r in reports:
        extra = gateway_extra[r.gateway_device_id]
        for s in r.seen:
            extra['nearby'].add(s.sensor)

    return gateway_extra


@api_resource('/gwapi/1.0/adminx/gateway/nearby_sensors')
class AdminGatewayNearbySensorsApi(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('gateway_id', type=id_argument, required=True, location='args')
        parser.add_argument('nearby_sensors_hours', type=int, required=False, location='args')
        return parser.parse_args()

    def get(self):
        """
        Gateway Devices

        Factory Methods
        ---
        parameters:
          - name: gateway_id
            in: query
            type: string
            default: ZHP0N45
          - name: nearby_sensors_hours
            in: query
            type: int
            default: 3
        responses:
          200:
            description: Data Accepted
            examples:

        """

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        nearby_sensors = api_helper_nearby_devices([args['gateway_id']])[args['gateway_id']]['nearby']

        return build_response({'sensors': [api_json_from_sensor_remote_details(s) for s in nearby_sensors]})


@api_resource('/gwapi/1.0/adminx/gateway/scanreports')
class AdminGatewayScanReportsApi(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('gateway_id', type=id_argument, required=True, location='args')
        parser.add_argument('scan_report_hours', type=int, required=False, location='args')
        return parser.parse_args()

    def get(self):
        """
        Gateway Devices

        Factory Methods
        ---
        parameters:
          - name: gateway_id
            in: query
            type: string
            default: ZHP0N45
          - name: scan_report_hours
            in: query
            type: int
            default: 12
          - name: nearby_sensors_hours
            in: query
            type: int
            default: 3
        responses:
          200:
            description: Data Accepted
            examples:

        """

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        if args['scan_report_hours'] is not None:
            reports = GatewayScanReport.query\
                .filter(GatewayScanReport.gateway_device_id==args['gateway_id'])\
                .filter(GatewayScanReport.timestamp>datetime.utcnow()-timedelta(hours=args['scan_report_hours']))\
                .order_by(GatewayScanReport.timestamp.desc())\
                .options(joinedload(GatewayScanReport.seen).joinedload(GatewaySensorDiscovered.sensor)) \
                .options(joinedload(GatewayScanReport.seen).joinedload(GatewaySensorDiscovered.action_request)) \
                .all()
        else:
            reports = None

        def parse_flags(flags, map):
            return ",".join([map[k][1] if (1 << k & flags) else map[k][0] for k in map.keys()])

        def build_json(r):
            return {
                'id': id_encoded(r.id),
                'time': r.timestamp.isoformat(),
                'trigger': GatewayScanReport.TRIGGER[r.triggertype],
                'state_flags': r.gateway_state,
                'state': parse_flags(r.gateway_state, GatewayScanReport.GATEWAY_STATE_FLAGS),
                'meta': r.meta,
                'devices': [
                    {'id': id_encoded(s.id),
                     'name': s.sensor.short_name(),
                     'action': s.action_request.action_type if s.action_request is not None else 0,
                     'records': s.action_request.synced_record_last - s.action_request.synced_record_first if s.action_request is not None and s.action_request.synced_record_last is not None else 0
                     } for s in r.seen]
            }

        reports_json = [build_json(s) for s in reports] if reports is not None else None

        return build_response({'reports': reports_json})


@api_resource('/gwapi/1.0/adminx/gateway/seen')
class AdminGatewaySensorSeenEventsApi(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('gateway_id', type=id_argument, required=True, location='args')
        parser.add_argument('sensor_id', type=id_argument, required=True, location='args')
        parser.add_argument('seen_hours', type=int, required=True, default=12, location='args')
        return parser.parse_args()

    def get(self):
        """
        Gateway Devices

        Factory Methods
        ---
        parameters:
          - name: gateway_id
            in: query
            type: string
            default: ZHP0N45
          - name: sensor_id
            in: query
            type: string
            default: ZHP0N45
          - name: seen_hours
            in: query
            type: int
            default: 12
        responses:
          200:
            description: Data Accepted
            examples:

        """

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        reports = GatewayScanReport.query\
            .filter(GatewayScanReport.gateway_device_id==args['gateway_id'])\
            .filter(GatewayScanReport.timestamp>datetime.utcnow()-timedelta(hours=args['seen_hours']))\
            .filter(GatewayScanReport.triggertype != 0)\
            .order_by(GatewayScanReport.timestamp.desc())\
            .options(joinedload(GatewayScanReport.seen).joinedload(GatewaySensorDiscovered.sensor)) \
            .options(joinedload(GatewayScanReport.seen).joinedload(GatewaySensorDiscovered.action_request)) \
            .all()

        sensor_id = args['sensor_id']
        seen_events = []
        for r in reports:
            for s in [s for s in r.seen if s.sensor.id == sensor_id]:
                seen_events.append(
                    {
                        'timestamp': r.timestamp.isoformat(),
                        'action_type': s.action_request.action_type if s.action_request is not None else 0,
                        'status_accepted': s.action_request.status_accepted if s.action_request is not None else 0,
                        'status_connected': s.action_request.status_connected if s.action_request is not None else 0,
                        'status_completed': s.action_request.status_completed if s.action_request is not None else 0,
                        'status_interrupted': s.action_request.status_interrupted if s.action_request is not None else 0
                    }
                )

        return build_response({'seen_events': seen_events})


@api_resource('/gwapi/1.0/adminx/gateway/scanreport')
class AdminGatewayReportApi(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('report_id', type=id_argument, required=True, location='args')
        return parser.parse_args()

    def get(self):
        """
        Gateway Devices

        Factory Methods
        ---
        parameters:
          - name: report_id
            in: query
            type: string
            default: ZHP0N45
        responses:
          200:
            description: Data Accepted
            examples:

        """

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        report = GatewayScanReport.query.get(args['report_id'])

        def build_json(s):
            return {
                'id': s.sensor.short_name(),
                'state': MotionDevice.SENSOR_STATE_TYPE[s.sensor_state],
                'rssi': s.sensor_rssi,
                'action': GatewaySensorActionRequest.ACTION_TYPE[s.action_request.action_type],
                'status_accepted': s.action_request.status_accepted,
                'status_connected': s.action_request.status_connected,
                'status_interrupted': s.action_request.status_interrupted,
                'status_completed': s.action_request.status_completed,
                'state_tx': s.action_request.state_tx,
                'state_pending': s.action_request.state_pending_records,
                'session_id': s.action_request.session_id,
                'msg': s.action_request.msg
            }

        value_json = [build_json(s) for s in report.seen]

        return build_response({'report': {'time': report.timestamp.isoformat(), 'discovered': value_json}})


@api_resource('/gwapi/1.0/adminx/gateway/cleanup')
class AdminGatewayCleanupApi(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        return parser.parse_args()

    def get(self):
        """
        Cleanup Devices

        Factory Methods
        ---
        responses:
          200:
            description: Data Accepted
            examples:

        """

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        report_cnt = GatewayScanReport.query.filter(GatewayScanReport.timestamp < datetime.utcnow() - timedelta(days=30)).count()
        GatewayScanReport.query.filter(GatewayScanReport.timestamp < datetime.utcnow() - timedelta(days=30)).delete()

        first = GatewayScanReport.query.order_by(GatewayScanReport.id).first()

        seen_cnt = GatewaySensorDiscovered.query.filter(GatewaySensorDiscovered.scan_report_id < first.id).count()
        GatewaySensorDiscovered.query.filter(GatewaySensorDiscovered.scan_report_id < first.id).delete()

        db.session.commit()

        return build_response(
            {
                'scanrecords': report_cnt,
                'seen': seen_cnt
            })


@api_resource('/gwapi/1.0/adminx/sensor/activate')
class AdminSensorActivateApi(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('sensor_id', type=id_argument, required=True, location='json')
        return parser.parse_args()

    def post(self):
        """
        Gateway Devices

        Factory Methods
        ---
        parameters:
          - name: sensor_id
            in: query
            type: string
            default: ZHP0N45
        responses:
          200:
            description: Data Accepted
            examples:

        """

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        sensor = MotionDevice.query.get(args['sensor_id'])
        sensor.activated = True
        db.session.commit()

        return build_response({'mac': sensor.mac_string()})


@api_resource('/gwapi/1.0/adminx/sensor/deactivate')
class AdminSensorDeactivateApi(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('sensor_id', type=id_argument, required=True, location='json')
        return parser.parse_args()

    def post(self):
        """
        Gateway Devices

        Factory Methods
        ---
        parameters:
          - name: sensor_id
            in: query
            type: string
            default: ZHP0N45
        responses:
          200:
            description: Data Accepted
            examples:

        """

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        sensor = MotionDevice.query.get(args['sensor_id'])
        sensor.activated = False
        db.session.commit()

        return build_response({'mac': sensor.mac_string()})


@api_resource('/gwapi/1.0/adminx/sensor/terminate')
class AdminSensorTerminateApi(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('sensor_id', type=id_argument, required=True, location='json')
        return parser.parse_args()

    def post(self):
        """
        Gateway Devices

        Factory Methods
        ---
        parameters:
          - name: sensor_id
            in: query
            type: string
            default: ZHP0N45
        responses:
          200:
            description: Data Accepted
            examples:

        """

        # Parse Arguments
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        sensor = MotionDevice.query.get(args['sensor_id'])
        sensor.terminated = True
        db.session.commit()

        return build_response({'mac': sensor.mac_string()})
