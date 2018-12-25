import numpy
import pytz
from datetime import timedelta, datetime
from flask_restful import Resource, reqparse, abort
from api.auth import check_auth
from api.error_codes import ApiStatus
from api.helpers import build_response, id_argument, str_array_argument, api_resource, datetime_argument, \
    id_out, datenotz_argument
from flaskapp import api
from math.algorithm.algorithms import Algorithms
from models import Organization
from models.structure.measurement import Measurement
from query.deriveddata.derived_data_query import fetch_cached_derived_data_hour, DataNotReady, \
    fetch_derived_data_bins, get_algorithm, DataNotReadyCls
from query.measurements.measurement_query import fetch_measurement
from query.sensordata.sensor_query import extend_sensors_remote_details
from query.structure.patients_query import fetch_patient_from_key, fetch_patient_from_id
from query.structure.projects_query import fetch_org_and_project
from utils import floor_time_to, floor_datetime, utc_start_of_local_today, utc_from_local


@api_resource('/api/1.0/patient_view/progress', endpoint='/api/1.0/patient_view/progress')
class ApiPatientViewProgress(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('project_key', type=str, required=True, location='args')
        parser.add_argument('patient_key', type=str, required=True, location='args')
        parser.add_argument('date', type=datenotz_argument, required=False, location='args')
        parser.add_argument('day_count', type=int, required=False, default=1, location='args')
        return parser.parse_args()

    def get(self):
        """
        Progress Endpoint for Patient Access

        Returns current progress based on patient project_key & patient_key
        ---
        tags:
          - Patient View
        parameters:
          - name: project_key
            in: query
            type: string
            default: AHXTS
            required: true
          - name: patient_key
            in: query
            type: string
            default: 94731
            required: true
          - name: date
            in: query
            type: string
            default:
            required: false
          - name: day_count
            in: query
            type: int
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

        # Allow up to 14 days
        day_count = min(14, args['day_count'])

        # Sharable: Check project + user key

        # todo: read timezone from user
        timezone = pytz.timezone('Europe/Copenhagen')

        # if date not set, use today
        start_day_utc = utc_start_of_local_today(tz=timezone).replace(tzinfo=None)
        if 'date' in args and args['date'] is not None:
            start_day_utc = utc_from_local(args['date'], tz=timezone).replace(tzinfo=None)

        # lookup project key
        project, patient = fetch_patient_from_key(args['project_key'], args['patient_key'])
        if project is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROJECT_NOT_FOUND)
        if patient is None:
            return build_response(None, status_code=ApiStatus.STATUS_PATIENT_NOT_FOUND)

        # Verify valid measurement_id
        end_time_utc = start_day_utc + timedelta(days=day_count)
        m = None
        for m_ in Measurement.query.filter(Measurement.patient_id == patient.id).all():
            if end_time_utc > m_.start_time and start_day_utc < m_.end_time_or_now():
                m = m_
                break

        if m is None:
            return build_response(None, status_code=ApiStatus.STATUS_MEASUREMENT_NOT_FOUND)

        # Verify valid stream

        extend_sensors_remote_details([s.sensor for s in m.attached])
        sensor_device_map = m.get_sensor_map()

        alg = m.profile.alg()

        result = []

        not_ready = False

        for d in range(day_count):
            current = start_day_utc.replace(tzinfo=None) - timedelta(days=d)

            day_sum = {k: 0 for k in alg.__output__}

            bins = fetch_derived_data_bins(
                sensor_map=sensor_device_map,
                alg_profile=m.profile,
                parameters={'mobility': ''},
                start_time=current,
                hours=24,
                bins_per_hour=4)
            # bins returned in format [{'ts': unixts, 'summary': {'cal/tag': minutes}}]

            summed_time = 0
            if isinstance(bins, DataNotReadyCls):
                not_ready = True
            else:
                # Summarize all 24 hour bins
                for b in bins:
                    for k in alg.__output__:
                        day_sum[k] += b['summary'][k]
                        if k.endswith('time'):
                            summed_time += b['summary'][k]

            if 24*60 - summed_time > 0.1:
                day_sum['general/nodata/time'] += 24*60 - summed_time
            result += [
                {'start_time': current.replace(tzinfo=None).isoformat(),
                 'end_time': (current+timedelta(hours=24)).replace(tzinfo=None).isoformat(),
                 'values': day_sum}
            ]

        if not_ready:
            return build_response(None,
                                  status_code=ApiStatus.STATUS_ANALYSIS_IN_PROGRESS)
        else:
            return build_response(
                {
                    'data': result
                }
            )
