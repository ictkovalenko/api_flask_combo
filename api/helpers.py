import base64
from http import HTTPStatus
from api.error_codes import ApiStatus
from flaskapp import api
from components import obscure
import json
from flask import Response
from utils import parse_date_string, floor_datetime


def api_resource(*urls, **kwargs):
    def decorator(cls):
        api.add_resource(cls, *urls, **kwargs)
        return cls
    return decorator


def build_response(value, status_code = 0):
    j = json.dumps({'status_code': status_code,
                    'status_msg': ApiStatus.msg(status_code),
                    'value': value},
                   separators=(',', ':'))
    return Response(j, mimetype='application/json', status=HTTPStatus.OK if status_code == 0 else HTTPStatus.NOT_ACCEPTABLE)


def build_parameter_error_respose(e):
    j = json.dumps({'status_code': ApiStatus.STATUS_INVALID_PARAMETER,
                    'status_msg': e.data,
                    'value': None},
                   separators=(',', ':'))
    return Response(j, mimetype='application/json', status=HTTPStatus.BAD_REQUEST)


def id_out(num_id):
    return obscure.encode_tame(num_id)


def id_encoded(num_id):
    return obscure.encode_tame(num_id)


def id_array_argument(val):
    return [obscure.decode_tame(s) for s in str_array_argument(val)]


def id_argument(val):
    return obscure.decode_tame(val)


def str_array_argument(val):
    return val.split(',')


def bindata_argument(val):
    data = base64.b64decode(val)
    return data


def datetime_argument(value):
    return parse_date_string(value)


def datenotz_argument(value):
    date = parse_date_string(value)
    if date == floor_datetime(date, 'day') == date:
        return date
    else:
        raise "NOTZ DATE"


default_help = 'Missing'
