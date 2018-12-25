import numpy as np
import numpy
import scipy.signal as sig
import time
from numpy.fft import rfftfreq
from math.algorithm.utils import get_xyz, OVER_SAMPLES
from types.derived_data import DerivedData
from types.sensor_data_bundle import SensorDataBundle
from .lowpass_filter import LowpassFilter


class AlgorithmMeta:
    pass


# local function temp
def chunk_window(data, idx, width):
    start = max(0, idx - width)
    end = min(len(data) - 1, idx + width)
    return data[start:end + 1]


# Return indexes of where an array crosses a certain limit (index before)
def crossing(data, limit=0.0):
    signs = np.sign(data - limit)
    signs[signs>-1] = 1
    pos = signs.copy()
    pos[signs<0] = 0
    neg = (signs.copy())*-1
    neg[signs>0] = 0
    down = neg[1:] * pos[0:-1]
    up = pos[1:] * neg[0:-1]
    idx = np.arange(len(down), dtype=np.int64)
    return idx[up>0.5], idx[down>0.5]


# http://stackoverflow.com/questions/23289976/how-to-find-zero-crossings-with-hysteresis
def hyst(x, th_lo, th_hi, initial = False):
    hi = x >= th_hi
    lo_or_hi = (x <= th_lo) | hi
    ind = np.nonzero(lo_or_hi)[0]
    if not ind.size: # prevent index error if ind is empty
        return np.zeros_like(x, dtype=bool) | initial
    cnt = np.cumsum(lo_or_hi) # from 0 to len(x)
    return np.where(cnt, hi[ind[cnt-1]], initial)


# Return indexes of where an array crosses a certain limit with hysteresis(index before)
def hyst_crossing(data, limit_low, limit_high):
    h = hyst(data, limit_low, limit_high)*1
    df = np.diff(h)
    idx = np.arange(len(df), dtype=np.int64)
    return idx[df<0], idx[df>00]


class Algorithm:
    @classmethod
    def is_categorizer(cls):
        return cls.__type__ == 'categorizer'

    @classmethod
    def is_for_samples(cls):
        return cls.__type__ == 'samples'

    @classmethod
    def is_for_chunk(cls):
        return cls.__type__ == 'chunk'

    @classmethod
    def categoriy_ids(cls):
        return cls.__categories__.keys() + [100]

    @classmethod
    def analyse_data(cls, data_map, parameters):
        start_t = time.time()

        if len(data_map) != len(cls.__place__) and len(data_map) != 1:
            assert False, "Incorrect number of places"

        if cls.is_categorizer():
            derived_data = SensorDataBundle(start_time=None, end_time=None, stream_type='derived')
            # todo: this should be a little smarter to merge multiple sessions
            chunked_data = {}
            for place, sensordata in data_map.items():
                print("SENSORDATA", place, sensordata)
                d = sensordata.data[0]
                print("DATA", d)
                chunked_d = d.chunked_view(64)
                chunked_data[place] = chunked_d
            res = cls.analyse_data_chunks(chunked_data, parameters=parameters)
            assert res.dtype == numpy.int32, "Type was %s" % str(res.dtype)
            derived_data.add(DerivedData(derived_type=cls.__output__, data=res, source=d, ts=chunked_data['person/thigh'].ts))
            # rint("++ analyzed in %f" % (time.time() - start_t))
            return derived_data
        else:
            assert False, "Not Implemented"

    class ParametersDefault:
        STANDING_ANGLE_MIN = 0.35
        STANDING_ANGLE_MAX = 0.55
        STANDING_ANGLE_THRESHOLD = 0.75
        WALKING_ANGLE_THRESHOLD = 0.85
        UP_DOWN_WINDOW_SIZE = 1
        UP_DOWN_THRESHOLD = 2
        WALKING_MAX_FREQ = 2.0
        CYCLE_WALK_FACTOR = 0.7 # Below this is cycling
        CYCLE_MIN_FREQ = 0.2
        RESTING_AMPLITUDE_THRESHOLD = 0.05
        OTHER_AMPLITUDE_THRESHOLD = 0.05
        FFT_LOW_FREQUENCY_DISCARD_COUNT = 1
        POST_FILTER_ITERATIONS = 2
        RUNNING_MIN_AMPLITUDE = 0.4

    class ParametersMobilityFull(ParametersDefault):
        RESTING_AMPLITUDE_THRESHOLD = 0.05
        FFT_LOW_FREQUENCY_DISCARD_COUNT = 4
        POST_FILTER_ITERATIONS = 1
        CYCLE_WALK_FACTOR = 0.9
        CYCLE_MIN_FREQ = 0.3

    class ParametersMobilityCatA(ParametersDefault):
        RESTING_AMPLITUDE_THRESHOLD = 0.04
        FFT_LOW_FREQUENCY_DISCARD_COUNT = 1
        POST_FILTER_ITERATIONS = 1
        CYCLE_WALK_FACTOR = 0.7
        CYCLE_MIN_FREQ = 0.3

    class ParametersMobilityCatB(ParametersDefault):
        RESTING_AMPLITUDE_THRESHOLD = 0.03
        FFT_LOW_FREQUENCY_DISCARD_COUNT = 1

    class ParametersMobilityCatC(ParametersDefault):
        RESTING_AMPLITUDE_THRESHOLD = 0.05
        FFT_LOW_FREQUENCY_DISCARD_COUNT = 1


