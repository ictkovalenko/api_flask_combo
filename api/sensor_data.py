from datetime import timedelta
from flask import request
from flask_restful import Resource, reqparse, abort
from api.auth import check_auth
from api.error_codes import ApiStatus
from components import ext_cache
from math.algorithm.algorithms import Algorithms
from models.structure.patient import PatientProfile
from models.structure.measurement import AlgProfile
from query.deriveddata.derived_data_query import generate_derived_data, fetch_derived_data_bins, \
    fetch_cached_derived_data_hour, DataNotReady
from query.sensordata.sensor_query import fetch_sensor, fetch_sensor_from_id, extend_sensors_remote_details
from query.sensordata.sensordata_query import fetch_sensor_data_bundle_for_sensor
from query.structure.projects_query import fetch_org_and_project
from .helpers import api_resource, build_response, str_array_argument, datetime_argument, id_argument, id_out
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
import numpy


def format_samples(data_bundle, average, var_names):
    """
    Formats
    :param data_bundle:
    :param average: boolean indicating whether to output data in diff format
    :param var_names: list of names to use for naming output
    :return:
    """
    v = {'ts': []}

    # Add diff variables if diff format
    for l in var_names:
        v[l] = []
        if average:
            v[l + '_diff'] = []

    # min/max used to help plot data
    min_all = None
    max_all = None

    for i, sensor_data in enumerate(data_bundle):
        data = sensor_data.samples()
        ts = sensor_data.ts
        sample_count = len(ts)

        if i == 0:
            min_all = numpy.min(data)
            max_all = numpy.max(data)
        else:
            min_all = numpy.min([min_all, numpy.min(data)])
            max_all = numpy.max([max_all, numpy.max(data)])

        if average:
            # chunk it
            assert(len(data))
            if len(data) > 10:
                # Chunk approx 2 minutes based on ts of first 10 samples
                # 24h = 1440 minutes => 720 values
                chunk_size = int(2*60000*10/(ts[10] - ts[0]))+1
            else:
                chunk_size = len(data)
            chunk_count_c = int(numpy.ceil(len(data)/chunk_size))
            chunk_count_f = int(numpy.floor(len(data)/chunk_size))

            print(chunk_count_c, chunk_count_f)

            # Initialize arrays
            avg_samples = numpy.zeros([chunk_count_c, data.shape[1]])
            min_samples = numpy.zeros([chunk_count_c, data.shape[1]])
            max_samples = numpy.zeros([chunk_count_c, data.shape[1]])
            ts_new = numpy.zeros(chunk_count_c, dtype=numpy.int64)

            # First analyze complete chunks
            data1 = data[:chunk_count_f*chunk_size]
            data1.shape = (chunk_count_f, chunk_size, data.shape[1])
            for i in range(chunk_count_f):
                min_value = numpy.min(data1[i], axis=0)
                max_value = numpy.max(data1[i], axis=0)
                avg_samples[i] = numpy.median(data1[i], axis=0)
                min_samples[i] = min_value
                max_samples[i] = max_value
                ts_new[i] = ts[i*chunk_size]

            # Analyze incomplete chuunk if required
            if chunk_count_c != chunk_count_f:
                i = chunk_count_c - 1
                data2 = data[chunk_count_f*chunk_size:]
                min_value = numpy.min(data2, axis=0)
                max_value = numpy.max(data2, axis=0)
                avg_samples[i] = numpy.median(data2, axis=0)
                min_samples[i] = min_value
                max_samples[i] = max_value
                ts_new[i] = ts[i*chunk_size]

            # Not sure what this does
            #if avg_samples.shape[0] > 1:
            #    avg_samples[-1] = avg_samples[-2]
            #    min_samples[-1] = min_samples[-2]
            #    max_samples[-1] = max_samples[-2]
            #    ts_new[-1] = ts_new[-2] + 60000

            # Insert None in time holes, to show a hole in the plot
            if i != 0:
                v['ts'] += [int(ts_new[0]-1)]
                for j, l in enumerate(var_names):
                    v[l] += [None]
                    v[l+'_diff'] += [(None, None)]

            v['ts'] += [int(ts_new[i]) for i in range(chunk_count_c)]
            for j, l in enumerate(var_names):
                v[l] += [avg_samples[i, j] for i in range(chunk_count_c)]
                v[l+'_diff'] += [(min_samples[i, j], max_samples[i, j]) for i in range(chunk_count_c)]

        else:
            # Insert None in time holes, to show a hole in the plot
            if i != 0:
                v['ts'] += [int(ts[0]-1)]
                for j, l in enumerate(var_names):
                    v[l] += [None]

            v['ts'] += [int(ts[i]) for i in range(sample_count)]
            for j, l in enumerate(var_names):
                v[l] += [data[i, j] for i in range(sample_count)]

    return v


