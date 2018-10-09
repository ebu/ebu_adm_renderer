import numpy as np
from attr import attrs, attrib
from .design import HOADecoderDesign
from ..renderer_common import BlockProcessingChannel, InterpretTimingMetadata, ProcessingBlock
from ..track_processor import MultiTrackProcessor
from ...options import OptionsHandler, SubOptions


@attrs(slots=True, frozen=True)
class FixedMatrix(ProcessingBlock):
    """Take n input channels, apply a matrix, and sum into m output channels.

    Attributes:
        matrix (ndarray of shape (m, n)): Matrix from n input channels to m
            output channels.
        output_channels (index for ndarray): Channels in output to sum into.
    """
    matrix = attrib()
    output_channels = attrib()

    def process(self, start_sample, input_samples, output_samples):
        ovl_state, ovl_samples = self.overlap(start_sample, len(input_samples))

        output_samples[ovl_samples, self.output_channels] += np.dot(input_samples[ovl_samples], self.matrix.T)


class InterpretHOAMetadata(InterpretTimingMetadata):
    """Interpret a sequence of HOATypeMetadata, producing a sequence of ProcessingBlock.

    Args:
        design_decoder (callable): Called with HOATypeMetadata to design a decode matrix.
        output_channels (index for ndarray): Output channels to sum into.
    """

    def __init__(self, design_decoder, output_channels):
        super(InterpretHOAMetadata, self).__init__()
        self.design_decoder = design_decoder
        self.output_channels = output_channels

    def __call__(self, sample_rate, block):
        """Yield ProcessingBlock that apply the processing for a given HOATypeMetadata.

        Args:
            sample_rate (int): Sample rate to operate in.
            block (HOATypeMetadata): Metadata to interpret.

        Yields:
            One ProcessingBlock object that apply gains for a single input channel.
        """
        start_time, end_time = self.block_start_end(block, block_time_in_block_format=False)

        start_sample = sample_rate * start_time
        end_sample = sample_rate * end_time

        decoder = self.design_decoder(block)

        yield FixedMatrix(start_sample, end_sample, decoder, self.output_channels)


class HOARenderer(object):

    options = OptionsHandler(
        design_opts=SubOptions(handler=HOADecoderDesign.options,
                               description="options for decoder design"),
    )

    @options.with_defaults
    def __init__(self, layout, design_opts):
        self._decoder_design = HOADecoderDesign(layout.without_lfe, **design_opts)
        self._output_channels = ~layout.is_lfe

        self.block_processing_channels = []

    def set_rendering_items(self, rendering_items):
        """Set the rendering items to process.

        Note:
            Since this resets the internal state, this should normally be called
            once before rendering is started. Dynamic modification of the
            rendering items could be implemented though another API.

        Args:
            rendering_items (list of HOARenderingItem): Items to process.
        """
        self.block_processing_channels = [(MultiTrackProcessor(item.track_specs),
                                           BlockProcessingChannel(
                                               item.metadata_source,
                                               InterpretHOAMetadata(self._decoder_design.design,
                                                                    self._output_channels)))
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
        output_samples = np.zeros((len(input_samples), len(self._output_channels)))

        for track_spec_processor, block_processing in self.block_processing_channels:
            track_samples = track_spec_processor.process(sample_rate, input_samples)
            block_processing.process(sample_rate, start_sample, track_samples, output_samples)

        return output_samples