class Algorithms:
    _list = {}

    @classmethod
    def get(cls, algname):
        """
        Returns the algorithm class corresponding to algname,
        or None if no such algorithm has been attached
        """
        return cls._list[algname] if algname in cls._list else None

    @classmethod
    def attach(cls, algorithm):
        cls._list[algorithm.__algname__] = algorithm


class RawXYZ(Algorithm):
    __algname__ = "xyz"
    __output__ = ['x','y','z']
    __type__ = 'samples'
    __input__ = 'accelerometer'
    __min__ = -2
    __max__ = 2

    @staticmethod
    def analyse_data_low(sensor_data, idx=0):
        assert(len(sensor_data.data.shape) == 3) # required for 'chunk' type
        x, y, z, _ = get_xyz(sensor_data)
        return np.vstack((x[idx,:].transpose(), y[idx,:].transpose(), z[idx,:].transpose()))


class SmoothAngle(Algorithm):
    __algname__ = "angle"
    __output__ = ['x', 'a']
    __type__ = 'samples'
    __input__ = 'accelerometer'
    __min__ = -2
    __max__ = 2

    @staticmethod
    def analyse_data_low(sensor_data, idx=0):
        assert(len(sensor_data.data.shape) == 3) # required for 'chunk' type
        smoothed = SmoothXYZ.analyse_data_low(sensor_data, idx)
        x = np.squeeze(smoothed[0,:])
        a = np.squeeze(np.arcsin(-x))
        return np.vstack((x, a))


class SmoothXYZ(Algorithm):
    __algname__ = "xyz_low"
    __output__ = ['x','y','z']
    __type__ = 'samples'
    __input__ = 'accelerometer'
    __min__ = -2
    __max__ = 2

    @staticmethod
    def analyse_data_low(sensor_data, idx=0):
        assert(len(sensor_data.data.shape) == 3) # required for 'chunk' type
        x, y, z, _ = get_xyz(sensor_data)
        chunk_sc = sensor_data.sample_count() / sensor_data.chunk_count()
        lp = LowpassFilter(12.5, 0.5)

        for i in [x, y, z]:
            all_view = i.view()
            all_view.shape = (-1, 1)
            all_view = np.squeeze(all_view)
            lp_data = lp.filter(all_view)
            all_view[:] = lp_data
        return np.vstack((x[idx,:].transpose(), y[idx,:].transpose(), z[idx,:].transpose()))


class SampleFFT(Algorithm):
    __algname__ = "fft"
    __output__ = ['x','y','z', 'l']
    __type__ = 'samples'
    __input__ = 'accelerometer'
    __min__ = 0
    __max__ = 1

    @staticmethod
    def analyse_data_low(sensor_data, idx=0):
        assert(len(sensor_data.data.shape) == 3) # required for 'chunk' type
        chunk_sc = sensor_data.sample_count() / sensor_data.chunk_count()
        x, y, z, _ = get_xyz(sensor_data)
        x_fft = np.fft.rfft(x, axis=OVER_SAMPLES)
        y_fft = np.fft.rfft(y, axis=OVER_SAMPLES)
        z_fft = np.fft.rfft(z, axis=OVER_SAMPLES)
        x_fft[idx,0] = 0
        y_fft[idx,0] = 0
        z_fft[idx,0] = 0
        l_fft = np.sqrt( np.sum(np.absolute(i)*np.absolute(i) for i in [x_fft, y_fft, z_fft]) )
        return np.absolute(np.vstack((x_fft[idx,:].transpose(), y_fft[idx,:].transpose(), z_fft[idx,:].transpose(), l_fft[idx,:].transpose())))/chunk_sc


