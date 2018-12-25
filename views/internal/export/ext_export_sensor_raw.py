from time import time
import numpy
from io import BytesIO
from datetime import timedelta
from flask import request, abort
from api.helpers import id_argument
from flaskapp import app
from models import MotionDevice
from query.sensordata.sensordata_query import fetch_sensor_data_bundle_for_sensor
from utils import parse_date_string
from views.util import download_view


@app.route('/internal/export/raw')
@download_view
def internal_export_sensor_raw():
    sensor_name = request.args.get('sensor_name', None)
    access_key = request.args.get('key', None)
    start_time_str = request.args.get('start_time', None)

    sensor = None
    for s in MotionDevice.query.all():
        if s.terminated != 1 and s.short_name().replace(":", ".") == sensor_name:
            sensor = s
            break

    if sensor is None or start_time_str is None:
        print(sensor, start_time_str)
        abort(500)

    start_time = parse_date_string(start_time_str)
    end_time = start_time + timedelta(hours=1)

    data_bundle = fetch_sensor_data_bundle_for_sensor(sensor, start_time - timedelta(minutes=5),
                                                      end_time + timedelta(minutes=5), 'acc/3ax/4g', window_s=90)

    for sensor_data in data_bundle:
        combined = numpy.hstack((sensor_data.ts.reshape(-1, 1), sensor_data.data))
        title = "Accelerometer"
        print(time())
        outfile = BytesIO()
        print(time())
        header = 'x-axis; y-axis; z-axis; length; angle'
        numpy.savetxt(outfile, combined, header='header')
        print(time())
        return outfile.getvalue().decode("utf-8"), \
                   'text/css; charset=utf-8', \
                   'export_%s_%s.npy' % (sensor.short_name().replace('.', '_').replace('-', '_'),
                                         start_time.isoformat())
