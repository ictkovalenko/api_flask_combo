import time
from math import floor
import pytz
from datetime import datetime, date, timedelta
from dateutil import parser
import numpy
from flaskapp import client


def ensure_list_like(x):
    if hasattr(x, '__iter__'):
        return x
    else:
        return [x]


def tx_format(tx):
    ts = floor(tx / 100)
    d = floor(ts / 3600 / 24)
    print(d, ts, (ts - d*3600*24))
    h = floor((ts - d*3600*24) / 3600)
    m = floor((ts - d*3600*24 - h*3600) / 60)
    s = floor((ts - d*3600*24 - h*3600 - m*60))
    return "% 2dD.%02dH.%02dM.%02d.%02d" % (d, h, m, s, tx-ts*100)


def unixts(dt):
    """Convert a datetime object to a unix timestamp in ms

        Args:
            dt: datetime object

        Returns:
            unix timestamp in ms
    """
    if dt is None:
        return None
    return int((dt - datetime(1970, 1, 1)).total_seconds() * 1000)


def from_unixts(ts):
    return datetime.utcfromtimestamp(ts/1000)


def parse_date_string(s):
    return parser.parse(s)


def json_isoformat(d):
    if d is None:
        return None
    else:
        return d.isoformat()


def floor_time_to(dt, tstep):
    fts = int(numpy.floor(unixts(dt) / (tstep.total_seconds() * 1000)))
    fts = fts * tstep.total_seconds()
    return datetime.utcfromtimestamp(fts)


def ceil_time_to(dt, tstep):
    cts = int(numpy.ceil(unixts(dt) / (tstep.total_seconds() * 1000)))
    cts = cts * tstep.total_seconds()
    return datetime.utcfromtimestamp(cts)


def datetime_matches(dt, period):
    if period == 'hour':
        return unixts(dt) % 60000 == 0
    else:
        raise NotImplementedError


def floor_datetime(dt, unit):
    if unit == 'day':
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif unit == 'hour':
        return dt.replace(minute=0, second=0, microsecond=0)
    else:
        assert False, "floor_datetime doesnt support %s" % unit


def utc_from_local(dt, tz):
    return tz.localize(dt).astimezone(pytz.utc)


def local_from_utc(dt, tz=pytz.timezone('Europe/Kyiv')):
    return pytz.utc.localize(dt).astimezone(tz)


def utc_start_of_local_today(tz):
    dt_local = datetime.utcnow().astimezone(tz)
    return floor_datetime(dt_local, 'day').astimezone(pytz.utc)


def range_datetime(dt_start, dt_end, delta):
    dt = dt_start
    while dt <= dt_end:
        yield dt
        dt += delta


def time_int_mult(small, large):
    """
    Check if large is an integer multiple of small

    :param small: timedelta with smallest length
    :param large: timedelta with longest length
    :return: True/False
    """
    # NOTE: timedelta.total_seconds() returns float by default
    return (large.total_seconds() / small.total_seconds()).is_integer()


def time_ago(hours=0):
    return datetime.utcnow() - timedelta(hours=hours)


def isoformat_or_none(dt):
    if dt is None:
        return None
    return dt.isoformat()


class Timing:
    def __init__(self):
        self.start = time.time()
        self.steps = []

    def step(self, msg):
        self.steps.append((time.time(), msg))

    def print(self):
        for step in self.steps:
            print("% 10d - % 10d - %s", step[0], step[0], step[1])


def first(v):
    if len(v) == 0:
        return None
    else:
        return v[0]


def send_sns(num, code):
    # Send your sms message.
    client.publish(
        PhoneNumber=num,
        Message=code
    )
