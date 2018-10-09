import numpy as np
from .panner import DirectSpeakersPanner
from ..renderer_common import BlockProcessingChannel, InterpretTimingMetadata, FixedGains
from ..track_processor import TrackProcessor


class InterpretDirectSpeakersMetadata(InterpretTimingMetadata):
    """Interpret a sequence of DirectSpeakersTypeMetadata, producing a sequence of ProcessingBlock.

    Args:
        calc_gains (callable): Called with DirectSpeakersTypeMetadata to calculate per-channel gains.
    """

    def __init__(self, calc_gains):
        super(InterpretDirectSpeakersMetadata, self).__init__()
        self.calc_gains = calc_gains

    def __call__(self, sample_rate, block):
        """Yield ProcessingBlock that apply the processing for a given DirectSpeakersTypeMetadata.

        Args:
            sample_rate (int): Sample rate to operate in.
            block (DirectSpeakersTypeMetadata): Metadata to interpret.

        Yields:
            One ProcessingBlock object that apply gains for a single input channel.
        """
        start_time, end_time = self.block_start_end(block)

        start_sample = sample_rate * start_time
        end_sample = sample_rate * end_time

        gains = self.calc_gains(block)

        yield FixedGains(start_sample, end_sample, gains)


class DirectSpeakersRenderer(object):

    options = DirectSpeakersPanner.options

    @options.with_defaults
    def __init__(self, layout, **options):
        self._panner = DirectSpeakersPanner(layout, **options)
        self._nchannels = len(layout.channels)

        # tuples of a track spec processor and a BlockProcessingChannel to
        # apply to the samples it produces.
        self.block_processing_channels = []

    def set_rendering_items(self, rendering_items):
        """Set the rendering items to process.

        Note:
            Since this resets the internal state, this should normally be called
            once before rendering is started. Dynamic modification of the
            rendering items could be implemented though another API.

        Args:
            rendering_items (list of DirectSpeakersRenderingItem): Items to process.
        """
        self.block_processing_channels = [(TrackProcessor(item.track_spec),
                                           BlockProcessingChannel(
                                               item.metadata_source,
                                               InterpretDirectSpeakersMetadata(self._panner.handle)))
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
        output_samples = np.zeros((len(input_samples), self._nchannels))

        for track_spec_processor, block_processing in self.block_processing_channels:
            track_samples = track_spec_processor.process(sample_rate, input_samples)
            block_processing.process(sample_rate, start_sample, track_samples, output_samples)

        return output_samples
