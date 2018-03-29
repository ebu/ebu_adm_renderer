import numpy as np


class OverlapSaveConvolver(object):
    """Objects that convolve a signal with a filter in fixed-size blocks.

    Parameters:
        block_size (int): time domain block size for input and output blocks
        nchannels (int): number of channels to process
        f (array of (n, nchannels) floats): specification of nchannels length n
            FIR filters to convolve the input channels with.

    Attributes:
        block_size (int): time domain block size for input and output blocks
        filter_blocks_fd (list of complex arrays): blocks of block_size samples
            of the filter, padded to 2*block_size and fft-ed
        blocks_fd (list of complex arrays): The filter state; blocks_fd[i] will
            form the output in i blocks time, so each input block is multiplied
            by filter_blocks_fd[i] and summed into blocks_fd[i]. After each
            block this queue is rotated to maintain this invariant.
        input_block (array of (block_size*2, nchannels) floats): input to the
            forward fft; the first half contains the input for this block, and the
            second half contains the input from the previous block, so that the
            first half of each block in blocks_fd will contain the tail from the
            previous block.
    """

    def __init__(self, block_size, nchannels, f):
        self.block_size = block_size
        self.input_block = np.zeros((block_size * 2, nchannels))

        self.filter_blocks_fd = []
        self.blocks_fd = []
        for start in range(0, len(f), self.block_size):
            end = min(len(f), start + self.block_size)
            block_fd = np.fft.rfft(f[start:end], self.block_size * 2, axis=0)

            self.filter_blocks_fd.append(block_fd)
            self.blocks_fd.append(np.zeros_like(block_fd))

    def filter_block(self, in_block_td):
        """Filter a time domain block of samples.

        Parameters:
            in_block_td (array of (block_size, nchannels) floats): block of
                time domain input samples

        Returns:
            array of (block_size, nchannels) floats: block of time domain
                output samples
        """
        self.input_block[self.block_size:] = self.input_block[:self.block_size]
        self.input_block[:self.block_size] = in_block_td

        in_block_fd = np.fft.rfft(self.input_block, axis=0)

        for filter_block, block in zip(self.filter_blocks_fd, self.blocks_fd):
            block += filter_block * in_block_fd

        first_block_td = np.fft.irfft(self.blocks_fd[0], axis=0)

        self.blocks_fd[0][:] = 0.0
        self.blocks_fd.append(self.blocks_fd.pop(0))

        return first_block_td[:self.block_size]


class VariableBlockSizeAdapter(object):
    """Adapt a block that processes fixed-size blocks of samples into one that
    processes variable sized blocks by adding some delay.

    Parameters:
        block_size (int): Block size that process_func accepts.
        nchannels (int): Number of channels that block_size accepts.
        process_func (callable): Callback such that Y=process_func(X) processes
            an (block_size, nchannels) array X, to produce another (block_size,
            nchannels) array Y.
    """

    def __init__(self, block_size, nchannels, process_func):
        self.process_func = process_func
        self.block_size = block_size

        # store block_size samples, input samples followed by output samples:
        # - self.buffer[:self.buffer_input] stores unprocessed input samples
        # - self.buffer[self.buffer_input:] stores processed output samples
        self.buffer = process_func(np.zeros((block_size, nchannels)))
        self.buffer_input = 0

    def delay(self, process_delay):
        return self.block_size + process_delay

    def process(self, input_samples):
        """Process n samples.

        Parameters:
            input_samples (array of (n, nchannels) floats): input samples

        Returns:
            array of (n, nchannels) floats: output samples
        """
        output_samples = np.zeros_like(input_samples)

        # range of input and output samples that are yet to be processed
        n_done, n_input = 0, len(input_samples)

        while n_done < n_input:
            # transfer as many samples as possible from the buffer to the
            # output, and from the input to the buffer in their place.
            to_xfer = min(n_input - n_done, self.block_size - self.buffer_input)
            buffer_slice = slice(self.buffer_input, self.buffer_input+to_xfer)
            samples_slice = slice(n_done, n_done + to_xfer)

            output_samples[samples_slice] = self.buffer[buffer_slice]
            self.buffer[buffer_slice] = input_samples[samples_slice]

            self.buffer_input += to_xfer
            n_done += to_xfer

            # at this point the buffer is a full as it can be of input samples;
            # process these to turn them into output samples if we have enough
            if self.buffer_input == self.block_size:
                self.buffer[:] = self.process_func(self.buffer)
                self.buffer_input = 0

        assert n_done == n_input

        return output_samples
