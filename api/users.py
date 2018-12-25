import uuid

from flask_mail import Message, Mail
from flask_restful import Resource, reqparse


from api.error_codes import ApiStatus
from components import db
from flaskapp import mail
from .helpers import api_resource, build_response, id_argument
from models.structure.user import User, create_user, shadow_pwd
from api.mail_settings import MailSettings


@api_resource('/api/1.0/user/add', endpoint='/api/1.0/user/add')
class ApiAddUsers(Resource):
    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('email', type=str, required=True, location='json')
        parser.add_argument('pwd', type=str, required=True, location='json')

        return parser.parse_args()

    def post(self):
        """
        Add user

        Create a new user
        ---
        tags:
          - User Management
        parameters:
          - name: json
            in: body
            schema:
                type: object
                properties:
                    email:
                        type: string
                        required: true
                        default: None
                    pwd:
                        type: string
                        required: true
                        default: None

            required: true
        responses:
          200:
            description: User added succesfully
            examples: {'blah'}
          400:
            description: Invalid Parameters
            examples:
          406:
            description: Failed to handle request. See returned API status_code.
            examples:

        """
        args = self.parse_args()

        email = args['email'].strip()
        pwd = args['pwd'].strip()

        user, code = create_user(email, pwd)

        status_code = code if user is None else ApiStatus.STATUS_OK

        return build_response(None, status_code)


@api_resource('/api/1.0/password/reset', endpoint='/api/1.0/password/reset')
class ApiPasswordReset(Resource):
    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('email', type=str, required=True, location='json')

        return parser.parse_args()

    def post(self):
        """
        Password Reset
        ---
        tags:
          - Password Management
        parameters:
          - name: json
            in: body
            schema:
                type: object
                properties:
                    email:
                        type: string
                        required: true
                        default: None

            required: true
        responses:
          200:
            description: reset mail send
            examples: {'blah'}
          400:
            description: Invalid Parameters
            examples:
          406:
            description: Failed to handle request. See returned API status_code.
            examples:

        """
        args = self.parse_args()

        email = args['email'].strip()

        if not email:
            return build_response(None, ApiStatus.STATUS_USER_NOT_FOUND)

        user = User.get_from_email(email)

        if user is None:
            return build_response(None, ApiStatus.STATUS_USER_NOT_FOUND)

        user.reset_password_token = uuid.uuid4().hex
        db.session.commit()

        msg = Message(
            subject=MailSettings.subject,
            sender=MailSettings.sender,
            recipients=[email]
        )

        msg.html = MailSettings.message_body.format(
            MailSettings.host.format(
                user.reset_password_token
            )
            )

        mail.send(msg)

        return build_response(None, ApiStatus.STATUS_OK)


@api_resource('/api/1.0/password/reset/done', endpoint='/api/1.0/password/reset/done')
class ApiPasswordResetDone(Resource):
    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('hash_str', type=str, required=True, location='json')
        parser.add_argument('pwd', type=str, required=True, location='json')

        return parser.parse_args()

    def post(self):
        """
        Password Reset
        ---
        tags:
          - Password Management
        parameters:
          - name: json
            in: body
            schema:
                type: object
                properties:
                    hash_str:
                        type: string
                        required: true
                        default: None
                    pwd:
                        type: string
                        required: true
                        default: None

            required: true
        responses:
          200:
            description: reset mail done
            examples: {'blah'}
          400:
            description: Invalid Parameters
            examples:
          406:
            description: Failed to handle request. See returned API status_code.
            examples:

        """

        args = self.parse_args()

        reset_password_token = args['hash_str'].strip()

        if reset_password_token is None:
            return build_response(None, ApiStatus.STATUS_USER_NOT_FOUND)

        user = User.query.filter(User.reset_password_token == reset_password_token).first()

        if user is None:
            return build_response(None, ApiStatus.STATUS_USER_NOT_FOUND)

        user.reset_password_token = ''

        user.password = user.shadow_pwd(args['pwd'].strip())

        db.session.commit()

        return build_response(None, ApiStatus.STATUS_OK)
