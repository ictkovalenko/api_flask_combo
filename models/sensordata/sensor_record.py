import uuid
from datetime import datetime, timedelta
import struct
import numpy
from components import db
from math.pack import unpack10bit
from math.compress import decompress

UINT32_STRUCT = struct.Struct('>L')


class SensorBinData(db.Model):
    __tablename__ = "sensor_bindata"
    __bind_key__ = 'sensordata'

    uuid = db.Column(db.BINARY(16), primary_key=True)
    bin_data = db.Column(db.LargeBinary, nullable=False)


class SensorRecord2(db.Model):
    __tablename__ = "sensor_records2"
    __bind_key__ = 'sensordata'

    # Fields
    stream_id = db.Column(db.Integer, db.ForeignKey('streams2.id'), nullable=False, primary_key=True)
    timestamp_tx = db.Column(db.BigInteger, nullable=False, primary_key=True)
    timestamp_tx_end = db.Column(db.BigInteger, nullable=False)
    stream_cnt_begin = db.Column(db.Integer, nullable=False)
    stream_cnt_end = db.Column(db.Integer, nullable=False)
    datastore = db.Column(db.Integer, nullable=False)
    uuid = db.Column(db.BINARY(16), nullable=False)

    DATASTORE_DIRECT = 0  # (Up to 16 bytes)
    DATASTORE_LOCAL = 1
    DATESTORE_S3 = 2

    FORMAT_SINGLE_UINT16 = 0
    FORMAT_LEGACY_3INT12 = 1
    FORMAT_COMPRESS_3INT12 = 2

    bindata_cached = None


def add_bin_data(record, data):
    if record.datastore == 0:
        # Empty
        data_uuid = uuid.uuid4().bytes
        record.bindata_cached = SensorBinData(uuid = data_uuid, bin_data = data)
        record.datastore = 1
        record.uuid = data_uuid
        db.session.add(record.bindata_cached)
    else:
        if record.bindata_cached == None:
            record.bindata_cached = SensorBinData.query.get(record.uuid)
        record.bindata_cached.bin_data += data


def add_records(session, stream, records_to_add, timesync):
    # Lookup previous db record in stream
    if stream.open_record_tx != None:
        record = SensorRecord2.query.filter(SensorRecord2.stream_id == stream.id).filter(SensorRecord2.timestamp_tx == stream.open_record_tx).first()
    else:
        record = None

    for (timestamp_tx, counter, bin_data) in records_to_add:

        # Validate timestamp
        real_ts = timesync.tx_to_utc(timestamp_tx)
        timediff = datetime.utcnow() - real_ts

        if timediff < -timedelta(minutes=5):
            # Timestamp in the future
            raise Exception('SensorRecord ts in future ' + str(real_ts) + ' ' + stream.stream_type + ' ' + str(stream.id))
        if stream.last_record_added_tx != None and stream.last_record_added_tx >= timestamp_tx:
            #print('Record already submitted', stream.stream_type, timestamp_tx)
            continue

        # counter is 8bit and should match last added record, if not a new db record should be created
        expected_last_counter = counter - 1 if counter > 0 else 255
        if record != None and expected_last_counter != record.stream_cnt_end:
            if (counter == 0 and\
                stream.data_format == SensorRecord2.FORMAT_SINGLE_UINT16 \
                    and (timestamp_tx - record.timestamp_tx_end) < 6600): # Backwards compat for creating stream of single meas
                counter = 0 if record.stream_cnt_end == 255 else record.stream_cnt_end + 1
            else:
                #print("** COUNTER", stream.stream_type, expected_last_counter, record.stream_cnt_end)
                record = None
        if record != None and ((timestamp_tx - record.timestamp_tx) > 20*60*100):
            #print("** TIMESTAMP", stream.stream_type, timestamp_tx, record.timestamp_tx, timestamp_tx - record.timestamp_tx)
            record = None
        if record == None:
            #print("** FIRST", stream.stream_type)
            record = SensorRecord2(stream_id = stream.id, timestamp_tx = timestamp_tx, timestamp_tx_end = timestamp_tx,\
                                    stream_cnt_begin = counter, stream_cnt_end = counter, datastore = 0, uuid = bytearray([]))
            db.session.add(record)
        sample_count = 1 # Default
        if stream.data_format == SensorRecord2.FORMAT_LEGACY_3INT12:
            bin_data = UINT32_STRUCT.pack(timestamp_tx) + bytearray([len(bin_data)/4]) + bin_data # prepend length so we can split it
            sample_count = ord(bin_data[0:1])
        elif stream.data_format == SensorRecord2.FORMAT_COMPRESS_3INT12:
            bin_data = bytearray([0xFE, 0x04]) + UINT32_STRUCT.pack(timestamp_tx) + bin_data  # prepend timestamp
            sample_count = len(decompress(bin_data))
        else:
            bin_data = UINT32_STRUCT.pack(timestamp_tx) + bin_data # prepend timestamp
        add_bin_data(record, bin_data)
        rate = stream.get_rate()
        if rate != None:
            record.timestamp_tx_end = timestamp_tx + sample_count*100*rate
        else:
            record.timestamp_tx_end = timestamp_tx
        record.stream_cnt_end = counter
        stream.last_record_added_tx = timestamp_tx
        stream.open_record_tx = record.timestamp_tx


