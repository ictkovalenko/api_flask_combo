import json
import pickle
from datetime import timedelta, datetime
import time
import lz4.frame
import numpy
from components import db
from flaskapp import app
from math.algorithm.algorithms import AlgorithmMeta, Algorithms, Algorithm
from models import CacheDerivedData
from models.cache.cache_queue_entry import CacheQueueEntry
from query.sensordata.sensor_query import extend_sensors_remote_details
from query.sensordata.sensordata_query import fetch_sensor_data_bundle_for_sensor
from types.derived_data import DerivedData
from types.sensor_data_bundle import SensorDataBundle
from utils import time_int_mult, floor_time_to, ceil_time_to, unixts, floor_datetime, datetime_matches


class DataNotReadyCls:
    pass


DataNotReady = DataNotReadyCls()


def check_cached_derived_data_hour(sensor_map, alg_profile, parameters, start_time):
    """ Top level function for checking if derived data exists in cache.

    params:
        sensor_map  - Dict object [placement -> sensor_device]
        profile     - Patient Profile
        start_time  - datetime object (already padded)
    return:
        DerivedData if available
        None of not yet available
    """

    cache_id = CacheDerivedData.make_cache_id(sensor_map, alg_profile, start_time)
    return CacheDerivedData.query.filter(CacheDerivedData.id == cache_id).count() != 0


def fetch_cached_derived_data_hour(sensor_map, alg_profile, parameters, start_time):
    """ Top level function for getting derived data. Will handle caching.

    params:
        sensor_map  - Dict object [placement -> sensor_device]
        profile     - Patient Profile
        start_time  - datetime object (already padded)
    return:
        DerivedData if available
        None of not yet available
    """

    cache_id = CacheDerivedData.make_cache_id(sensor_map, alg_profile, start_time)
    entry = CacheDerivedData.query.get(cache_id)

    if entry is not None:
        return pickle.loads(lz4.frame.decompress(entry.data))
    else:
        start_time_day = floor_datetime(start_time, 'day')
        cache_q_id = CacheDerivedData.make_cache_id(sensor_map, alg_profile, start_time_day)
        queue_entry = CacheQueueEntry.query.get(cache_q_id)
        if queue_entry is None:
            queue_entry = CacheQueueEntry(id=cache_q_id,
                                          start_time=start_time_day,
                                          sensor_map=CacheDerivedData.sensor_map_string(sensor_map, alg_profile),
                                          measurement_id=None,
                                          alg_profile_id=alg_profile.id,
                                          server=app.config['CACHE_SERVER_ID'],
                                          parameters=json.dumps(parameters),
                                          scheduled=datetime.utcnow())
            db.session.add(queue_entry)
            db.session.commit()
        return DataNotReady


def fetch_derived_data_hour(sensor_device_map, profile, parameters, start_time):
    """
    NOTE: Unless told not to (via the use_cache param), this function will
    ALWAYS attempt to load the data from the cache
    :param session - Session object
    :param alg     - Algorithm object
    :param tart   - datetime object
    :param pad     - timedelta object, how much 'extra' data to load as padding
    :param use_cache   - boolean, whether or not to use the cache
    :return
    """

    alg = Algorithms.get(profile.algorithm)
    assert alg is not None

    if isinstance(sensor_device_map, list):
        sensor_device_map = {x: v for x,v in zip(alg.__place__, sensor_device_map)}

    assert isinstance(sensor_device_map, dict)

    return generate_derived_data(sensor_device_map, profile, parameters, start_time, start_time + timedelta(hours=1))


def generate_derived_data(sensor_device_map, profile, parameters, start_time, end_time):
    """
    params:
        sensor_map  - Dict object [placement -> sensor_device]
        profile     - Patient Profile
        start_time  - datetime object (already padded)
        end_time    - datetime object (already padded)
    return:
        (N x M + 1) numpy array where each of the N rows is a data point with
        the following structure [timestamp, <M outputs from alg...>]
    """

    alg = Algorithms.get(profile.algorithm)

    start_t = time.time()

    if isinstance(sensor_device_map, list):
        sensor_device_map = {x: v for x,v in zip(alg.__place__, sensor_device_map)}

    any_empty = False
    data_map = {}
    for p, sd in sensor_device_map.items():
        sensor_data = fetch_sensor_data_bundle_for_sensor(sd, start_time - timedelta(minutes=5), end_time + timedelta(minutes=5), 'acc/3ax/4g', window_s=90)
        any_empty |= not sensor_data.has_data()
        data_map[p] = sensor_data

    #print("+++ data in %f" % (time.time() - start_t))

    if len(data_map) == 0 or any_empty:
        return SensorDataBundle(start_time=start_time, end_time=end_time, stream_type='derived')
    elif len(data_map) == 1:
        return alg.analyse_data(data_map, parameters=parameters)
    elif len(data_map) == 2:
        return alg.analyse_data(data_map, parameters=parameters)
    else:
        assert(len(data_map) <= 2)


