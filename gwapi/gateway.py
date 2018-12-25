from datetime import datetime
from werkzeug.exceptions import BadRequest
from api.error_codes import ApiStatus
from components import db
from flaskapp import app
from models import GatewayDevice
from ..api.helpers import api_resource, build_response, default_help, build_parameter_error_respose
from flask_restful import reqparse, Resource


@api_resource('/gwapi/1.0/gateway/register')
class ApiGatewayRegister(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('device_id', type=str, required=True, help=default_help)
        parser.add_argument('device_name', required=True, help=default_help)
        parser.add_argument('device_platform', type=int, required=True, help=default_help)
        parser.add_argument('app_version', type=str, required=True, help=default_help)
        parser.add_argument('app_build', type=str, required=True, help=default_help)

        return parser.parse_args()

    def post(self):
        """
        Register Gateway Meta

        Must be called when gateway changes meta
        ---
        parameters:
          - name: json
            in: body
            schema:
                type: object
                properties:
                    device_id:
                        type: string
                        default: swagger
                    device_id:
                        type: string
                        default: swagger
                    device_platform:
                        type: string
                        default: 2
                    app_version:
                        type: string
                        default: 3.0.0
                    app_build:
                        type: string
                        default: debug
            required: true
        responses:
          200:
            description: Data Accepted
            examples:
          400:
            description: Invalid Parameters
            examples:
          406:
            description: Failed to handle request. See returned API status_code.
            examples:

        """
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        g = GatewayDevice.query.filter(GatewayDevice.local_id==args['device_id']).first()
        if g:
            g.name = args['device_name']
        else:
            g = GatewayDevice(local_id=args['device_id'], name=args['device_name'])
            db.session.add(g)

        g.version = args["app_version"]
        g.build = args["app_build"]
        g.platform = args["device_platform"]

        g.last_online = datetime.utcnow()
        db.session.commit()

        version_parts = g.version.split('.')
        v_minor = version_parts[2].split('-')[0]
        version_num = int(version_parts[0]) * 10000 + int(version_parts[1]) * 100 + int(v_minor)
        if version_num < 20300:
            return build_response({}, status_code=ApiStatus.STATUS_UNSUPPORTED_VERSION)

        return build_response({})


@api_resource('/gwapi/1.0/gateway/refresh')
class ApiGatewayRefresh(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('device_id', type=str, required=True, help=default_help)
        parser.add_argument('app_parameters', type=str, required=True, help=default_help)
        parser.add_argument('app_state', type=str, required=True, help=default_help)

        return parser.parse_args()

    def post(self):
        """
        Register Gateway Meta

        Must be called when gateway changes meta
        ---
        parameters:
          - name: json
            in: body
            schema:
                type: object
                properties:
                    device_id:
                        type: string
                        default: device_id
                    device_id:
                        type: string
                        default: app_parameters
                    device_platform:
                        type: string
                        default: app_state
            required: true
        responses:
          200:
            description: Data Accepted
            examples:
          400:
            description: Invalid Parameters
            examples:
          406:
            description: Failed to handle request. See returned API status_code.
            examples:

        """
        try:
            args = self.parse_args()
        except BadRequest as e:
            return build_parameter_error_respose(e)

        g = GatewayDevice.query.filter(GatewayDevice.local_id == args['device_id']).first()

        if not g:
            return build_response({}, status_code=ApiStatus.STATUS_DEVICE_NOT_FOUND)

        g.parameters = args["app_parameters"]
        g.state_info = args["app_state"]

        g.last_online = datetime.utcnow()
        db.session.commit()

        return build_response({})

