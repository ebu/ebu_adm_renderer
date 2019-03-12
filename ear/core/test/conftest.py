from .. import bs2051
from ..layout import Speaker
from ..geom import PolarPosition
import pytest

layout_names, layouts = [], []

for layout_name in bs2051.layout_names:
    layout_names.append(layout_name)
    layouts.append(bs2051.get_layout(layout_name))


wide_screen_speakers = [
    Speaker(channel=0,
            names=["M+SC"], polar_position=PolarPosition(azimuth=45.0,
                                                         elevation=0.0,
                                                         distance=1.0)),
    Speaker(channel=1,
            names=["M-SC"], polar_position=PolarPosition(azimuth=-45.0,
                                                         elevation=0.0,
                                                         distance=1.0)),
]

layout_names.append("4+9+0 wide")
layouts.append(bs2051.get_layout("4+9+0").with_speakers(wide_screen_speakers)[0])


@pytest.fixture(params=layouts, ids=layout_names)
def layout_with_lfe(request):
    """Layout object."""
    return request.param


@pytest.fixture
def layout(layout_with_lfe):
    return layout_with_lfe.without_lfe
