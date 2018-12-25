import numpy as np
import scipy.signal as sig


class LowpassFilter:
    def __init__(self, sample_freq_hz, cutoff_hz):
        # Configure Filter
        nyq_freq = sample_freq_hz / 2.0
        ripple_db = 26.0
        width = 1.0 / nyq_freq
        cutoff_freq = cutoff_hz

        # Generate Filter
        n, beta = sig.kaiserord(ripple_db, width)
        taps = sig.firwin(n, cutoff_freq / nyq_freq, window=('kaiser', beta))

        self.taps = taps
        self.ltaps = len(self.taps)
        self.ltapsh = int(np.floor(len(self.taps) / 2))

    def filter(self, data, axis=-1):
        data = np.atleast_2d(data)
        tapshl = self.ltaps // 2 + 1
        padding = [(0, 0)] * data.ndim
        padding[axis] = (tapshl, tapshl)

        us_data = data.copy()
        s_data = np.pad(us_data, padding, 'symmetric')
        us_data = sig.lfilter(self.taps, 1.0, s_data, axis=axis)

        idxs = np.arange(2 * tapshl, us_data.shape[axis])
        return np.squeeze(us_data.take(idxs, axis=axis))
