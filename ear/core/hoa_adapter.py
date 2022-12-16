import numpy as np
import re
from ..common import CartesianScreen, PolarScreen, default_screen
from . import hoa
from attr import attrib, attrs
from attr.validators import instance_of, optional

HOA_FORMAT_RE = re.compile("hoa_([^_]+)_([^_]+)_([0-9]+)")
AMBIX_RE = re.compile("ambix_([^_]+)")


@attrs
class HOAFormat:
    max_order = attrib()
    normalization = attrib(default="SN3D")
    channel_order = attrib(default="ACN")

    screen = attrib(
        validator=optional(instance_of((CartesianScreen, PolarScreen))),
        default=default_screen,
    )

    @property
    def num_channels(self):
        return (self.max_order + 1) ** 2

    @property
    def without_lfe(self):
        return self

    @property
    def is_lfe(self):
        return np.zeros(self.num_channels, dtype=bool)

    @property
    def orders_degrees(self):
        assert self.channel_order == "ACN"

        n = (self.max_order + 1) ** 2
        acn = np.arange(n)
        return hoa.from_acn(acn)

    @property
    def norm_fn(self):
        return hoa.norm_functions[self.normalization]

    @classmethod
    def parse_or_none(cls, fmt_string):
        match = HOA_FORMAT_RE.fullmatch(fmt_string)
        if match is not None:
            normalization, channel_order, max_order_str = match.groups()
            return cls(
                normalization=normalization,
                channel_order=channel_order,
                max_order=int(max_order_str),
            )

        match = AMBIX_RE.fullmatch(fmt_string)
        if match is not None:
            (max_order_str,) = match.groups()
            return cls(
                normalization="SN3D", channel_order="ACN", max_order=int(max_order_str)
            )


@attrs
class HOAPointSourceAdapter:
    norm = attrib()
    max_order = attrib()
    orders = attrib()
    degrees = attrib()

    @classmethod
    def build(cls, fmt: HOAFormat):
        orders, degrees = fmt.orders_degrees

        return cls(
            norm=hoa.norm_functions[fmt.normalization],
            max_order=fmt.max_order,
            orders=orders,
            degrees=degrees,
        )

    @property
    def num_channels(self):
        return len(self.orders)

    def handle(self, position):
        x, y, z = position
        az = -np.arctan2(x, y)
        el = np.arctan2(z, np.hypot(x, y))

        return hoa.sph_harm(self.orders, self.degrees, az, el, self.norm)