class ActivityT1(Algorithm):
    __algname__ = "activity_t1"
    __output__ = ['peakl']
    __type__ = 'chunk'
    __input__ = 'accelerometer'
    __min__ = 0
    __max__ = 5

    @staticmethod
    def analyse_data_low(sensor_data):
        assert(len(sensor_data.data.shape) == 3) # required for 'chunk' type
        x, y, z, _ = get_xyz(sensor_data)
        # todo: force chunk
        l = x*x + y*y + z*z
        lsum = np.zeros((sensor_data.chunk_count(),1))
        for part in np.array_split(l, 3, axis=OVER_SAMPLES):
            OVER_PARTS = 1 # part is a dimension smaller than chunk, so this is last axis
            mx = np.amax(part, axis=OVER_PARTS)
            mn = np.amin(part, axis=OVER_PARTS)
            df = mx - mn
            lsum += df
        return (lsum/3.0).transpose()


class Transition(Algorithm):
    __algname__ = "transition"
    __output__ = ['up', 'down']
    __type__ = 'chunk'
    __input__ = 'accelerometer'
    __min__ = -5
    __max__ = 5

    @staticmethod
    def analyse_data_low(sensor_data):
        assert(len(sensor_data.data.shape) == 3) # required for 'chunk' type
        x, y, z, _ = get_xyz(sensor_data)
        lp = LowpassFilter(12.5, 0.5)
        chunk_sc = sensor_data.sample_count() / sensor_data.chunk_count()

        x_all = x.view()
        x_all.shape = (-1, 1)
        x_lp = lp.filter(np.squeeze(x_all))
        x_all[:] = 0
        #up_idx, down_idx = crossing(np.arcsin(-x_lp), 0.4)
        up_idx, down_idx = hyst_crossing(-x_lp, numpy.sin(0.35), numpy.sin(0.55))
        up = np.zeros((sensor_data.chunk_count(),1))
        down = np.zeros((sensor_data.chunk_count(),1))
        for u in up_idx:
            i = int(u//chunk_sc)
            up[i,0] = up[i,0] + 1
        for d in down_idx:
            i = int(d//chunk_sc)
            down[i,0] = down[i,0] - 1
        return np.vstack((up.transpose(), down.transpose()))


class RawAngles(Algorithm):
    __algname__ = 'raw_angles'
    __output__ = ['xangle', 'yangle', 'zangle']
    __type__ = 'samples'
    __input__ = 'accelerometer'
    __min__ = -np.pi
    __max__ = np.pi

    def __init__(self): pass

    @staticmethod
    def analyse_data(sensor_data):
        x, y, z, _ = get_xyz(sensor_data)
        return np.hstack([
            np.arcsin(np.clip(x, -1, 1)),
            np.arcsin(np.clip(y, -1, 1)),
            np.arcsin(np.clip(z, -1, 1))
        ])


class ActivityAngle(Algorithm):
    __algname__ = "activity_angle"
    __output__ = ['angle1', 'angle2']
    __type__ = 'chunk'
    __input__ = 'accelerometer'
    __min__ = -2
    __max__ = 2

    @staticmethod
    def analyse_data_low(sensor_data, axis='x'):
        x, y, z, _ = get_xyz(sensor_data)
        # Find average of X and cap it to range [-1, 1]
        if axis == 'x':
            x_avg = np.clip(np.mean(x, axis=OVER_SAMPLES), -1.0, 1.0)
        elif axis == 'y':
            x_avg = np.clip(np.mean(y, axis=OVER_SAMPLES), -1.0, 1.0)
        # PI/2 is standing, 0 is resting
        a = np.squeeze(np.arcsin(-x_avg))

        return np.vstack((a, a))


class ActivityDAngle(Algorithm):
    __algname__ = "activity_d_angle"
    __output__ = ['dangle']
    __type__ = 'chunk'
    __input__ = 'accelerometer'
    __min__ = -2
    __max__ = 2

    @staticmethod
    def analyse_data_low(sensor_data):
        x, y, z, _ = get_xyz(sensor_data)
        # Find min and max of X and cap it to range [-1, 1]
        x_min = np.clip(np.min(x, axis=OVER_SAMPLES), -1.0, 1.0)
        x_max = np.clip(np.max(x, axis=OVER_SAMPLES), -1.0, 1.0)
        # Difference in angle
        da = np.arcsin(-x_min ) - np.arcsin(-x_max)
        return da.transpose()


class ActivityFFT(Algorithm):
    __algname__ = "activity_fft"
    __output__ = ['amplitude', 'order1', 'factor']
    __type__ = 'chunk'
    __input__ = 'accelerometer'
    __min__ = 0
    __max__ = 2.0

    @staticmethod
    def analyse_data_low(sensor_data, param):
        x, y, z, _ = get_xyz(sensor_data)

        chunk_sc = int(sensor_data.sample_count() / sensor_data.chunk_count())

        freqs = rfftfreq(chunk_sc, 0.08)
        peak = np.squeeze(np.argmax(peaks, axis=OVER_SAMPLES))

        return np.vstack((yz_fft_max, fft_order1, fft_factor))


class FreqPeakFilt(Algorithm):
    __algname__ = "freq_peak_filt"
    __output__ = ["response"]
    __type__ = 'samples'
    __min__ = -0.25
    __max__ = 1.0

    N = 100
    MULTS = np.array([1, 1.5, 2, 2.5, 3, 3.5, 4])
    SIGNS = np.array([1, -1, 1, -1, 1, -1, 1])

    @staticmethod
    def get_search_freqs(meta=None):
        # TODO: caculate this from the meta
        return np.linspace(0.2, 1.8, FreqPeakFilt.N)

    @staticmethod
    def calc_response(freqs, chunk, meta=None):

        search_freqs = FreqPeakFilt.get_search_freqs(meta)
        r = np.zeros(FreqPeakFilt.N)
        chunk = np.squeeze(chunk)
        for j, f in enumerate(search_freqs):
            r[j] = np.dot(np.interp(f * FreqPeakFilt.MULTS, freqs, chunk),
                          FreqPeakFilt.SIGNS)

        return r

    @staticmethod
    def analyse_data_low(sensor_data, meta=None):
        x, y, z, _ = get_xyz(sensor_data)
        param = Algorithm.get_parameters(meta)

        chunk_sc = sensor_data.sample_count() / sensor_data.chunk_count()

        freqs = rfftfreq(chunk_sc, float(sensor_data.sample_interval) / 1000.0)
        x_fft = np.fft.rfft(x, axis=OVER_SAMPLES)
        y_fft = np.fft.rfft(y, axis=OVER_SAMPLES)
        z_fft = np.fft.rfft(z, axis=OVER_SAMPLES)
        yz_fft_abs = np.sqrt(np.sum(np.absolute(i)**2
                             for i in [x_fft, y_fft, z_fft]))/chunk_sc

        resp = np.zeros((yz_fft_abs.shape[0], FreqPeakFilt.N))
        for i, chunk in enumerate(yz_fft_abs):
            resp[i,:] = FreqPeakFilt.calc_response(freqs, chunk, meta)

        return resp


class FreqPeaks(Algorithm):
    __algname__ = "freq_peaks"
    __output__ = ['amplitude', 'response', 'factor', 'order1']
    __type__ = 'chunk'
    __input__ = 'accelerometer'
    __min__ = 0
    __max__ = 2.0

    @staticmethod
    def analyse_data_low(sensor_data, meta=None):
        AMP_CUTOFF = 0.05

        x, y, z, _ = get_xyz(sensor_data)
        param = Algorithm.get_parameters(meta)

        chunk_sc = sensor_data.sample_count() / sensor_data.chunk_count()

        freqs = rfftfreq(chunk_sc, float(sensor_data.sample_interval) / 1000.0)
        x_fft = np.fft.rfft(x, axis=OVER_SAMPLES)
        y_fft = np.fft.rfft(y, axis=OVER_SAMPLES)
        z_fft = np.fft.rfft(z, axis=OVER_SAMPLES)
        yz_fft_abs = np.sqrt(np.sum(np.absolute(i)**2
                             for i in [x_fft, y_fft, z_fft]))/chunk_sc

        resp = np.zeros(yz_fft_abs.shape[0])
        order1 = np.zeros(yz_fft_abs.shape[0])
        amp = np.zeros(yz_fft_abs.shape[0])
        factor = np.zeros(yz_fft_abs.shape[0])

        search_freqs = FreqPeakFilt.get_search_freqs(meta)

        for i, chunk in enumerate(np.squeeze(yz_fft_abs)):
            r = FreqPeakFilt.calc_response(freqs, chunk)
            max_idx = np.argmax(r)
            resp[i] = r[max_idx]
            order1[i] = search_freqs[max_idx]
            fa = np.interp(order1[i] * FreqPeakFilt.MULTS[::2], freqs, chunk)
            amp[i] = np.max(fa)
            if amp[i] > AMP_CUTOFF:
                factor[i] = np.sum(fa[1:3]) / fa[0]
            else:
                factor[i] = 0
                order1[i] = 0

        return np.vstack((amp, resp, factor / 5.0, order1))


Algorithms.attach(ActivityAngle)
Algorithms.attach(ActivityFFT)
Algorithms.attach(Transition)
