import numpy as np
import math
from fractions import Fraction
from attr import attrs, attrib
from collections import deque
import warnings


def ceil(x):
    """Ceiling function compatible with Fraction on both python 2 and 3 that
    also passes through inf."""
    if math.isinf(x):
        return x
    y = math.trunc(x)
    if y < x:
        y += 1
    return y


@attrs(slots=True, frozen=True)
class ProcessingBlock(object):
    """Time-bounded audio processing.

    This applies some kind of audio effect between fractional sample numbers
    start_sample and end_sample. The actual samples affected are those between
    first_sample and last_sample.

    This class deals with the timing of the blocks; the actual audio processing
    is defined in sub-classes.
    """

    # fractional start and end samples; sample number s is affected if
    # start_sample <= s < end_sample
    start_sample = attrib()
    end_sample = attrib()

    # integer sample numbers of the first and last sample affected; sample
    # number s is affected if first_sample <= s < last_sample
    first_sample = attrib(init=False, eq=False)
    last_sample = attrib(init=False, eq=False)

    @first_sample.default
    def init_start_sample_round(self):
        return ceil(self.start_sample)

    @last_sample.default
    def init_end_sample_round(self):
        return ceil(self.end_sample)

    def overlap(self, start_sample, num_samples):
        """Calculate the overlap between this block and a block of samples.

        Args:
            start_sample (int): Index of the first sample in the block.
            num_samples (int): Number of samples in the block.

        Returns:
            - slice: range of samples in this block (with 0 being the first
                sample affected by this block) that the overlap covers. can be used
                to index some internal state of this block.
            - slice: range of samples in the block of samples (with 0 being the
                first sample in the block) that the overlap covers. This can be
                used to index the sample block.
        """
        end_sample = start_sample + num_samples

        overlap_start_sample = max(start_sample, self.first_sample)
        overlap_end_sample = min(end_sample, self.last_sample)

        if overlap_start_sample <= overlap_end_sample:
            return (slice(overlap_start_sample - self.first_sample, overlap_end_sample - self.first_sample),
                    slice(overlap_start_sample - start_sample, overlap_end_sample - start_sample))
        else:
            # no overlap
            return slice(0), slice(0)


@attrs(slots=True, frozen=True)
class FixedGains(ProcessingBlock):
    """Take a single input channel, apply n gains and sum into n output channels."""

    gains = attrib()

    def process(self, start_sample, input_samples, output_samples):
        ovl_state, ovl_samples = self.overlap(start_sample, len(input_samples))

        output_samples[ovl_samples] += input_samples[ovl_samples, np.newaxis] * self.gains[np.newaxis]


@attrs(slots=True, frozen=True)
class InterpGains(ProcessingBlock):
    """Take a single input channel, apply n linearly interpolated gains and sum into n output channels.

    Attributes:
        gains_start (array of n floats): Gains to be applied at time start_sample.
        gains_end (array of n floats): Gains to be applied at time end_sample.
    """

    gains_start = attrib()
    gains_end = attrib()

    # interpolation coefficients: ramp from 0 to 1 between start_sample and
    # end_sample, sampled for each sample in range first_sample:last_sample
    _interp_p = attrib(init=False, eq=False)

    @_interp_p.default
    def init_interp_p(self):
        # number of samples actually in the ramp
        n = self.last_sample - self.first_sample

        # avoid divide by 0 if there are no samples to apply to
        if n == 0: return np.array([])

        # value at first_sample and last_sample
        start = float((self.first_sample - self.start_sample) / (self.end_sample - self.start_sample))
        end = float((self.last_sample - self.start_sample) / (self.end_sample - self.start_sample))

        return start + np.arange(n) * ((end - start) / n)

    def process(self, start_sample, input_samples, output_samples):
        ovl_state, ovl_samples = self.overlap(start_sample, len(input_samples))

        if self.gains_start is not None:
            input_fade_down = input_samples[ovl_samples] * (1.0 - self._interp_p[ovl_state])
            output_samples[ovl_samples] += input_fade_down[:, np.newaxis] * self.gains_start[np.newaxis]

        if self.gains_end is not None:
            input_fade_up = input_samples[ovl_samples] * self._interp_p[ovl_state]
            output_samples[ovl_samples] += input_fade_up[:, np.newaxis] * self.gains_end[np.newaxis]


