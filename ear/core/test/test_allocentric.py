from ..allocentric import positions_for_layout
from .. import bs2051
from .. import layout
from .. import geom
import numpy.testing as npt
import pytest


@pytest.mark.parametrize("x, az", [
    (0.0, 0.0),
    (1.0, 30.0),
    (0.5, 15.0),
])
def test_screen_pos(x, az):
    speakers = [
        layout.Speaker(channel=0,
                       names=["M+SC"], polar_position=geom.PolarPosition(azimuth=az,
                                                                         elevation=0.0,
                                                                         distance=1.0)),
        layout.Speaker(channel=1,
                       names=["M-SC"], polar_position=geom.PolarPosition(azimuth=-az,
                                                                         elevation=0.0,
                                                                         distance=1.0)),
    ]

    layout_mod, _upmix = bs2051.get_layout("4+9+0").without_lfe.with_speakers(speakers)

    positions = positions_for_layout(layout_mod)

    npt.assert_allclose([x, 1.0, 0.0], positions[layout_mod.channel_names.index("M-SC")])
    npt.assert_allclose([-x, 1.0, 0.0], positions[layout_mod.channel_names.index("M+SC")])


@pytest.mark.parametrize("layout_name", bs2051.layout_names)
def test_all_layouts(layout_name):
    layout = bs2051.get_layout(layout_name).without_lfe
    positions_for_layout(layout)
