from datetime import timedelta, datetime
from flask import request, abort
from api.auth import check_auth
from api.helpers import id_argument
from flaskapp import app
from math.algorithm.algorithms import Algorithms
from models.legacy.monitored_user import MonitoredUserGroup
from models.legacy.roi import ROI
from models.structure.measurement import AlgProfile
from query.deriveddata.derived_data_query import fetch_cached_derived_data_hour, fetch_derived_data_hour, \
    fetch_derived_data_bins, DataNotReadyCls
from query.sensordata.sensor_query import fetch_sensor_from_id, extend_sensors_remote_details
from query.sensordata.sensordata_query import fetch_sensor_data_bundle_for_sensor
from query.structure.projects_query import fetch_org_and_project
from utils import ceil_time_to, floor_time_to, parse_date_string
from views.util import text_view, download_view


@app.route('/export/sensor/raw')
@download_view
def export_sensor_raw():
    org_id = id_argument(request.args.get('org_id'))
    project_id = id_argument(request.args.get('project_id'))
    sensor_id = id_argument(request.args.get('sensor_id'))
    start_time = request.args.get('start_time')
    stream_type = request.args.get('stream_type')
    window_type = request.args.get('window_type')

    #
    # Lot of this is the same as @api_resource('/api/1.0/sensor/data/raw') so make sure they are linked
    #

    user = check_auth({'Auth-Token': 'session'})

    org, proj = fetch_org_and_project(user, org_id, project_id)

    if org is None:
        abort(404)

    if proj is None:
        abort(404)

    sensor = fetch_sensor_from_id(sensor_id, proj)

    if sensor is None:
        abort(404)

    start_time = parse_date_string(start_time)
    if window_type == 'hour':
        end_time = start_time + timedelta(hours=1)
    elif window_type == 'day':
        end_time = start_time + timedelta(days=1)
    else:
        abort(404)

    stream_name = stream_type

    if stream_name == 'acc/3ax/4g':
        var_names = ['x', 'y', 'z']
    elif stream_name in ['cap/stretch/scalar', 'volt/system/mv', 'temp/acc/scalar']:
        var_names = ['v']
    else:
        abort(404)

    extend_sensors_remote_details([sensor])
    data_bundle = fetch_sensor_data_bundle_for_sensor(sensor.remote_details, start_time, end_time, stream_name)

    def out():
        yield "utc, unixts, " + ", ".join(var_names)

        if data_bundle.has_data():
            for v in data_bundle.data[0].timed_samples():
                yield "%s, %s, " % (datetime.utcfromtimestamp(v[0]/1000).isoformat(), int(v[0])) + ", ".join([str(x) for x in v[1:]])

    return out(),\
           'text/css; charset=utf-8',\
           'export_%s_%s_%s.csv' % (sensor.remote_details.short_name().replace('.', '_').replace('-', '_'),
                                 start_time.isoformat(),
                                 window_type)