@api_resource('/api/1.0/sensor/data/raw', endpoint='/api/1.0/sensor/data/raw')
class ApiGetSensorData2(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        parser.add_argument('org_id', type=id_argument, required=True, location='args')
        parser.add_argument('project_id', type=id_argument, required=True, location='args')
        parser.add_argument('sensor_id', type=id_argument, required=True, location='args')
        parser.add_argument('window_type', type=str, required=True, location='args')
        parser.add_argument('streams', type=str_array_argument, required=True, location='args')
        parser.add_argument('start_time', type=datetime_argument, required=True, location='args')
        return parser.parse_args()

    @ext_cache.cached(timeout=60*2, query_string=True)
    def get(self):
        """
        Get Raw Sensor Data

        Return unprocessed sensor data from a given sensor
        ---
        tags:
          - Sensor Data
        parameters:
          - name: Auth-Token
            in: header
            schema:
                type: string
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
          - name: window_type
            in: query
            type: string
            default: 'hour'
            required: true
          - name: streams
            in: query
            type: string
            default: 'acc/3ax/4g'
            required: true
          - name: start_time
            in: query
            type: string
            default: '2017-11-07T11:00:00'
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

        sensor = fetch_sensor_from_id(args['sensor_id'], proj)

        if sensor is None:
            return build_response(None, status_code=ApiStatus.STATUS_SENSOR_NOT_FOUND)

        start_time = args['start_time']
        if args['window_type'] == 'hour':
            end_time = start_time + timedelta(hours=1)
        elif args['window_type'] == 'day':
            end_time = start_time + timedelta(days=1)
        else:
            abort(500)

        if len(args['streams']) != 1:
            raise NotImplementedError

        stream_name = args['streams'][0]

        if stream_name == 'acc/3ax/4g':
            var_names = ['x', 'y', 'z']
        elif stream_name in ['cap/stretch/scalar', 'volt/system/mv', 'temp/acc/scalar']:
            var_names = ['v']
        else:
            abort(500)

        extend_sensors_remote_details([sensor])
        data_bundle = fetch_sensor_data_bundle_for_sensor(sensor.remote_details, start_time, end_time, stream_name)

        if args['window_type'] == 'hour':
            values = format_samples(data_bundle, False, var_names)
        else:
            values = format_samples(data_bundle, True, var_names)

        return build_response(
            {
                'data':
                {
                    'sensor_id': id_out(sensor.id),
                    'start_time': args['start_time'].isoformat(),
                    'end_time': end_time.isoformat(),
                    'window_type': args['window_type'],
                    'streams':
                        [
                            {
                                'stream_type': stream_name,
                                'values': values
                            }
                        ]
                }
            }
        )


@api_resource('/api/1.0/sensor/data/derived', endpoint='/api/1.0/sensor/data/derived')
class ApiGetSensorDerivedData(Resource):

    @staticmethod
    def parse_args():
        parser = reqparse.RequestParser()
        parser.add_argument('Auth-Token', location='headers')
        parser.add_argument('org_id', type=id_argument, required=True, location='args')
        parser.add_argument('project_id', type=id_argument, required=True, location='args')
        parser.add_argument('sensor_id', type=id_argument, required=True, location='args')
        parser.add_argument('window_type', type=str, required=True, location='args')
        parser.add_argument('alg_profile', type=str, required=True, default='person/activity', location='args')
        parser.add_argument('patient_profile', type=str, required=True, default='person/default', location='args')
        parser.add_argument('parameters', type=str, required=False, default='', location='args')
        parser.add_argument('start_time', type=datetime_argument, required=True, location='args')
        return parser.parse_args()

    def get(self):
        """
        Get Derived Sensor Data

        Return derived sensor data from a given sensor and algorithm
        ---
        tags:
          - Sensor Data
        parameters:
          - name: Auth-Token
            in: header
            schema:
                type: string
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
          - name: window_type
            in: query
            type: string
            default: 'hour'
            required: true
          - name: alg_profile
            in: query
            type: string
            default: 'person/activity'
            required: true
          - name: patient_profile
            in: query
            type: string
            default: 'person/default'
            required: true
          - name: parameters
            in: query
            type: string
            default: ''
            required: false
          - name: start_time
            in: query
            type: string
            default: '2017-11-07T11:00:00'
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

        # Verify valid Organization and Project

        org, proj = fetch_org_and_project(user, args['org_id'], args['project_id'])

        if org is None:
            return build_response(None, status_code=ApiStatus.STATUS_ORG_NOT_FOUND)

        if proj is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROJECT_NOT_FOUND)

        # Verify valid start_time and derive end_time

        start_time = args['start_time']
        if args['window_type'] == 'hour':
            end_time = start_time + timedelta(hours=1)
        elif args['window_type'] == 'day':
            end_time = start_time + timedelta(days=1)
        else:
            abort(500)

        # Verify valid sensor_id

        sensor = fetch_sensor_from_id(args['sensor_id'], proj)
        if sensor is None:
            return build_response(None, status_code=ApiStatus.STATUS_SENSOR_NOT_FOUND)

        # Verify streams

        alg = Algorithms.get(args['alg_profile'])
        if alg is None:
            abort(500)

        # Verify profile
        alg_profile = AlgProfile.query.filter(AlgProfile.name == args['alg_profile']).first()
        if alg_profile is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROFILE_NOT_FOUND)

        patient_profile = PatientProfile.query.filter(PatientProfile.short_name == args['patient_profile']).first()
        if patient_profile is None:
            return build_response(None, status_code=ApiStatus.STATUS_PROFILE_NOT_FOUND)

        # Fetch the data

        extend_sensors_remote_details([sensor])
        sensor_map = {alg.__place__[0]: sensor.remote_details}

        #categories = [x for x in alg.__output__ if x.endswith('/time')]
        #other = [x for x in alg.__output__ if not x.endswith('/time')]

        if args['window_type'] == 'hour':

            derived = fetch_cached_derived_data_hour(sensor_map, alg_profile, {}, start_time)

            # Resource is not ready yet
            if derived is DataNotReady:
                return build_response(None, status_code=ApiStatus.STATUS_GENERATING_RESOURCE)

            # Copied
            if derived.has_data():  # check for empty data
                derived_window = derived.get_data().derived_window(start_time, end_time)
                ts_window = derived.get_data().ts_window(start_time, end_time)
            else:
                derived_window = []
                ts_window = []

            values = {'ts': [int(x) for x in ts_window],
                      'activity/category/idx': [int(numpy.nonzero(x)[0][0]) for x in derived_window],
                      'activity/step/count': [float(x[7]/10.0) for x in derived_window],
                     }
        elif args['window_type'] == 'day':
            summary = fetch_derived_data_bins(
                sensor_map,
                alg_profile,
                {},
                start_time)

            if summary is DataNotReady:
                return build_response(None, status_code=ApiStatus.STATUS_GENERATING_RESOURCE)

            values = summary

        return build_response(
            {
                'data':
                {
                    'sensor_id': id_out(sensor.id),
                    'start_time': args['start_time'].isoformat(),
                    'end_time': end_time.isoformat(),
                    'window_type': args['window_type'],
                    'streams':
                        [
                            {
                                'alg_profile': alg_profile.name,
                                'values': values,
                                'categories': alg.__output__[:7]
                            }
                        ]
                }
            }
        )
