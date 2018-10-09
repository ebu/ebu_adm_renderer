import numpy as np


class Delay(object):
    """Multi-channel delay line.

    Parameters:
        nchannels (int): number of channels to process
        delay (int): number of samples to delay by
    """

    def __init__(self, nchannels, delay):
        assert delay >= 0
        self.delaymem = np.zeros((delay, nchannels))
        self.delay = delay

    def process(self, input_samples):
        """Push n samples through the delay line.

        Parameters:
            input_samples (array of nsamples by nchannels): input samples

        Returns:
            array of nsamples by nchannels: output samples, delayed by delay
                samples.
        """
        output = np.zeros_like(input_samples)

        # transfer samples from the delay memory followed by the input, to the
        # output followed by the new delay memory, such that concat(src) before
        # the transfer has the same value as concat(dst) after
        src = [self.delaymem, input_samples]
        dst = [output, self.delaymem]

        # copy the common part of src[0] and dst[0]
        start_len = min(len(src[0]), len(dst[0]))
        if start_len: dst[0][:start_len] = src[0][:start_len]

        # copy the part where src[0] overlaps dst[1] or src[1] overlaps dst[0]
        overlap = len(src[0]) - len(dst[0])
        if overlap > 0:  # src[0] longer
            dst[1][:overlap] = src[0][-overlap:]
        elif overlap < 0:  # dst[0] longer
            dst[0][overlap:] = src[1][:-overlap]

        # copy the common part of src[1] and dst[1]
        end_len = min(len(src[1]), len(dst[1]))
        if end_len: dst[1][-end_len:] = src[1][-end_len:]

        return output
