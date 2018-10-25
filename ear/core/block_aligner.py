import numpy as np


class BlockAligner(object):
    """Mix a number of input streams with varying delays into a single aligned
    output stream.

    The calls to `add` and `get` must repeat in this sequence:

        - one call to add with a block and delay for each input stream
        - one call to get

    Args:
        n_channels (int): number of channels in all inputs and outputs.
    """

    def __init__(self, n_channels):
        self.buf = np.zeros((0, n_channels))
        # sample number of the first sample in the buffer
        self.buf_start = 0
        # sample number of the end of the earliest buffer added, or None if we
        # are at the start of a round. This indicates the end of the completed
        # region in buf.
        self.first_end = None

    def add(self, start, samples):
        """Add a block of samples to be summed into the output.

        Args:
            start (int): index that the first sample in the block should take
                in the output; may be negative.
            samples (ndarray of n,k floats): n samples for k channels.
        """
        # strip off any samples before time 0
        if start < self.buf_start:
            assert self.buf_start == 0, "samples in past only allowed before time 0"

            to_discard = min(self.buf_start - start, len(samples))
            samples = samples[to_discard:]
            start += to_discard
            # here, we might have 0 samples, but we still go through the rest
            # of the process so that first_end is updated below

        end = start + len(samples)

        # start and end indices of samples in self.buf
        start_buf = start - self.buf_start
        end_buf = end - self.buf_start

        if end_buf > len(self.buf):
            self.buf.resize((end_buf, self.buf.shape[1]), refcheck=False)

        if len(samples):
            assert 0 <= start_buf and 0 < end_buf
            self.buf[start_buf:end_buf] += samples

        if self.first_end is None or self.first_end > end:
            self.first_end = end

    def get(self):
        """Get the samples that have been completely filled by all input streams.

        Returns:
            ndarray of (n, k): n samples for k channels.

            The number of samples returned varies according to the number of
            input samples and their times, and may be 0. The first sample
            returned is the sample for time 0.
        """
        assert self.first_end is not None
        # number of samples that are completely filled and can be returned
        n_samples = max(self.first_end - self.buf_start, 0)

        # return the first n_samples samples, and shift the remaining samples to the start
        to_return = self.buf[:n_samples].copy()
        self.buf[:len(self.buf) - n_samples] = self.buf[n_samples:]
        self.buf[len(self.buf) - n_samples:] = 0

        self.buf_start += n_samples
        self.first_end = None

        return to_return
