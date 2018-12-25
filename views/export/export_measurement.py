from datetime import timedelta
from flask import request
from flaskapp import app
from math.algorithm.algorithms import Algorithms
from models.legacy.monitored_user import MonitoredUserGroup
from models.legacy.roi import ROI
from models.structure.measurement import AlgProfile
from query.deriveddata.derived_data_query import fetch_cached_derived_data_hour, fetch_derived_data_hour, \
    fetch_derived_data_bins, DataNotReadyCls
from utils import ceil_time_to, floor_time_to
from views.util import text_view


@app.route('/export/measurement')
def export_measurement():

    # todo: check session
    proj_id = request.args.get("proj_id")

    MOBILITY = {5: "H1", 6: "H2", 7: "H3"}

    def out():

        # Find a patient
        group = MonitoredUserGroup.query.get(64)
        print(group)
        yield "Exporting Group: " + group.name

        for p in [group.monitored_users[10]]:
            if not p.name.lower().startswith('kit'):
                continue

            rois = ROI.query.filter(ROI.monitored_user_id==p.id).filter(ROI.start_time!=None).all()
            if len(rois) != 1:
                yield "%s skipped" % p.name
                for r in rois:
                    print(r.id, r.start_time, r.end_time)
                continue
            roi = rois[0]

            yield p.name + " " * (10 - len(p.name)) + roi.start_time.isoformat() + "   " + roi.end_time.isoformat()

            yield "Mobility: " + str(p.mobility) + " " + MOBILITY[p.mobility]
            yield "ROI: " + roi.start_time.isoformat()
            yield "ROI: " + roi.end_time.isoformat()

            yield "TODO: pin to hour"
            start_ = floor_time_to(roi.start_time, timedelta(hours=1))

            measurement_profile = AlgProfile.query.filter(AlgProfile.name == 'person/activity2s').first()

            for h in range(1):
                start = start_ + timedelta(hours=h)
                yield "Analyzing " + start.isoformat()

                sensor_map = {roi.sensors[0].place: roi.sensors[0].motion_device,
                              roi.sensors[1].place: roi.sensors[1].motion_device}

                #d = fetch_derived_data_hour(sensor_map, profile, profile.parameters, start)
                #print("Derived", d)
                #print("Derived", d.data)
                #print("Derived", d.data[0].timed_samples())
                bins = fetch_derived_data_bins(sensor_map, measurement_profile, {'mobility': p.mobility}, start, hours=24, bins_per_hour=4)
                if isinstance(bins, DataNotReadyCls):
                    yield ".. analyzing"
                else:
                    print(bins)

    return out()
