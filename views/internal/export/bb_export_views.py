import flask
from datetime import timedelta
from dateutil import tz
from flask import request
from flask import make_response, request
from functools import wraps
from sqlalchemy import event
from sqlalchemy.orm import joinedload
from components import db
from flaskapp import app
from math.algorithm.algorithms import Algorithms
from models.legacy.monitored_user import MonitoredUserGroup, MonitoredUser
from models.legacy.roi import ROI
from models.structure.measurement import AlgProfile
from query.deriveddata.derived_data_query import fetch_cached_derived_data_hour, fetch_derived_data_hour, \
    fetch_derived_data_bins, DataNotReadyCls, check_derived_data_bins
from utils import ceil_time_to, floor_time_to, unixts, from_unixts
from views.util import text_view, download_view, DataNotReadyException


def tolocal(utc):
    utc_zoned = utc.replace(tzinfo=tz.gettz('UTC'))
    local_zoned = utc_zoned.astimezone(tz.gettz('Europe/Kyiv'))
    return local_zoned


# wget --content-disposition -i list.txt

@app.route('/internal/export/bb/list')
@text_view
def export_bb_list():
    show = request.args.get('show', 0)

    def out():

        # Find a patient
        group = MonitoredUserGroup.query\
            .options(joinedload(MonitoredUserGroup.monitored_users))\
            .get(64)

        users = [p for p in group.monitored_users if p.name.lower().startswith('kit')]
        users.sort(key=lambda x: int(x.name.split(" ")[1]))

        cnt = 1

        links = []

        for p in users:
            if not p.name.lower().startswith('kit'):
                continue

            n = int(p.name.split(" ")[1])

            if n < 6:
                # kit 1-5 not of interrest
                continue

            if n in [15, 18, 19, 25, 27, 30, 32, 34, 35, 38, 43, 49, 55, 56, 60, 63, 66, 70, 74,
                     78, 80, 82, 90, 91, 95, 109, 119, 121, 122, 123, 124, 137, 138, 133, 143, 144, 145]:
                # filtered kits
                continue

            rois = ROI.query\
                .filter(ROI.monitored_user_id == p.id)\
                .filter(ROI.start_time != Null)\
                .options(joinedload(ROI.sensors))\
                .all()
            if len(rois) != 1:
                #yield "%s skipped - unexpected ROI count %d" % (p.name, len(rois))
                for r in rois:
                    print(r.id, r.start_time, r.end_time)
                continue
            roi = rois[0]

            if len(roi.sensors) != 2:
                #yield "%s skipped - Unexpected sensor count %d" % (p.name, len(roi.sensors))
                continue

            links += ['https://api.loc/internal/export/bb/get?mu_id=%d&per_day=1' % p.id]
            links += ['https://api.loc/internal/export/bb/get?mu_id=%d&per_day=0' % p.id]
            yield ("#%02d - " % cnt) + p.name + " <a href='/internal/export/bb/get?mu_id=%d&per_day=1'>24h</a> <a href='/internal/export/bb/get?mu_id=%d&per_day=0'>15min</a>" % (p.id, p.id) + " " * (10 - len(p.name)) + roi.start_time.isoformat() + "   " + roi.end_time.isoformat()
            cnt += 1

        print("SQL REQUESTS: %d" % flask.g.stats_sql_count)

        for l in links:
            yield l

    return out()


@app.route('/internal/export/bb/get')
@download_view
def export_bb_get():

    mu_id = request.args.get('mu_id', None)
    per_day = request.args.get('per_day', '0') == '1'

    MOBILITY = {5: "H1", 6: "H2", 7: "H3"}

    retur = {'ready': True, 'filename': 'export.csv'}

    # Find a patient
    group = MonitoredUserGroup.query.get(64)

    p = MonitoredUser.query.get(mu_id)

    if p not in group.monitored_users:
        return

    def out(r):

        rois = ROI.query.filter(ROI.monitored_user_id==p.id).filter(ROI.start_time!=None).all()
        if len(rois) != 1:
            return
        roi = rois[0]

        yield "% 30s, % 30s" % ('Name', p.name.lower())
        yield "% 30s, % 30s" % ('Start Time UTC', roi.start_time.isoformat())
        yield "% 30s, % 30s" % ('End Time UTC', roi.end_time.isoformat())
        yield "% 30s, % 30s" % ('Start Time Local', tolocal(roi.start_time).isoformat())
        yield "% 30s, % 30s" % ('End Time Local', tolocal(roi.end_time).isoformat())
        yield "% 30s, % 30s" % ('Mobility', MOBILITY[p.mobility])
        yield ""

        start = floor_time_to(roi.start_time, timedelta(days=1))
        start_q = ceil_time_to(roi.start_time, timedelta(minutes=15))
        end_q = floor_time_to(roi.end_time, timedelta(minutes=15))

        measurement_profile = AlgProfile.query.filter(AlgProfile.name=='person/activity2s').first()

        alg = Algorithms.get(measurement_profile.algorithm)
        fields = alg.__output__

        fmap = {'general/nodata': 'Ingen Data (min)',
                'activity/lying/time': 'Liggende (min)',
                'activity/standing/time': 'Stående (min)',
                'activity/walking/time': 'Gående (min)',
                'activity/other/time': 'Anden bevægelse (min)',
                'activity/elevated_lying/time': 'Liggende Hævet (min)',
                'activity/sitting/time': 'Siddende (min)',
                'activity/sit2stand/count': 'Rejse/Sætte (antal)'
                }

        yield ", ".join(["% 30s" % s for s in ['UTC Time', 'Local Time', 'Unix Timestamp']] + ["% 25s" % s for s in fmap.values()])

        def fmt(k):
            return "%.0f" if k.endswith('count') else "%06.3f"

        ready = True

        for d in range(10):

            day_sum = {k: 0 for k in fmap}

            current = start + timedelta(days=d)
            if current > roi.end_time:
                continue

            sensor_map = {roi.sensors[0].place: roi.sensors[0].motion_device,
                          roi.sensors[1].place: roi.sensors[1].motion_device}

            bins = fetch_derived_data_bins(sensor_map, measurement_profile, {'mobility': p.mobility}, current, hours=24, bins_per_hour=4)
            if isinstance(bins, DataNotReadyCls):
                ready = False
            else:
                for b in bins:

                    utc = from_unixts(b['ts'])
                    if per_day == 0:
                        if utc < start_q or utc > end_q:
                            continue
                        utc_zoned = utc.replace(tzinfo=tz.gettz('UTC'))
                        local_zoned = utc_zoned.astimezone(tz.gettz('Europe/Copenhagen'))

                        ts = "% 30s, % 30s, % 30d, " % (utc.isoformat(), local_zoned.isoformat(), b['ts']/1000)

                        values = ", ".join(["% 25s" % fmt(k) % b['summary'][k] for k in fmap])
                        yield ts + values
                    else:
                        if utc < start_q or utc > end_q:
                            day_sum['general/nodata'] += 15.0
                        else:
                            for k in fmap:
                                day_sum[k] += b['summary'][k]

                if per_day == 1:
                    utc = current
                    local_zoned = tolocal(utc)
                    ts = "% 30s, % 30s, % 30d, " % (utc.isoformat(), local_zoned.isoformat(), unixts(utc) / 1000)
                    values = ", ".join(["% 25s" % fmt(k) % day_sum[k] for k in fmap])
                    yield ts + values

        if ready is False:
            raise DataNotReadyException

    return out(retur),\
           'text/css; charset=utf-8',\
           'export_%s_%s.csv' % (p.name.lower().strip().replace(' ', ''), "24h" if per_day else "15min")
