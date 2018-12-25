from flask_restful import Resource, reqparse, abort
from query.structure.projects_query import fetch_all_orgs_for_user
from .helpers import api_resource, build_response, id_array_argument, id_out
from .auth import check_auth


@api_resource('/api/1.0/organizations', endpoint='/api/1.0/organizations')
class ApiGetOrganizations(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        return parser.parse_args()

    def get(self):
        """
        List Organizations

        Returns a list of all available organizations
        ---
        tags:
          - Project & Organization Management
        parameters:
          - name: Auth-Token
            in: header
            schema:
                type: string
                default: fake
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

        orgs = fetch_all_orgs_for_user(user)

        return build_response(
            {
                'organizations':
                [{
                    'id': id_out(o.id),
                    'short_name': o.short_name,
                    'full_name': o.name,
                } for o in orgs]
            }
        )


@api_resource('/api/1.0/projects', endpoint='/api/1.0/projects')
class ApiGetProjects(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers', default='')
        parser.add_argument('org_id', type=id_array_argument, required=False, default=[], location='args')
        return parser.parse_args()

    def get(self):
        """
        List Projects

        Returns a list of all available projects under an organization.
        If org_id is not specified, it will list all organizations and projects
        ---
        tags:
          - Project & Organization Management
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
            required: false
        responses:
          200:
            description: Success
          400:
            description: Invalid Parameters
          401:
            description: Authentication Failed
            examples:
          406:
            description: Failed to handle request. See returned API status_code.
            examples:
        """
        args = self.parse_args()
        user = check_auth(args)
        org_ids = args['org_id']

        orgs = fetch_all_orgs_for_user(user, include_projects=False)

        response = [
            {
                'organization': {
                    'id': id_out(org.id),
                    'short_name': org.short_name,
                    'full_name': org.name,
                },
                'projects': [
                    {
                        'id': id_out(p.id),
                        'short_name': p.short_name,
                        'full_name': p.name,
                        'created': p.created_time.isoformat(),
                        'active': p.active,
                        'project_class': p.project_class
                    } for p in org.projects]
            } for org in orgs if org.id in org_ids or org_ids == []]

        if len(response) == 0:
            return build_response(None, status_code=3)
        else:
            return build_response(response)

