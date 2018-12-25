import scipy
import numpy
from numpy import pi, absolute, floor
from scipy.signal import firwin, kaiserord, lfilter


class UpsampleFilter:
    def __init__(self, source_interval, upsample_factor):
        source_freq = 1000.0/source_interval
        target_freq = source_freq * upsample_factor

        # Configure Fiter
        nyq_freq = target_freq / 2.0
        ripple_db = 26.0
        width = 1.0/nyq_freq
        cutoff_freq = source_freq * 0.40

        # Generate Filter
        N, beta = kaiserord(ripple_db, width)
        taps = firwin(N, cutoff_freq/nyq_freq, window=('kaiser', beta))

        self.taps = taps
        self.source_freq = source_freq
        self.target_freq = target_freq
        self.upsample_factor = upsample_factor
        self.ltaps = len(self.taps)
        self.ltapsh = int(floor(len(self.taps)/2))

    def upsample(self, data):
        tapshl = self.ltaps//2 + 1
        padding = ((tapshl, tapshl), (0,0))

        us_data = numpy.repeat(data, self.upsample_factor, 0)
        us_data = numpy.pad(us_data, padding, 'symmetric')
        us_data = scipy.signal.lfilter(self.taps, 1.0, us_data, axis=0)

        return us_data[self.ltaps+2:,:]
