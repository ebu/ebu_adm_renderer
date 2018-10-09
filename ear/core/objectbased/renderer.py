import numpy as np
import math
from fractions import Fraction
from ..convolver import OverlapSaveConvolver, VariableBlockSizeAdapter
from ..delay import Delay
from ...options import Option, SubOptions, OptionsHandler
from .gain_calc import GainCalc
from . import decorrelate
from ..renderer_common import BlockProcessingChannel, InterpretTimingMetadata, InterpGains, FixedGains
from ..track_processor import TrackProcessor


class InterpretObjectMetadata(InterpretTimingMetadata):
    """Interpret a sequence of ObjectTypeMetadata, producing a sequence of ProcessingBlock.

    Args:
        calc_gains (callable): Called with ObjectTypeMetadata to calculate per-channel gains.
    """

    def __init__(self, calc_gains):
        super(InterpretObjectMetadata, self).__init__()
        self.calc_gains = calc_gains

        self.last_block_end = None
        self.last_block_gains = None

    @classmethod
    def interp_length(cls, block_format, duration):
        if block_format.jumpPosition.flag:
            if block_format.jumpPosition.interpolationLength is not None:
                return block_format.jumpPosition.interpolationLength
            else:
                return Fraction(0)
        else:
            return duration

    def __call__(self, sample_rate, block):
        """Yield ProcessingBlock that apply the processing for a given ObjectTypeMetadata.

        Args:
            sample_rate (int): Sample rate to operate in.
            block (ObjectTypeMetadata): Metadata to interpret.

        Yields:
            One or two ProcessingBlock objects that apply gains for a single input channel.
        """
        start_time, end_time = self.block_start_end(block)
        interp_time = self.interp_length(block.block_format, end_time - start_time)
        target_time = start_time + interp_time

        if target_time > end_time:
            raise Exception("specified interpolation length is longer than block {0.id}".format(block.block_format))

        # if this block starts immediately after a previous block, interpolate
        # from it, otherwise, don't do any interpolation.
        if self.last_block_end is not None and start_time == self.last_block_end:
            interp_from = self.last_block_gains
        else:
            target_time = start_time
            interp_from = None

        interp_to = self.calc_gains(block)

        start_sample = start_time * sample_rate
        end_sample = end_time * sample_rate
        target_sample = target_time * sample_rate

        if start_sample != target_sample:
            assert not math.isinf(target_sample)
            yield InterpGains(start_sample, target_sample, interp_from, interp_to)
        if target_sample != end_sample:
            assert not math.isinf(target_sample)
            yield FixedGains(target_sample, end_sample, interp_to)

        self.last_block_end = end_time
        self.last_block_gains = interp_to


class ObjectRenderer(object):

    options = OptionsHandler(
        block_size=Option(
            default=512,
            description="block size for decorrelator convolution",
        ),
        gain_calc_opts=SubOptions(
            handler=GainCalc.options,
            description="options for gain calculator",
        ),
        decorrelator_opts=SubOptions(
            handler=decorrelate.design_options,
            description="options for decorrelation filter design",
        ),
    )

    @options.with_defaults
    def __init__(self, layout, gain_calc_opts, decorrelator_opts, block_size):
        self._gain_calc = GainCalc(layout, **gain_calc_opts)
        self._nchannels = len(layout.channels)

        # tuples of a track spec processor and a BlockProcessingChannel to
        # apply to the samples it produces.
        self.block_processing_channels = []

        decorrlation_filters = decorrelate.design_decorrelators(layout, **decorrelator_opts)
        decorrelator_delay = (decorrlation_filters.shape[0] - 1) // 2

        decorrelators = OverlapSaveConvolver(
            block_size, self._nchannels, decorrlation_filters)
        self.decorrelators_vbs = VariableBlockSizeAdapter(
            block_size, self._nchannels, decorrelators.filter_block)

        self.overall_delay = self.decorrelators_vbs.delay(decorrelator_delay)

        self.delays = Delay(self._nchannels, self.overall_delay)

    def _calc_gains(self, block):
        gains = self._gain_calc.render(block)
        return np.concatenate((gains.direct, gains.diffuse))

    def set_rendering_items(self, rendering_items):
        """Set the rendering items to process.

        Note:
            Since this resets the internal state, this should normally be called
            once before rendering is started. Dynamic modification of the
            rendering items could be implemented though another API.

        Args:
            rendering_items (list of ObjectRenderingItem): Items to process.
        """
        self.block_processing_channels = [(TrackProcessor(item.track_spec),
                                           BlockProcessingChannel(item.metadata_source,
                                                                  InterpretObjectMetadata(self._calc_gains)))
                                          for item in rendering_items]

    def render(self, sample_rate, start_sample, input_samples):
        """Process n input samples to produce n output samples.

        Args:
            sample_rate (int): Sample rate.
            start_sample (int): Index of the first sample in input_samples.
            input_samples (ndarray of (k, k) float): Multi-channel input sample
                block; there must be at least as many channels as referenced in the
                rendering items.

        Returns:
            (ndarray of (n, l) float): l channels of output samples
                corresponding to the l loudspeakers in layout.
        """
        interpolated = np.zeros((len(input_samples), self._nchannels * 2))

        for track_spec_processor, block_processing in self.block_processing_channels:
            track_samples = track_spec_processor.process(sample_rate, input_samples)
            block_processing.process(sample_rate, start_sample, track_samples, interpolated)

        direct_out = self.delays.process(interpolated[:, :self._nchannels])
        diffuse_out = self.decorrelators_vbs.process(interpolated[:, self._nchannels:])
        return direct_out + diffuse_out
