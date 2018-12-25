from datetime import timedelta, datetime
from api.api_json import api_isoformat
from api.helpers import id_out
from flaskapp import app
from math.compress import analyze_compressed
from models import Session2, TimeSync, get_samples, get_bindata, MotionDevice, load_all_bindata
from query.sensordata.sensordata_query import fetch_records_for_stream
from utils import parse_date_string, tx_format
from views.util import text_view, id_encode


@app.route('/internal/records/sensor/<sensor_device_name>')
@text_view
def internal_browse_records_sessions(sensor_device_name):

    def out():
        yield sensor_device_name
        all_sensors = MotionDevice.query.all()
        for d in all_sensors:
            if d.short_name() == sensor_device_name:
                for s in d.sessions:
                    yield "<br>Session\
                     <br>  start:%s\
                     <br>  end:%s\
                     <br>  tame:%s\
                     <br>  id:%d\
                     <br>  <a href='/internal/records/browse/%s/%s'>View</a>\
                     <br>  <a href='/internal/records/export_session/%s'>Export</a>"\
                          % (api_isoformat(s.start_time),
                             api_isoformat(s.end_time),
                             id_out(s.id),
                             s.id,
                             id_encode(s.id), api_isoformat(s.start_time),
                             id_encode(s.id))

    return out()


@app.route('/internal/records/browse/<tame:session_id>/<day>')
@text_view
def browse_session1_raw(session_id, day):

    def out():
        yield "<pre>"
        session = Session2.query.get(session_id)
        expand = True

        if session is None:
            yield "Session %d not found" % session_id
            return

        streams = session.streams

        if day == 'start':
            start = session.start_time
        else:
            start = parse_date_string(day)
        end = start + timedelta(days=1)

        yield "Session Start: " + session.start_time.isoformat()
        yield "Session End:   " + session.end_time.isoformat() if session.end_time else "None"

        yield "Start: " + start.isoformat()
        yield "End:   " + end.isoformat()

        yield "*" * 30

        yield "Timesyncs"
        yield "% 10s % 10s - %10s - %10s" % ("Diff TX", "Abs TX", "Server Time", "Derived Epoch")
        timesyncs = TimeSync.query.filter(TimeSync.session_id==session_id).all()
        prev = 0
        for t in timesyncs:
            if t.server_time < start - timedelta(days=1) or t.server_time > end + timedelta(days=1):
                continue
            epoch = t.server_time - timedelta(milliseconds=t.timestamp_tx * 10)
            yield "% 10d % 10d - %s - %s" % (t.timestamp_tx - prev, t.timestamp_tx, t.server_time.isoformat(), epoch)
            prev = t.timestamp_tx

        for s in streams:
            if s.stream_type != 'acc/3ax/4g':
                continue

            yield "*" * 30
            yield "Stream: " + s.stream_type

            yield "Properties: " + s.properties
            yield "Format: %d" % s.data_format
            yield "Open TX: %s" % tx_format(s.open_record_tx)

            records, _ = fetch_records_for_stream(s, start, end)
            prev = 0
            prev_end = 0
            prev_samples = 0
            avrg = [0,0,0,0,0]
            yield ("% 30s" + "% 15s " * 5) % ("UTC Begin", "TS Begin", "TS End", "TS Len Min", "bin_len", "sample_cnt")
            last_stream_cnt = -1

            load_all_bindata(records)
            for i, r in enumerate(records):
                if last_stream_cnt != -1 and r.stream_cnt_begin != last_stream_cnt:
                    yield " ---- Missing Data %d -> %d" % (last_stream_cnt, r.stream_cnt_begin)
                last_stream_cnt = r.stream_cnt_end + 1
                samples = get_samples(r, s)

                diff = 1.0 * r.timestamp_tx - prev
                diff2 = r.timestamp_tx - prev_end
                #ts = diff / prev_samples
                #if (prev != 0):
                #    avrg[i%5] = ts
                bin_data = get_bindata(r)
                if (r.timestamp_tx - prev) > 0 and prev_samples != 0:
                    freq = prev_samples / ((r.timestamp_tx - prev) / 100.0)
                else:
                    freq = 0
                #yield "% 10d % 10d %d" % (r.timestamp_tx, r.timestamp_tx_end, r.timestamp_tx - prev_end)
                yield ""
                yield "+ % 30s % 15s % 15s % 15.2f % 15d % 15d % 15.2f %d/%d" % (timesyncs[0].tx_to_utc(r.timestamp_tx).isoformat(),
                                                                tx_format(r.timestamp_tx),
                                                                tx_format(r.timestamp_tx_end),
                                                                (r.timestamp_tx_end - r.timestamp_tx) / 6000.0,
                                                                len(bin_data),
                                                                len(samples),
                                                                 freq,
                                                                  r.stream_cnt_begin, r.stream_cnt_end)

                if expand is False:
                    continue

                bin_data = get_bindata(r)
                prev2 = 0
                prev2_samples = 0
                total_samples = 0
                for (tx, sample_cnt, bytes_cnt) in analyze_compressed(bin_data):

                    total_samples += sample_cnt
                    if (tx - prev2) > 0 and prev2_samples != 0:
                        freq = prev2_samples / ((tx - prev2) / 100.0)
                    else:
                        freq = 0
                    prev2 = tx
                    prev2_samples = sample_cnt

                    yield "- % 30s % 15s = Samples: % 6d @ Bytes: % 6d % 12.2f" % (timesyncs[0].tx_to_utc(r.timestamp_tx).isoformat(), tx_format(tx), sample_cnt, bytes_cnt, freq)

                yield "total: " + str(total_samples)

                #yield "% 10d %d % 10d % 10d % 8d % 5d %.2f %.2f" % (diff, diff2, r.timestamp_tx, r.timestamp_tx_end, len(bin_data), len(samples), ts, numpy.sum(avrg)/5)
                prev = r.timestamp_tx
                prev_end = r.timestamp_tx_end
                prev_samples = len(samples)

    return out()
