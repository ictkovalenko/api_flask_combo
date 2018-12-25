import pickle
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from components import internal_cache, db
from flaskapp import app
from math.algorithm.algorithms import Algorithms
from models import SensorAccess, GatewaySensorDiscovered, Session2, TimeSync, MotionDevice
from models.structure.measurement import AlgProfile
from query.deriveddata.derived_data_query import fetch_derived_data_bins, fetch_cached_derived_data_hour
from query.sensordata.sensor_query import extend_sensors_remote_details
from utils import parse_date_string
from views.util import text_view, id_encode


@app.route('/internal/debug/info')
def debug_info():
    return 'SENS backend ' + app.config['DESCRIPTION']


@app.route('/internal/debug/crash')
def view_crash():
    None.non_existing_function()


@app.route('/internal/id/totame/<int:id>')
def internal_id_totame(id):
    return id_encode(id)


@app.route('/internal/id/fromtame/<tame:id>')
def internal_id_fromtame(id):
    return "%d" % id


@app.route('/internal/test_derived/<profile_name>/<int:sensor_id>/<start_time>')
@text_view
def test_derived_data(profile_name, sensor_id, start_time):
    start_time = parse_date_string(start_time)
    profile_name = profile_name.replace('_', '/')

    sensor = SensorAccess.query.get(sensor_id)
    extend_sensors_remote_details([sensor])
    profile = AlgProfile.query.filter(AlgProfile.name == profile_name).first()

    alg = Algorithms.get(profile.algorithm)
    data = fetch_cached_derived_data_hour({alg.__place__[0]: sensor}, profile, {}, start_time)
    pickled_data = pickle.dumps(data)
    print(len(pickled_data))

    def out():
        yield "Sensor %s" % sensor.remote_details.short_name()
        if data is None:
            yield "Analyzing..."
        else:
            for d in data.data:
                d2 = d.windowed_view(start_time, start_time + timedelta(hours=1))
                yield "Data Part"
                yield str(d2.data.shape)
                yield str(d2.timed_samples().shape)
                for t, v in zip(d2.ts, d2.data):
                    yield datetime.utcfromtimestamp(t/1000).isoformat() + " " + str(v)

    return out()


@app.route('/internal/test_derived_bins/<profile_name>/<int:sensor_id>/<start_time>')
@text_view
def test_derived_data_bins(profile_name, sensor_id, start_time):
    start_time = parse_date_string(start_time)
    profile_name = profile_name.replace('_', '/')

    sensor = SensorAccess.query.get(sensor_id)
    profile = AlgProfile.query.filter(AlgProfile.name == profile_name).first()

    data = fetch_derived_data_bins([sensor], profile, start_time, start_time + timedelta(hours=24), bin_width=timedelta(minutes=60))

    def out():
        if data is None:
            yield "Calculating... "
        else:
            for d in data:
                yield datetime.utcfromtimestamp(d['ts']/1000).isoformat() + " " + str(d['summary'])

    return out()


@app.route('/internal/label/get')
def internal_label_get():
    pending = internal_cache.get('pending-labels-0')
    if pending is not None:
        labels = pending.split('$')
        label = labels[0]
        new_labels = "$".join(labels[1:])
        if new_labels != "":
            internal_cache.set('pending-labels-0', new_labels, timeout=60*5)
        else:
            internal_cache.delete('pending-labels-0')
        return label
    else:
        return ""


@app.route('/internal/label/add')
def internal_label_add():
    pending = internal_cache.get('pending-labels-0')
    if pending is not None:
        labels = pending.split('$') + ["TEST"]
    else:
        labels = ["TEST"]

    new_labels = "$".join(labels)
    internal_cache.set('pending-labels-0', new_labels, timeout=60*5)
    return "OK"


@app.route('/internal/sensor/actions/<int:sensor_id>')
@text_view
def internal_sensor_actions(sensor_id):

    def out():
        d = MotionDevice.query.get(sensor_id)

        seen = GatewaySensorDiscovered.query\
            .filter(GatewaySensorDiscovered.sensor_id == sensor_id)\
            .options(joinedload(GatewaySensorDiscovered.scan_report))\
            .options(joinedload(GatewaySensorDiscovered.action_request))\
            .all()

        yield d.mac_string()
        yield "Seen Events"
        yield ""
        #yield "2018-09-13T06:26:34      1       3  None  None/None  0:0:0:0  SENS HUAWEI 07          2.4.2-2"
        yield "          Timestamp  State  Action     Tx     F/L     A:C:I:C                    Gateway    Version"
        for s in seen:
            yield "%s      %d      %2d  %5s  %4s/%4s  %s:%s:%s:%s  %25s    %s" % (s.scan_report.timestamp.isoformat(),
                                   s.sensor_state,
                                   s.action_request.action_type if s.action_request else -1,
                                   str(s.action_request.state_tx) if s.action_request else -1,
                                   str(s.action_request.synced_record_first) if s.action_request else -1,
                                   str(s.action_request.synced_record_last) if s.action_request else -1,
                                   str(s.action_request.status_accepted) if s.action_request else '_',
                                   str(s.action_request.status_connected) if s.action_request else '_',
                                   str(s.action_request.status_interrupted) if s.action_request else '_',
                                   str(s.action_request.status_completed) if s.action_request else '_',
                                   s.scan_report.gateway_device.name,
                                   s.scan_report.gateway_device.version)


        sessions = Session2.query.filter(Session2.motion_device_id == sensor_id).all()
        for s in sessions:
            yield " "
            yield "----- TimeSyncs -----"
            yield "Session " + str(s.start_time) + " " + str(s.end_time)
            yield "          ServerTime          Tx                       Epoch"
            for ts in TimeSync.query.filter(TimeSync.session_id == s.id).all():
                yield "%20s  %10d  %20s" % (ts.server_time, ts.timestamp_tx, ts.server_time - timedelta(milliseconds= ts.timestamp_tx*10))

    return out()
