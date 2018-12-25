import json

import itertools

from datetime import datetime
from flask_restful import Resource, reqparse, abort
from api.api_json import api_json_from_sensor, api_json_from_sensor_pool
from api.error_codes import ApiStatus
from components import obscure, db
from query.sensordata.sensor_query import extend_sensors_remote_details, extend_sensor_measurements, \
    fetch_sensor_from_id, fetch_all_sensors_for_project
from query.structure.projects_query import fetch_org_and_project
from .helpers import api_resource, build_response, id_array_argument, str_array_argument, id_argument, id_out
from .auth import check_auth


@api_resource('/api/1.0/sensors', endpoint='/api/1.0/sensors')
class ApiGetSensors(Resource):
    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        parser.add_argument('org_id', type=id_argument, required=True, location='args')
        parser.add_argument('project_id', type=id_argument, required=True, location='args')
        return parser.parse_args()

    def get(self):
        """
        List Sensors

        Returns a list of all available sensors under a certain project
        ---
        tags:
          - Sensor Management
        parameters:
          - name: Auth-Token
            in: header
            schema:
                type: string
                default: fake
                required: true
          - name: org_id
            in: query
            type: string
            default:
            required: true
          - name: project_id
            in: query
            type: string
            default:
            required: true
        responses:
          200:
            description: Success
          400:
            description: Invalid Parameters
          401:
            description: Authentication Failed
            examples:
        """
        args = self.parse_args()
        user = check_auth(args)

        org, proj = fetch_org_and_project(user, args['org_id'], args['project_id'])

        if org is None:
            return build_response(None, status_code=ApiStatus.STATUS_ORG_NOT_FOUND)

        if proj is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROJECT_NOT_FOUND)

        # Return all sensors in project
        sensor_pools = proj.sensor_pools

        # Get remote details of all sensors
        all_sensors = fetch_all_sensors_for_project(proj)
        extend_sensors_remote_details(all_sensors)

        return build_response(
            {
                'sensors': [api_json_from_sensor(s) for s in all_sensors],
                'sensor_pools': [api_json_from_sensor_pool(p) for p in sensor_pools]
            }
        )


@api_resource('/api/1.0/sensor/details')
class ApiGetSensor(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        parser.add_argument('org_id', type=id_argument, required=True, location='args')
        parser.add_argument('project_id', type=id_argument, required=True, location='args')
        parser.add_argument('sensor_id', type=id_argument, required=True, location='args')
        parser.add_argument('include_pools', type=int, required=False, default=False, location='args')
        parser.add_argument('include_data_sessions', type=int, required=False, default=False, location='args')
        return parser.parse_args()

    def get(self):
        """
        Get Sensor Details

        Returns meta infor about a given sensor
        ---
        tags:
          - sensors
        parameters:
          - name: Auth-Token
            in: header
            schema:
                type: string
                default: fake
                required: true
          - name: org_id
            in: query
            type: string
            default:
            required: true
          - name: project_id
            in: query
            type: string
            default:
            required: true
          - name: sensor_id
            in: query
            type: string
            default:
            required: true
          - name: include_pools
            in: query
            type: integer
            default: 0
            required: false
          - name: include_data_sessions
            in: query
            type: integer
            default: 0
            required: false
        responses:
          200:
            description: Success
          400:
            description: Invalid Parameters
          401:
            description: Authentication Failed
            examples:
        """
        args = self.parse_args()
        user = check_auth(args)

        org, proj = fetch_org_and_project(user, args['org_id'], args['project_id'])

        if org is None:
            return build_response(None, status_code=ApiStatus.STATUS_ORG_NOT_FOUND)

        if proj is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROJECT_NOT_FOUND)

        sensor = fetch_sensor_from_id(args['sensor_id'], proj)

        if sensor is None:
            return build_response(None, status_code=ApiStatus.STATUS_SENSOR_NOT_FOUND)

        extend_sensors_remote_details([sensor])
        response = {'sensor': api_json_from_sensor(sensor)}

        if args['include_pools']:
            response['sensor_pools'] = []

        if args['include_data_sessions']:
            extend_sensor_measurements(sensor)
            response['data_sessions'] = [
                {'id': id_out(session.id),
                 'start_time': session.start_time.isoformat(),
                 'end_time': session.end_time.isoformat() if session.end_time is not None else datetime.utcnow().isoformat(),
                 'closed': session.end_time is not None,
                 'streams': [{'type': stream.stream_type, 'sample_rate': stream.get_rate()} for stream in session.streams]
                 } for session in sensor.sessions
            ]

        return build_response(
            response
        )


@api_resource('/api/1.0/sensor/control')
class ApiControlSensor(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        parser.add_argument('org_id', type=id_argument, required=True, location='json')
        parser.add_argument('project_id', type=id_argument, required=True, location='json')
        parser.add_argument('sensor_id', type=id_argument, required=True, location='json')
        parser.add_argument('command', type=str, required=True, location='json')
        return parser.parse_args()

    def post(self):
        args = self.parse_args()
        user = check_auth(args)

        org, proj = fetch_org_and_project(user, args['org_id'], args['project_id'])

        if org is None:
            return build_response(None, status_code=ApiStatus.STATUS_ORG_NOT_FOUND)

        if proj is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROJECT_NOT_FOUND)

        sensor = fetch_sensor_from_id(args['sensor_id'], proj)

        if sensor is None:
            return build_response(None, status_code=ApiStatus.STATUS_SENSOR_NOT_FOUND)

        if args['command'] not in ['activate', 'deactivate']:
            build_response(None, status_code=ApiStatus.STATUS_INVALID_PARAMETER)

        extend_sensors_remote_details([sensor])
        if args['command'] == 'activate':
            sensor.remote_details.activated = True
        elif args['command'] == 'deactivate':
            sensor.remote_details.activated = False
        else:
            assert False

        db.session.commit()

        return build_response({})
