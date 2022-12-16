import numpy as np
from ..convolver import OverlapSaveConvolver, VariableBlockSizeAdapter
from ..delay import Delay
from ..hoa_adapter import HOAFormat
from .gain_calc_hoa import GainCalcHOA
from .renderer import ObjectRenderer, build_objects_renderer


def design_decorrelators(layout, size=512):
    from .. import hoa
    from ..quadrature import get_t_design
    from .decorrelate import design_decorrelator_basic

    points = get_t_design((layout.max_order * 2) + 1)

    decorrelators = np.array(
        [design_decorrelator_basic(i, size=size) for i in range(len(points))]
    ).T

    az = -np.arctan2(points[:, 0], points[:, 1])
    el = np.arctan2(points[:, 2], np.hypot(points[:, 0], points[:, 1]))

    n, m = layout.orders_degrees
    encoder = hoa.sph_harm(
        n[:, np.newaxis],
        m[:, np.newaxis],
        az[np.newaxis],
        el[np.newaxis],
        norm=hoa.norm_N3D,
    )

    decoder = encoder.T / len(points)

    # decode to t-design, decorrelate, then re-encode
    # order: sample, in, out
    decorr_mat = np.einsum("ij,kj,jl->kil", encoder, decorrelators, decoder)

    # normalisebased on an omni source
    decorr_mat /= np.linalg.norm(decorr_mat[:, 0])

    # apply normalisation -- do this at the end to ensure it behaves the same
    # with different normalisations
    norm = layout.norm_fn(n, np.abs(m)) / hoa.norm_N3D(n, np.abs(m))
    decorr_mat *= norm / norm[:, np.newaxis]

    return decorr_mat


class OverlapSaveConvolverMatrix:
    def __init__(self, block_size, filters):
        """
        Args:
            block_size (int): block size
            filters (ndarray of shape (i, o, n)): filters with i input channels, o output channels and n samples
        """
        self._num_in, self._num_out = filters.shape[1:]

        filters_flat = filters.reshape(filters.shape[0], -1)

        self._decorrelators = OverlapSaveConvolver(
            block_size, filters_flat.shape[1], filters_flat
        )

    def filter_block(self, in_block):
        decorr_in = np.repeat(in_block, self._num_out, axis=1)
        decor_out = self._decorrelators.filter_block(decorr_in)
        return np.sum(decor_out.reshape(-1, self._num_in, self._num_out), axis=1)


class ObjectRendererHOA(ObjectRenderer):
    def __init__(self, layout, gain_calc_opts={}, decorrelator_opts={}, block_size=512):
        self._gain_calc = GainCalcHOA(layout, **gain_calc_opts)
        self._nchannels = n = layout.num_channels

        # tuples of a track spec processor and a BlockProcessingChannel to
        # apply to the samples it produces.
        self.block_processing_channels = []

        decorrlation_filters = design_decorrelators(layout)
        decorrelator_delay = (decorrlation_filters.shape[0] - 1) // 2

        decorrelators = OverlapSaveConvolverMatrix(block_size, decorrlation_filters)

        self.decorrelators_vbs = VariableBlockSizeAdapter(
            block_size, self._nchannels, decorrelators.filter_block
        )

        self.overall_delay = self.decorrelators_vbs.delay(decorrelator_delay)

        self.delays = Delay(self._nchannels, self.overall_delay)

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
            block_processing.process(
                sample_rate, start_sample, track_samples, interpolated
            )

        direct_out = self.delays.process(interpolated[:, : self._nchannels])
        diffuse_out = self.decorrelators_vbs.process(interpolated[:, self._nchannels :])
        return direct_out + diffuse_out


@build_objects_renderer.register(HOAFormat)
def _build_objects_renderer_hoa(layout):
    return ObjectRendererHOA(layout)
