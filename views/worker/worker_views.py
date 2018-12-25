import hashlib
import pickle
from datetime import timedelta, datetime
import time
from components import db
from flaskapp import app
from models import CacheQueueEntry, CacheDerivedData, MotionDevice
from models.structure.measurement import AlgProfile
from query.deriveddata.derived_data_query import fetch_derived_data_hour
from views.util import text_view
import lz4.frame


@app.route('/internal/worker/derived')
def view_worker_derived():

    queue_entry = CacheQueueEntry.query.filter(CacheQueueEntry.server==app.config['CACHE_SERVER_ID']).first()

    if queue_entry is None:
        return '<html><head><meta http-equiv="refresh" content="' \
               + str(15) \
               + '"></head>' \
               + '<body><pre>Queue Empty</pre></body></html>'

    alg_profile = AlgProfile.query.get(queue_entry.alg_profile_id)
    sensor_device_list = [MotionDevice.query.get(int(sensor_id)) for sensor_id in queue_entry.sensor_map.split(":")]
    sensor_device_map = {p: sensor_device_list[i] for i, p in enumerate(alg_profile.alg().__place__) if i < len(sensor_device_list)}

    now = datetime.utcnow()

    for h in range(24):
        start = time.time()

        start_hour = queue_entry.start_time + timedelta(hours=h)
        cache_id = CacheDerivedData.make_cache_id(sensor_device_map, alg_profile, start_hour)
        cached_entry = CacheDerivedData.query.get(cache_id)
        if cached_entry is not None:
            if not cached_entry.invalidated and cached_entry.timeout > now:
                continue

        #rint("Analyzing %s" % start_hour.isoformat())
        data = fetch_derived_data_hour(sensor_device_map, alg_profile, queue_entry.parameters_json(), start_hour)

        #rint(" ... fetched in %f" % (time.time() - start))

        pickled_data = pickle.dumps(data)
        compressed_data = lz4.frame.compress(pickled_data)
        #rint("Size %d %d" % (len(pickled_data), len(compressed_data)))

        cache_data = compressed_data

        #rint(" ... compressed in %f" % (time.time() - start))

        if cached_entry is None:
            cached_entry = CacheDerivedData(id=cache_id,
                                            start_time=start_hour,
                                            sensor_map=queue_entry.sensor_map,
                                            measurement_id=queue_entry.measurement_id,
                                            alg_profile_id=queue_entry.alg_profile_id,
                                            parameter_hash=hashlib.md5(queue_entry.parameters.encode('utf-8')).hexdigest(),
                                            server=app.config['CACHE_SERVER_ID'],
                                            timestamp=now,
                                            timeout=now+timedelta(days=14),
                                            data=cache_data)
            db.session.add(cached_entry)
        else:
            # Update invalidated entry
            cached_entry.timestamp = now
            cached_entry.timeout = now + timedelta(days=14)
            cached_entry.invalidated = False
            cached_entry.data = cache_data

        #rint(" ... added in %f" % (time.time() - start))

    db.session.delete(queue_entry)
    db.session.commit()

    left = CacheQueueEntry.query.count()

    refresh_s = 15 if left == 0 else 1

    return '<html><head><meta http-equiv="refresh" content="'\
           + str(refresh_s)\
           + '"></head>'\
           + '<body><pre>OK - %d pending</pre></body></html>' % left


@app.route('/internal/worker/status')
@text_view
def view_worker_status():
    return ["%d cache entries" % CacheQueueEntry.query.filter(CacheQueueEntry.server==app.config['CACHE_SERVER_ID']).count()]


@app.route('/internal/worker/clear')
@text_view
def view_worker_clear():
    CacheQueueEntry.query.filter(CacheQueueEntry.server==app.config['CACHE_SERVER_ID']).delete()
    db.session.commit()
    return ["OK"]
