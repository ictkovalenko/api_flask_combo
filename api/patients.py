import json

import itertools

from flask_restful import Resource, reqparse

from api.error_codes import ApiStatus
from models import ProjectAccessKey
from models.structure.access_keys import generate_ak, PatientAccessKey
from query.structure.projects_query import fetch_all_orgs_for_user
from query.structure.patients_query import fetch_patients_from_project
from query.structure.projects_query import fetch_org_and_project
from query.structure.patients_query import fetch_patient_from_id

from .helpers import api_resource, build_response, str_array_argument, id_argument, id_out
from .auth import check_auth
from models.structure.patient import Patient
from components import db


@api_resource('/api/1.0/patients', endpoint='/api/1.0/patients')
class ApiGetPatients(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        parser.add_argument('org_id', type=id_argument, required=True, location='args')
        parser.add_argument('project_id', type=id_argument, required=True, location='args')
        return parser.parse_args()

    def get(self):
        """
        List Patients

        Returns a list of all patients under a certain project
        ---
        tags:
          - Patient Management
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

        all_patients = fetch_patients_from_project(proj)

        if org is None:
            return build_response(None, status_code=ApiStatus.STATUS_ORG_NOT_FOUND)

        if proj is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROJECT_NOT_FOUND)
        filtered_patients = []
        for p in all_patients:
            if p.deleted != 0:
                continue
            else:
                filtered_patients.append(p)

        # Return all patients in project
        response = [
            {
                'project_id': id_out(proj.id),
                'patients': [
                    {
                        'id': id_out(p.id),
                        'short_name': p.short_name,
                        'description': p.description,
                        'deleted': p.deleted,
                        'timezone': p.timezone,
                    } for p in filtered_patients]
            }]

        if len(response) == 0:
            return build_response(None, status_code=3)
        else:
            return build_response(response)


@api_resource('/api/1.0/patient/details', endpoint='/api/1.0/patient/details')
class ApiGetPatientDetails(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        parser.add_argument('org_id', type=id_argument, required=True, location='args')
        parser.add_argument('project_id', type=id_argument, required=True, location='args')
        parser.add_argument('patient_id', type=id_argument, required=True, location='args')
        return parser.parse_args()

    def get(self):
        """
        Get Patient Details

        Returns meta info about a given patient
        ---
        tags:
          - Patient Management
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
          - name: patient_id
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

        p = fetch_patient_from_id(args['patient_id'], proj)

        if org is None:
            return build_response(None, status_code=ApiStatus.STATUS_ORG_NOT_FOUND)

        if proj is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROJECT_NOT_FOUND)

        # Return single patient in project
        response = [
            {
                'project_id': id_out(proj.id),
                'id': id_out(p.id),
                'short_name': p.short_name,
                'description': p.description,
                'deleted': p.deleted,
                'timezone': p.timezone,
            }]

        if len(response) == 0:
            return build_response(None, status_code=3)
        else:
            return build_response(response)


@api_resource('/api/1.0/patient/add', endpoint='/api/1.0/patient/add')
class ApiAddPatients(Resource):
    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        parser.add_argument('org_id', type=id_argument, required=True, location='json')
        parser.add_argument('project_id', type=id_argument, required=True, location='json')
        parser.add_argument('short_name', type=str, required=True, location='json')
        parser.add_argument('description', type=str, required=False, location='json')
        parser.add_argument('mobility', type=str, required=False, location='json')

        return parser.parse_args()

    def post(self):
        """
        Add patient

        Create a new patient under a certain project
        ---
        tags:
          - Patient Management
        parameters:
          - name: Auth-Token
            in: header
            schema:
                type: string
                default: fake
                required: true

          - name: json
            in: body
            schema:
                type: object
                properties:
                    short_name:
                        type: string
                        default:
                    mobility:
                        type: string
                        default: supported/walk
                    description:
                        type: string
                        default: secret
                    org_id:
                        type: string
                        default:
                        required: true
                    project_id:
                        type: string
                        default:
                        required: true

            required: true
        responses:
          200:
            description: Patient added succesfully
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
        org, proj = fetch_org_and_project(user, args['org_id'], args['project_id'])

        if org is None:
            return build_response(None, status_code=ApiStatus.STATUS_ORG_NOT_FOUND)

        if proj is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROJECT_NOT_FOUND)

        short_name = args['short_name'].strip()
        description = args['description'].strip()

        newPatient = Patient(short_name=short_name, project=proj, description=description)
        db.session.add(newPatient)
        db.session.commit()

        return build_response(None)


@api_resource('/api/1.0/patients/edit')
class ApiEditPatients(Resource):
    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        parser.add_argument('org_id', type=id_argument, required=True, location='json')
        parser.add_argument('project_id', type=id_argument, required=True, location='json')
        parser.add_argument('patient_id', type=id_argument, required=True, location='json')
        parser.add_argument('short_name', type=str, required=False, default=None, location='json')
        parser.add_argument('description', type=str, required=False, default=None, location='json')
        parser.add_argument('timezone', type=str, required=False, location='json')

        return parser.parse_args()

    def post(self):
        """
            Edit patient

            Edit patient endpoint
            ---
            tags:
              - Patient Management
            parameters:
              - name: Auth-Token
                in: header
                schema:
                    type: string
                    default: fake
                    required: true

              - name: json
                in: body
                schema:
                    type: object
                    properties:
                        short_name:
                            type: string
                            default:
                        description:
                            type: string
                            default: secret
                        org_id:
                            type: string
                            default:
                            required: true
                        project_id:
                            type: string
                            default:
                            required: true

                required: true
            responses:
              200:
                description: Patient added succesfully
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
        org, proj = fetch_org_and_project(user, args['org_id'], args['project_id'])
        current_patient = fetch_patient_from_id(args['patient_id'], proj)

        if org is None:
            return build_response(None, status_code=ApiStatus.STATUS_ORG_NOT_FOUND)

        if proj is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROJECT_NOT_FOUND)

        if args['short_name'] is not None:
            current_patient.short_name = args['short_name'].strip()

        if args['description'] is not None:
            current_patient.description = args['description'].strip()
        if args['timezone'] is not None:
            current_patient.timezone = args['timezone'].strip()

        db.session.commit()

        import time
        time.sleep(1)

        return build_response(None)


