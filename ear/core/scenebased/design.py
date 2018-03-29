import numpy as np
import warnings
from .. import hoa
from .. import point_source
from ...options import OptionsHandler, Option, SubOptions


class HOADecoderDesign(object):
    """Design HOA deciders for a given layout.

    Args:
        layout (Layout): Loudspeaker layout to design decoders for.
    """

    options = OptionsHandler(
        norm_mean_power=Option(default=True,
                               description="normalize the decoder"),
        maxRE=Option(default=False,
                     description="apply maxRE weighting"),
        maxRE_scale=Option(default="none",
                           description=("normalisation method for maxRE weights; "
                                        "only relevant if maxRE is set and norm_mean_power is not. "
                                        "options: none, speakers, components, order")),
        point_source_opts=SubOptions(
            handler=point_source.configure_options,
            description="options for point source panner",
        ),
    )

    @options.with_defaults
    def __init__(self, layout, norm_mean_power, maxRE, maxRE_scale, point_source_opts):
        self.psp = point_source.configure(layout, **point_source_opts)

        self._initialised = False

        self.norm_mean_power = norm_mean_power
        self.maxRE = maxRE
        self.maxRE_scale = maxRE_scale

    def init_slow(self):
        """Do the slow bits of the initialisation.

        Optionally call this after this object has been created to speed up the
        first call to design.
        """
        if not self._initialised:
            self._initialised = True
            self.points = hoa.load_points()
            self.G_virt = hoa.allrad_calc_G_virt(self.points, self.psp.handle)

    def design(self, type_metadata):
        """Design a decoder matrix for the given HOA format.

        Args:
            type_metadata (HOATypeMetadata): HOA metadata.

        Returns:
            l, m decoder matrix from m HOA channels to l loudspeaker channels
        """
        self.init_slow()

        if type_metadata.screenRef:
            warnings.warn("screenRef for HOA is not implemented; ignoring")
        if (type_metadata.extra_data.channel_frequency.lowPass is not None or
                type_metadata.extra_data.channel_frequency.highPass is not None):
            warnings.warn("frequency information for HOA is not implemented; ignoring")

        n, m = np.array(type_metadata.orders), np.array(type_metadata.degrees)

        norm = hoa.norm_functions[type_metadata.normalization]
        decoder = hoa.allrad_design(self.points, self.psp.handle, n, m, norm, G_virt=self.G_virt)

        # apply maxRE weights
        if self.maxRE:
            a_n = hoa.ApproxMaxRECoefficients(max(n))[n]

            # various options proposed for scaling maxRE weights to preserve
            # loudness; this is irrelevant if norm_mean_power is used.
            if self.maxRE_scale == "speakers":
                a_n *= np.sqrt(decoder.shape[0] / np.sum(a_n[n]**2))
            elif self.maxRE_scale == "components":
                a_n *= np.sqrt(len(n) / np.sum(a_n[n]**2))
            elif self.maxRE_scale == "order":
                a_n *= np.sqrt(max(n) / np.sum(a_n[n]**2))
            else:
                assert self.maxRE_scale == "none", "unknown maxRE_scale option {!r}".format(self.maxRE_scale)

            decoder *= a_n[n]

        # normalize the decoder so that the mean power is 1 by sampling over
        # the sphere as in the allrad design function
        if self.norm_mean_power:
            az = -np.arctan2(self.points[:, 0], self.points[:, 1])
            el = np.arctan2(self.points[:, 2], np.hypot(self.points[:, 0], self.points[:, 1]))
            K_v = hoa.sph_harm(n[:, np.newaxis], m[:, np.newaxis], az[np.newaxis], el[np.newaxis], norm=norm)
            decoder /= np.sqrt(np.mean(np.sum(np.dot(decoder, K_v) ** 2, axis=0)))

        return decoder