class BlockProcessingChannel(object):
    """Given a source of metadata, and a method for turning that metadata into
    audio processing blocks, apply the processing to an audio stream.

    Args:
        metadata_source (metadata_input.MetadataSource): Source of metadata to
            pull from.
        interpret_metadata (callable): Take a block from the metadata source
            (e.g. an ObjectTypeMetadata) and produce some corresponding
            ProcessingBlock objects to apply to the audio stream.
    """

    def __init__(self, metadata_source, interpret_metadata):
        self.metadata_source = metadata_source
        self.interpret_metadata = interpret_metadata

        # queue of ProcessingBlock to apply to the audio stream; the first item
        # is the currently active one
        self.processing_queue = deque()

    def _refil_processing_queue(self, sample_rate, start_sample=None):
        """If processing_queue is empty, try to fill it up by pulling from the
        metadata source and interpreting the result.

        Args:
            sample_rate (int): Sample rate, needed when interpreting metadata.
            start_sample (int or None): Sample index of the first sample we are
                about to process, to check that metadata has not appeared too late.
        """
        while not len(self.processing_queue):
            block = self.metadata_source.get_next_block()

            if block is None:
                return

            for new_state in self.interpret_metadata(sample_rate, block):
                if start_sample is not None and new_state.first_sample < start_sample:
                    raise Exception("metadata underrun: metadata arrived after the samples that it would apply to")
                self.processing_queue.append(new_state)

    def process(self, sample_rate, start_sample, input_samples, output_samples):
        """Process some samples.

        Args:
            sample_rate (int): Sample rate.
            start_sample (int): Sample number of first sample.
            input_samples (ndarray of float): Input samples.
            output_samples (ndarray of float): Output samples.

        Note:
            The shape of `input_samples` and `output_samples` depends on the
            shape accepted by the processing blocks used, but the samples must
            be along the first axis.
        """

        end_sample = start_sample + len(input_samples)
        self._refil_processing_queue(sample_rate, start_sample)

        while len(self.processing_queue):
            self.processing_queue[0].process(start_sample, input_samples, output_samples)

            if self.processing_queue[0].last_sample < end_sample:
                # processing ends before end of sample block; go to next processing block and apply that too
                self.processing_queue.popleft()
                self._refil_processing_queue(sample_rate)
            elif self.processing_queue[0].last_sample == end_sample:
                # processing ends at end of sample block; we've done with this processing block and this sample block
                self.processing_queue.popleft()
                break
            else:
                # processing ends after end of sample block; we're done with this sample block
                break


class InterpretTimingMetadata(object):
    """Base class for Interpret*Metadata classes that knows how to determine
    the start and end times of blocks and catch related errors.
    """

    def __init__(self):
        self.__last_block_end = None

    def block_start_end(self, block, block_time_in_block_format=True):
        """Get the start and end time of a metadata block.

        Note:
            This keeps track of the last block end to detect overlapping
            blocks, so must be called with all blocks in sequence.

        Args:
            block (TypeMetadata): Metadata block to determine timing for.
            block_time_in_block_format (bool): Where do the rtime and duration
                attributes live for this type?

        Returns:
            tuple:
                block start time (Fraction): Time that the block starts at.
                block end time (Fraction or inf): Time that the block ends at,
                    or inf if it has no end.
        """
        # determine object start and end time
        if block.extra_data.object_start is not None:
            object_start = block.extra_data.object_start
        else:
            object_start = Fraction(0)

        if block.extra_data.object_duration is not None:
            object_end = object_start + block.extra_data.object_duration
        else:
            object_end = np.inf

        # pull out the block timing information
        if block_time_in_block_format:
            rtime, duration = block.block_format.rtime, block.block_format.duration
        else:
            rtime, duration = block.rtime, block.duration

        # determine block start and end time
        if rtime is not None and duration is not None:
            block_start = object_start + rtime
            block_end = block_start + duration

            if block_end > object_end:
                raise Exception("block {0.id} ends after object".format(block.block_format))
        elif rtime is None and duration is None:
            block_start, block_end = object_start, object_end
        else:
            raise Exception("rtime and duration must be used together.")

        # check for overlapping blocks; this will also raise if there is more
        # than one block without timing information or a mixture of blocks with
        # and without
        if self.__last_block_end is not None and block_start < self.__last_block_end:
            raise Exception("overlapping blocks {0.id} detected".format(block.block_format))
        self.__last_block_end = block_end

        return block_start, block_end


def is_lfe(frequency):
    """Determine if a channel is an LFE channel from its frequency metadata.

    This issues a warning if there is frequency information available but it is
    not recognised as specifying an LFE channel.

    Args:
        frequency (Frequency): Frequency info from channelFormat.

    Returns:
        bool
    """
    if (frequency.lowPass is not None and
            frequency.lowPass <= 200 and
            frequency.highPass is None):
        return True
    else:
        if frequency.lowPass is not None or frequency.highPass is not None:
            warnings.warn("Not treating channel with frequency {!r} as LFE.".format(frequency))
        return False
