from models import Session2, TimeSync, SensorRecord2, get_samples, load_all_bindata
from datetime import datetime, timedelta
from types.sensor_data import SensorData2
from types.sensor_data_bundle import SensorDataBundle
from utils import unixts, tx_format
import numpy


def fetch_sessions_in_interval(sensor, start_time, end_time):
    # todo: important! sensor access check
    sessions = Session2.query.filter(Session2.motion_device == sensor) \
        .filter(Session2.start_time < end_time) \
        .filter((Session2.end_time > start_time) | (Session2.end_time == None)) \
        .order_by(Session2.start_time).all()
    return sessions


# Secondary
# New todo: copied from res_samples view
def fetch_records_for_stream(stream, period_start, period_end):
    """
    
    :param stream: 
    :param period_start: 
    :param period_end: 
    :return: [records], epoch
    """

    timestamp = period_start

    # Find time offset
    timesync = TimeSync.query.filter(TimeSync.session_id == stream.session.id).filter(TimeSync.server_time <= timestamp).order_by(TimeSync.server_time.desc()).first()

    print("1", timesync)
    if timesync is None or period_start - timesync.server_time > timedelta(hours=2):
        timesync2 = TimeSync.query.filter(TimeSync.session_id == stream.session.id).filter(TimeSync.server_time > timestamp).order_by(TimeSync.server_time).first()
        print("2", timesync2)
        if timesync2 is not None:
            if timesync is None or period_start - timesync.server_time > timesync2.server_time - period_start:
                timesync = timesync2
    if timesync is None:
        return None, None

    epoch = timesync.server_time - timedelta(seconds=timesync.timestamp_tx*0.01)

    period_start_tx = max(0, (period_start - epoch).total_seconds()*100 - 25*60*100)
    period_end_tx = (period_end - epoch).total_seconds()*100
    return fetch_records_for_stream_tx(stream, period_start_tx, period_end_tx), epoch


def fetch_records_for_stream_tx(stream, start_tx, end_tx):
    records = SensorRecord2.query.filter(SensorRecord2.stream_id == stream.id).filter(SensorRecord2.timestamp_tx > start_tx).filter(SensorRecord2.timestamp_tx < end_tx).order_by(SensorRecord2.timestamp_tx).all()
    load_all_bindata(records)
    return records


# New todo: not really view specific
def _combine_records(records, stream, epoch):
    if len(records) == 0:
        return numpy.array([]), numpy.array([])
    samples = []
    last_record_len = 0
    last_r = None
    consumed = 0
    for r in records:
        if last_r is not None and r.timestamp_tx > last_r.timestamp_tx_end + 10000:
            break
        last_r = r
        consumed += 1
        s = get_samples(r, stream)
        samples.append(s)
        last_record_len = len(s[:, 0])
        # HACK FOR BUFFER OVERRUN
        if len(r.bindata_cached.bin_data) == 65535:
            expected_cnt = int((r.timestamp_tx_end - r.timestamp_tx) / 100 * 90)
            missing_cnt = expected_cnt - len(s)
            if missing_cnt > 0:
                samples.append(numpy.zeros((missing_cnt, 3)))
                last_record_len += missing_cnt

    all_samples = numpy.vstack(samples)
    if len(records) > 1:
        period = ((last_r.timestamp_tx - records[0].timestamp_tx)*10.0)/(len(all_samples[:,0])-last_record_len)
    else:
        period = ((last_r.timestamp_tx_end - records[0].timestamp_tx)*10.0)/(len(all_samples[:,0]))
    ts = (numpy.arange(len(all_samples[:,0]))*period).astype(numpy.int64) + unixts(epoch) + records[0].timestamp_tx * 10
    return ts, all_samples, consumed


def fetch_sensor_data_for_stream(data_bundle, stream, start_time, end_time, window_s):
    """
    
    :param stream: 
    :param start_time: 
    :param end_time: 
    :return: ts(numpy(1)), data(numpy(x,y) int64 ), shape
    """
    # Fetch records in interval here
    records, epoch = fetch_records_for_stream(stream, start_time, end_time)

    if records is None:
        return

    consumed = 0
    while consumed < len(records):
        ts, data, cons = _combine_records(records[consumed:], stream, epoch)
        print(consumed, cons, len(records))
        consumed += cons
        select = (ts > unixts(start_time)-window_s*1000) & (ts < unixts(end_time)+window_s*1000)
        data = data[select]
        ts = ts[select].astype(numpy.int64)
        sensor_data = SensorData2(start_ts=ts[0], end_ts=ts[-1], ts=ts,
                                  stream_type=stream.stream_type, data=data)
        print(datetime.utcfromtimestamp(ts[0]/1000).isoformat(), datetime.utcfromtimestamp(ts[-1]/1000).isoformat())
        data_bundle.add(sensor_data)


# Primary
def fetch_sensor_data_bundle_for_sensor(sensor, start_time, end_time, stream_type, window_s=0):
    """
    
    :param sensor: 
    :param start_time: 
    :param end_time:
    :param stream_type:
    :param window_s: 
    :return: SensorDataBundle
    """
    # Find all sessions in interval
    data_bundle = SensorDataBundle(start_time, end_time, stream_type)
    sessions = fetch_sessions_in_interval(sensor, start_time, end_time)
    for s in sessions:
        for stream in s.streams:
            if stream.stream_type == stream_type:
                fetch_sensor_data_for_stream(data_bundle, stream, start_time, end_time, window_s)

    return data_bundle
