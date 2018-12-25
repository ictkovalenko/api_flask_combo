import numpy
from datetime import datetime
from utils import unixts


def window(ts, start_ts, end_ts):
    if len(ts) == 0:
        return 0, 0
    first = numpy.argmax(ts > start_ts)
    last = numpy.argmax(ts > end_ts)
    if first == 0 and ts[-1] < start_ts:
        first = len(ts)-1
    if last == 0 and ts[-1] < end_ts:
        last = len(ts)-1
    return first, last



class SensorData2(object):
    def __init__(self, start_ts, end_ts, ts, stream_type, data):
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.ts = ts
        self.stream_type = stream_type
        self.data = data
        self._samples = None
        self._times = None

    def __setattr__(self, key, value):
        # Since we cache some results, we need to invalidate these caches if
        # the underlying values are changed
        if key == 'data':
            # Data has been updated, clear _samples cache
            self._samples = None
        super(SensorData2, self).__setattr__(key, value)

    def __getstate__(self):
        """Return state values to be pickled."""
        return self.start_ts, self.end_ts, self.ts, self.stream_type, self.data

    def __setstate__(self, state):
        """Restore state from the unpickled state values."""
        self.start_ts, self.end_ts, self.ts, self.stream_type, self.data = state

    def samples(self):
        if self._samples is None:
            if self.stream_type == 'acc/3ax/4g':
                self._samples = self.data.astype(numpy.float64) * 4.0 / 500.0
            elif self.stream_type == 'temp/acc/scalar':
                self._samples = self.data.astype(numpy.float64) / 10.0
            elif self.stream_type == 'volt/system/mv':
                self._samples = self.data.astype(numpy.float64) / 1000.0
            elif self.stream_type == 'cap/stretch/scalar':
                self._samples = self.data.astype(numpy.float64) * 5.0
            else:
                self._samples = self.data.astype(numpy.float64)
        return self._samples

    def timed_samples(self):
        print(self.ts.shape, self.data.shape, self.samples().shape)
        return numpy.vstack((self.ts, self.samples().transpose())).transpose()

    def windowed_view(self, start, end):
        if not self.has_data():
            return self
        start_ts = unixts(start)
        end_ts = unixts(end)
        first, last = window(self.ts, start_ts, end_ts)
        return SensorData2(start_ts=self.ts[first],
                           end_ts=self.ts[last],
                           ts=self.ts[first:last],
                           stream_type=self.stream_type,
                           data=self.data[first:last, :])

    def chunked_view(self, sample_count):
        skip_count = len(self.data) % sample_count
        new_view = self.data.view()[0:len(self.data)-skip_count]
        new_shape = (-1, sample_count, self.data.shape[1])
        new_view.shape = new_shape
        return SensorData2(start_ts=self.start_ts,
                           end_ts=self.end_ts,
                           ts=self.ts[0:len(self.ts)-skip_count:sample_count],
                           stream_type=self.stream_type,
                           data=new_view)

    def continous_view(self):
        new_view = self.data.view()
        new_view.shape = (-1, self.data.shape[-1])
        new_ts = self._calc_ts(new_view.shape[0], self.start_ts, self.end_ts)
        return SensorData2(start_ts=self.start_ts,
                           end_ts=self.end_ts,
                           ts=new_ts,
                           stream_type=self.stream_type,
                           data=new_view)

    @property
    def start_time(self):
        return datetime.utcfromtimestamp(self.start_ts/1000)

    @property
    def end_time(self):
        return datetime.utcfromtimestamp(self.end_ts/1000)

    @property
    def is_chunked(self):
        return len(self.data.shape) >= 3

    def chunk_count(self):
        """
        Returns the amount of chunks the data has been slit into

        NOTE: If this is not a chunked view, then this function will return 1
        """
        if not self.is_chunked:
            return 1
        else:
            return self.data.shape[0]

    def has_data(self):
        """Returns true if this object contains any samples"""
        return len(self.data) > 0

    def sample_count(self):
        """Returns the total amount of samples this object contains"""
        last_axis = len(self.data.shape) - 1
        return self.data.size / self.data.shape[last_axis]

    @classmethod
    def empty(cls, stream_type):
        return SensorData2(0, 0, numpy.empty([0]), stream_type, numpy.empty([0, 1]))

    @classmethod
    def from_continous(cls, start_ts, end_ts, stream_type, data):
        ts = cls._calc_ts(len(data), start_ts, end_ts)
        return SensorData2(start_ts, end_ts, ts, stream_type, data)

    @classmethod
    def _calc_ts(cls, dlen, start_ts, end_ts):
        return numpy.arange(dlen, dtype=numpy.double) / \
               dlen * (end_ts - start_ts) + start_ts