def check_derived_data_bins(sensor_map, profile, parameters, start_time, hours=24, bins_per_hour=4, override_cache=False):

    hour = timedelta(hours=1)

    alg = alg = Algorithms.get(profile.algorithm)

    fudge_factor = 15.0/60.0 # Correct up to 15 seconds
    bw_mins = 60.0 / 4
    bin_width = timedelta(minutes=bw_mins)
    if not datetime_matches(start_time, 'hour'):
        raise Exception("Invalid start_time")
    hour_end = start_time + timedelta(hours=hours)
    hour_cnt = start_time
    out = [] # {timestamp: , cat: }
    notReady = False
    while hour_cnt < hour_end:
        has_data = check_cached_derived_data_hour(sensor_map, profile, parameters, hour_cnt)
        if not has_data:
            return False
    return True


def fetch_derived_data_bins(sensor_map, alg_profile, parameters, start_time, hours=24, bins_per_hour=4, override_cache=False):
    """
    params:
        sensors:
        profile:
        start:
        end:
        bin_width:
    return:
    """
    hour = timedelta(hours=1)

    alg = Algorithms.get(alg_profile.algorithm)

    fudge_factor = 15.0/60.0 # Correct up to 15 seconds
    bw_mins = 60.0 / 4
    bin_width = timedelta(minutes=bw_mins)
    if not datetime_matches(start_time, 'hour'):
        raise Exception("Invalid start_time")
    hour_end = start_time + timedelta(hours=hours)
    hour_cnt = start_time
    out = [] # {timestamp: , cat: }
    notReady = False
    while hour_cnt < hour_end:
        if override_cache:
            derived_data = fetch_derived_data_hour(sensor_map, alg_profile, parameters, hour_cnt)
        else:
            derived_data = fetch_cached_derived_data_hour(sensor_map, alg_profile, parameters, hour_cnt)
        if derived_data is DataNotReady:
            notReady = True
            hour_cnt += hour
            continue
        delta = timedelta(0)
        while delta < hour:
            data = derived_data.get_data()

            sum = 0
            values = {}
            if data.has_data():
                window_derived = derived_data.get_data().derived_window(
                    hour_cnt + delta, hour_cnt + delta + bin_width)
                summed = numpy.sum(window_derived, axis=0)
                #print(hour_cnt + delta, summed)

                for i, typ in enumerate(alg.__output__):
                    if typ.endswith('/time'):
                        values[typ] = summed[i] * derived_data.get_data().sample_ts() / 60000.0
                        sum += values[typ]
                    elif typ.endswith('/count'):
                        values[typ] = summed[i] / 10.0
                    else:
                        values[typ] = summed[i] * 1.0
            else:
                for typ in alg.__output__:
                    values[typ] = 0.0
            values['general/nodata'] = numpy.max([bw_mins - sum, 0])
            # Sometimes precision errors causes the sum to be slightly
            # less- or greater than the bin width. In this case, we adjust the
            # values so they sum to exactly bin width minutes.

            if values['general/nodata'] < fudge_factor or sum > bw_mins:
                values['general/nodata'] = 0.0
                for typ in alg.__output__:
                    if typ.endswith('/time'):
                        values[typ] *= bw_mins / sum

            for k, v in values.items():
                values[k] = numpy.round(v, 3)

            """
            if 8 < ((hour_cnt - hour_start).seconds / 3600) < 18 and 'activity/lying/time' in values:
                values['activity/elevated_lying/time'] = values['activity/lying/time'] * 0.05
                values['activity/sitting/time'] = values['activity/lying/time'] * 0.25
                values['activity/lying/time'] = values['activity/lying/time'] * 0.70
            """
            out.append({'ts': unixts(hour_cnt + delta),
                        'summary': values
                        })
            delta += bin_width
        hour_cnt += hour
    return out if not notReady else DataNotReady


def get_algorithm(mprofile):
    if mprofile.algorithm == 'person/activity':
        return Algorithms.get('person/activity')
    if mprofile.algorithm == 'person/activity2s':
        return Algorithms.get('person/activity2s')
    else:
        return None