def add_record(session_id, stream_id, timestamp_tx, sync_event_id, stream_counter, bin_data):
    # DB Method
    if SensorRecord2.query.filter(SensorRecord2.stream_id == stream_id).filter(SensorRecord2.timestamp_tx == timestamp_tx).count() == 0:
        s = SensorRecord2(stream_id = stream_id, timestamp_tx = timestamp_tx, sync_event_id = sync_event_id, stream_counter=stream_counter, bin_data = bin_data)
        db.session.add(s)


def get_records(session_id, stream_id, start_tx, end_tx):
    return SensorRecord2.query.filter(SensorRecord2.stream_id == stream_id).filter(SensorRecord2.timestamp_tx > start_tx).filter(SensorRecord2.timestamp_tx < end_tx).order_by(SensorRecord2.timestamp_tx).all()


def get_bindata(record):
    if record.datastore == 0:
        return bytearray([])
    elif record.datastore == 1:
        if record.bindata_cached == None:
            record.bindata_cached = SensorBinData.query.get(record.uuid)
        return record.bindata_cached.bin_data
    else:
        assert(False)


# New
def get_samples(record, stream):
    if stream.stream_type == "acc/3ax/4g" and stream.data_format == SensorRecord2.FORMAT_LEGACY_3INT12:
        bin_data = get_bindata(record)
        parts = []
        i = 0
        while i < len(bin_data):
            i += 4  # timestamp
            l = bin_data[i]*4
            i += 1
            p = bin_data[i:i+l]
            i += l
            a = unpack10bit(p)
            if len(a) == 3:
                b = numpy.zeros([125, 3])
                b[:,0] = a[0]
                b[:,1] = a[1]
                b[:,2] = a[2]-20
                a = b
            else:
                a.shape = (125,3)
                a[:,2] = a[:, 2]-20
            parts.append(a)
        return numpy.vstack(parts)
    elif stream.stream_type == "acc/3ax/4g" and stream.data_format == SensorRecord2.FORMAT_COMPRESS_3INT12:
        bin_data = get_bindata(record)
        parts = []
        i = 0
        st = datetime.utcnow().replace(minute=37, second=30)
        #print("----------------------------------------------")
        #print(st + timedelta(seconds=record.timestamp_tx/100))
        #print(".".join(["%02X" % x for x in bytearray(bin_data)]))
        values = decompress(bytearray(bin_data))
        #print(values.shape)
        #print(len(values))
        return values
    else:
        bin_data = get_bindata(record)
        # (ts, ts, ts, ts, data, data, na, na)
        samples = numpy.frombuffer(bin_data, dtype='>u2')[2::4]
        samples.shape = (samples.shape[0], 1)
        return samples


def load_all_bindata(records):
    local_ids = {}
    for r in records:
        if r.datastore == 1 and r.bindata_cached == None:
            local_ids[r.uuid] = r

    if len(local_ids):
        bindata = SensorBinData.query.filter(SensorBinData.uuid.in_(local_ids.keys())).all()
        for data in bindata:
            local_ids[data.uuid].bindata_cached = data
