from random import randint
from flask import session
from flask_restful import Resource, reqparse, abort
from api.error_codes import ApiStatus
from models.structure.user import User
from utils import send_sns
from .helpers import api_resource, build_response
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)


def check_auth(args):
    if 'Auth-Token' not in args or args['Auth-Token'] is None:
        abort(401)
    elif args['Auth-Token'] == 'session':
        if 'authtoken' in session:
            args['Auth-Token'] = session['authtoken']
        else:
            abort(401)
    user, status = User.get_from_token(args['Auth-Token'])
    if status != User.SIGNATURE_OK:
        abort(401)

    return user


@api_resource('/api/1.0/authenticate', endpoint='/api/1.0/authenticate')
class ApiAuthenticate(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('user_id', type=str, required=True, location='json')
        parser.add_argument('password', type=str, required=True, location='json')
        parser.add_argument('sns_code', type=str, required=True, location='json')
        return parser.parse_args()

    def post(self):
        """
        Acquire authentication token

        Login endpoint
        ---
        tags:
          - Authentication
        parameters:
          - name: json
            in: body
            schema:
                type: object
                properties:
                    user_id:
                        type: string
                        default: example@gmail.com
                    password:
                        type: string
                        default: secret1234
                    sns_code:
                        type: string
                        default: None
            required: true
        responses:
          200:
            description: Login Succesfull
            examples: {'blah'}
          400:
            description: Invalid Parameters
            examples:
          406:
            description: Failed to handle request. See returned API status_code.
            examples:

        """
        args = self.parse_args()

        if session['sns_code'] != args['sns_code'].strip():
            return build_response(None, ApiStatus.STATUS_WRONG_SNS_CODE)

        user_id = args['user_id'].lower().strip()
        password = args['password'].strip()

        user = User.get_from_email(user_id)

        if user is None:
            return build_response(None, ApiStatus.STATUS_USER_NOT_FOUND)

        if not user.password == user.shadow_pwd(password):
            return build_response(None, ApiStatus.STATUS_INVALID_PASSWORD)

        token = user.generate_auth_token()
        session['authtoken'] = token.decode('ascii')

        return build_response(
            {'auth_token': token.decode('ascii')}
        )


@api_resource('/api/1.0/logout')
class ApiLogout(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        return parser.parse_args()

    def post(self):
        """
        Remove auth token

        Logout endpoint
        ---
        responses:
          200:
            description: Login Succesfull
            examples: {'blah'}
          400:
            description: Invalid Parameters
            examples:
          406:
            description: Failed to handle request. See returned API status_code.
            examples:

        """
        _ = self.parse_args()
        session['authtoken'] = None

        return build_response({})


@api_resource('/api/1.0/permissions')
class ApiPermissions(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        return parser.parse_args()

    def get(self):
        """
        Get auth status and permissions

        Login endpoint
        ---
        responses:
          200:
            description: Login Succesfull
            examples: {'blah'}
          400:
            description: Invalid Parameters
            examples:
          406:
            description: Failed to handle request. See returned API status_code.
            examples:

        """
        args = self.parse_args()

        user = check_auth(args)

        return build_response(
            {'user': user.email}
        )


@api_resource('/api/1.0/snscode')
class ApiSnsCode(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('phone_number', type=str, required=True, location='json')
        return parser.parse_args()

    def post(self):
        """
        Acquire authentication token

        SNS endpoint
        ---
        tags:
          - Authentication get SNS code
        parameters:
          - name: json
            in: body
            schema:
                type: object
                properties:
                    phone_number:
                        type: string
                        default: +1122334455
            required: true
        responses:
          200:
            description: send SNS code
            examples: {'blah'}
          400:
            description: Invalid Parameters
            examples:
          406:
            description: Failed to handle request. See returned API status_code.
            examples:

        """
        args = self.parse_args()
        phone_number = args['phone_number'].strip()

        if phone_number is None:
            return build_response(None, ApiStatus.STATUS_INVALID_PARAMETER)

        sns_code = randint(1000, 9999)

        send_sns(phone_number, sns_code)
        session['sns_code'] = sns_code

        return build_response(None, ApiStatus.STATUS_OK)
