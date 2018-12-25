from datetime import datetime
import numpy
from types.sensor_data import window, SensorData2
from utils import unixts


class DerivedData():
    def __init__(self, derived_type, data, source, ts):
        self.start_ts = source.start_ts
        self.end_ts = source.end_ts
        self.source = source
        self.derived_type = derived_type
        self.data = data
        self.ts = ts
        self._times = None

    def __getstate__(self):
        """Return state values to be pickled."""
        return self.start_ts, self.end_ts, self.derived_type, self.data, self.ts

    def __setstate__(self, state):
        """Restore state from the unpickled state values."""
        self.start_ts, self.end_ts, self.derived_type, self.data, self.ts = state
        self.source = None
        self._times = None

    def timed_samples(self):
        return numpy.vstack((self.ts, self.data.transpose())).transpose()

    def derived_window(self, start, end):
        start_ts = unixts(start)
        end_ts = unixts(end)
        first, last = window(self.ts, start_ts, end_ts)
        return self.data[first:last, :]

    def categories_window(self, start, end):
        start_ts = unixts(start)
        end_ts = unixts(end)
        first, last = window(self.ts, start_ts, end_ts)
        return self.data[first:last, 0].astype(dtype=numpy.int)

    def meta_window(self, start, end):
        start_ts = unixts(start)
        end_ts = unixts(end)
        first, last = window(self.ts, start_ts, end_ts)
        return self.data[first:last, 1].astype(dtype=numpy.double)

    def ts_window(self, start, end):
        start_ts = unixts(start)
        end_ts = unixts(end)
        first, last = window(self.ts, start_ts, end_ts)
        return self.ts[first:last].astype(dtype=numpy.int)

    def windowed_view(self, start, end):
        start_ts = unixts(start)
        end_ts = unixts(end)
        first, last = window(self.ts, start_ts, end_ts)
        return DerivedData(derived_type=self.derived_type,
                           data=self.data[first:last, :],
                           source = self.source.windowed_view(start, end) if self.source is not None else SensorData2(start_ts, end_ts, None, None, None),
                           ts=self.ts[first:last])

    def total_ts_len_window(self, start, end):
        start_ = max(unixts(start), self.start_ts)
        end_ = max(unixts(end), self.end_ts)

    def sample_ts(self):
        return (self.ts[-1] - self.ts[0]) / len(self.data)

    def has_data(self):
        """Returns true if this object contains any samples"""
        return len(self.data) > 0

    @property
    def start_time(self):
        return datetime.utcfromtimestamp(self.start_ts/1000)

    @property
    def end_time(self):
        return datetime.utcfromtimestamp(self.end_ts/1000)