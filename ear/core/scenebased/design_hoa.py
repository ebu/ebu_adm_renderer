import numpy as np
import warnings
from .. import hoa
from ..hoa_adapter import HOAFormat
from .design import build_hoa_decoder_design


class HOAFormatConvert:
    """replacement for HOADecoderDesign which designs matrices to convert from
    one HOA format to another
    """

    def __init__(self, fmt):
        self.out_fmt = fmt

    def design(self, type_metadata):
        """Design a decoder matrix for the given HOA format.

        Args:
            type_metadata (HOATypeMetadata): HOA metadata.

        Returns:
            l, m decoder matrix from m HOA channels to l loudspeaker channels
        """
        if type_metadata.screenRef:
            warnings.warn("screenRef for HOA is not implemented; ignoring")
        if (
            type_metadata.extra_data.channel_frequency.lowPass is not None
            or type_metadata.extra_data.channel_frequency.highPass is not None
        ):
            warnings.warn("frequency information for HOA is not implemented; ignoring")

        in_orders, in_degrees = np.array(type_metadata.orders), np.array(
            type_metadata.degrees
        )
        out_orders, out_degrees = self.out_fmt.orders_degrees

        in_norm = hoa.norm_functions[type_metadata.normalization]
        out_norm = self.out_fmt.norm_fn

        def find(ns, ms, n, m):
            (where,) = np.where((ns == n) & (ms == m))
            assert len(where <= 1)
            if len(where):
                return where[0]

        # more in than out -> discard high orders
        # more out than in -> high orders are silent
        # therefore only process minimum of in and out
        max_order = min(max(in_orders), max(out_orders))

        out = np.zeros((len(out_orders), len(in_orders)))

        acns = np.arange((max_order + 1) ** 2)
        orders, degrees = hoa.from_acn(acns)
        norm_factors = out_norm(orders, np.abs(degrees)) / in_norm(
            orders, np.abs(degrees)
        )

        for n, m, norm_factor in zip(orders, degrees, norm_factors):
            in_channel = find(in_orders, in_degrees, n, m)
            out_channel = find(out_orders, out_degrees, n, m)

            if in_channel is not None and out_channel is not None:
                out[out_channel, in_channel] = norm_factor

        return out


@build_hoa_decoder_design.register(HOAFormat)
def _build_hoa_decoder_design_hoa(layout, **options):
    return HOAFormatConvert(layout, **options)
