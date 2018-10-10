import numpy as np
import warnings


class PeakMonitor(object):
    """Monitor the peak level of each channel in a multichannel stream.

    Call process(samples) on each block of samples, then print_warnings() to
    warn about overloaded channels.

    Parameters:
        nchannels (int): number of channels to monitor
    """

    def __init__(self, nchannels):
        self.peak_abs_linear = np.zeros(nchannels)

    def process(self, samples):
        """Process a block of samples.

        Parameters:
            samples (ndarray of (m, nchannels)): block of m samples
        """
        max_in_block = np.max(np.abs(samples), axis=0, initial=0.0)
        self.peak_abs_linear = np.maximum(self.peak_abs_linear, max_in_block)

    def has_overloaded(self):
        return np.any(self.peak_abs_linear > 1)

    def warn_overloaded(self):
        """Produce a warning for each overloaded channel."""
        for channel, max_sample in enumerate(self.peak_abs_linear):
            if max_sample > 1:
                warnings.warn("overload in channel {channel}; peak level was {max_dbfs:.1f}dBFS".format(
                    channel=channel,
                    max_dbfs=20*np.log10(max_sample),
                ))