@api_resource('/api/1.0/patients/delete')
class ApiDeletePatients(Resource):
    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        parser.add_argument('org_id', type=id_argument, required=True, location='json')
        parser.add_argument('project_id', type=id_argument, required=True, location='json')
        parser.add_argument('patient_id', type=id_argument, required=True, location='json')
        parser.add_argument('short_name', type=str, required=False, default=None, location='json')
        parser.add_argument('description', type=str, required=False, default=None, location='json')
        parser.add_argument('timezone', type=str, required=False, default=None, location='json')
        parser.add_argument('deleted', type=str, required=False, default='0', location='json')

        return parser.parse_args()

    def post(self):
        """
            Delete patient

            Delete patient endpoint
            ---
            tags:
              - patients
            parameters:
              - name: Auth-Token
                in: header
                schema:
                    type: string
                    default: fake
                    required: true
              - name: json
                in: body
                schema:
                    type: object
                    properties:
                        short_name:
                            type: string
                            default:
                        description:
                            type: string
                            default: secret
                        org_id:
                            type: string
                            default:
                            required: true
                        project_id:
                            type: string
                            default:
                            required: true

                required: true
            responses:
              200:
                description: Patient added succesfully
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
        org, proj = fetch_org_and_project(user, args['org_id'], args['project_id'])
        current_patient = fetch_patient_from_id(args['patient_id'], proj)

        if org is None:
            return build_response(None, status_code=ApiStatus.STATUS_ORG_NOT_FOUND)

        if proj is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROJECT_NOT_FOUND)

        if current_patient.deleted == 0:
            current_patient.deleted = 1

        db.session.commit()

        return build_response(None)


@api_resource('/api/1.0/patient/get_keys', endpoint='/api/1.0/patient/get_keys')
class ApiPatientGetKeys(Resource):
    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        parser.add_argument('org_id', type=id_argument, required=True, location='args')
        parser.add_argument('project_id', type=id_argument, required=True, location='args')
        parser.add_argument('patient_id', type=id_argument, required=True, location='args')

        return parser.parse_args()

    def get(self):
        """
            Get Access Keys for Patient

            Get Keys endpoint
            ---
            tags:
              - Patient Management
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
                required: true
              - name: project_id
                in: query
                type: string
                required: true
              - name: patient_id
                in: query
                type: string
                required: true

            responses:
              200:
                description:  Keys acquired succesfully
                examples: {project_key: 'ABCDEF', patient_key: 'GHIJKL'}
              400:
                description: Invalid Parameters
                examples:
              406:
                description: Failed to handle request. See returned API status_code.
                examples:

            """
        args = self.parse_args()
        user = check_auth(args)
        org, proj = fetch_org_and_project(user, args['org_id'], args['project_id'])

        if org is None:
            return build_response(None, status_code=ApiStatus.STATUS_ORG_NOT_FOUND)

        if proj is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROJECT_NOT_FOUND)

        patient = fetch_patient_from_id(args['patient_id'], proj)
        if patient is None:
            return build_response(None, status_code=ApiStatus.STATUS_PATIENT_NOT_FOUND)

        proj_ak = ProjectAccessKey.query.filter(ProjectAccessKey.project==proj).first()
        if proj_ak is None:
            key = generate_ak()
            proj_ak = ProjectAccessKey(key_string=key, project=proj)
            db.session.add(proj_ak)

        patient_ak = PatientAccessKey.query.filter(PatientAccessKey.patient==patient).first()
        if patient_ak is None:
            key = generate_ak()
            patient_ak = PatientAccessKey(key_string=key, project=proj, patient=patient)
            db.session.add(patient_ak)

        db.session.commit()

        return build_response({'project_key': proj_ak.key_string, 'patient_key': patient_ak.key_string})
