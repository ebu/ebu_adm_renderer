from ..layout import Channel, Layout, load_speakers, load_real_layout, Speaker, RealLayout
from ..geom import cart, PolarPosition, CartesianPosition
from ...common import PolarScreen, CartesianScreen
from ...compatibility import dump_yaml_str
from attr import evolve
import pytest
import numpy as np
import numpy.testing as npt


@pytest.fixture
def layout():
    # odd nominal positions, for testing
    return Layout(name="test", channels=[
        Channel(name="M+030", polar_position=(30, 0.0, 2.0),
                polar_nominal_position=(25, 0.0, 1.5), az_range=(25, 30), el_range=(0, 0), is_lfe=False),
        Channel(name="M-030", polar_position=PolarPosition(-30, 0.0, 2.0),
                polar_nominal_position=PolarPosition(-25, 0.0, 1.5), az_range=(-30, -25)),
    ])


def test_positions(layout):
    npt.assert_allclose(layout.positions, [cart(30, 0, 2), cart(-30, 0, 2)])


def test_norm_positions(layout):
    npt.assert_allclose(layout.norm_positions, [cart(30, 0, 1), cart(-30, 0, 1)])


def test_nominal_positions(layout):
    npt.assert_allclose(layout.nominal_positions, [cart(25, 0, 1.5), cart(-25, 0, 1.5)])


def test_without_lfe(layout):
    lfe_channel = Channel(name="LFE", polar_position=(30, -20, 2), is_lfe=True)
    layout_lfe = evolve(layout, channels=layout.channels + [lfe_channel])
    assert len(layout_lfe.channels) == 3
    assert len(layout_lfe.without_lfe.channels) == 2


def test_channel_names(layout):
    assert layout.channel_names == ["M+030", "M-030"]


def test_channels_by_name(layout):
    assert layout.channels_by_name == {
        "M+030": layout.channels[0],
        "M-030": layout.channels[1],
    }


def test_default_nominal_range():
    # defaulted nominal position and ranges should be kept when the position is modified
    default_channel = Channel(name="name", polar_position=(10, 20, 1))
    modified_channel = evolve(default_channel, polar_position=PolarPosition(30, 40, 1))
    for channel in [default_channel, modified_channel]:
        assert channel.polar_nominal_position == PolarPosition(10, 20, 1)
        assert channel.az_range == (10, 10)
        assert channel.el_range == (20, 20)


def test_Channel_check_position():
    errors = []
    Channel(name="name", polar_position=(10, 20, 1)).check_position(callback=errors.append)
    Channel(name="name", polar_position=(180, 20, 1), az_range=(175, -175)).check_position(callback=errors.append)
    Channel(name="name", polar_position=(180, 20, 1), az_range=(180, 180)).check_position(callback=errors.append)
    assert not errors

    errors = []
    Channel(name="name", polar_position=(10, 20, 1), az_range=(-5, 5)).check_position(callback=errors.append)
    assert errors == ["name: azimuth 10.0 out of range (-5, 5)."]

    errors = []
    Channel(name="name", polar_position=(10, 20, 1), el_range=(0, 15)).check_position(callback=errors.append)
    assert errors == ["name: elevation 20.0 out of range (0, 15)."]


def test_Layout_check_position(layout):
    errors = []
    layout.check_positions(callback=errors.append)
    assert errors == []

    layout_err = evolve(layout, channels=[
        (evolve(channel, polar_position=PolarPosition(30, 10, 1)) if channel.name == "M+030" else channel)
        for channel in layout.channels])

    errors = []
    layout_err.check_positions(callback=errors.append)
    assert errors == ["M+030: elevation 10.0 out of range (0, 0)."]


def test_Layout_with_speakers_real_layout(layout):
    speakers = [Speaker(channel=1, names=["M+030"], polar_position=PolarPosition(25, 0, 1.5)),
                Speaker(channel=2, names=["M-030"]),
                Speaker(channel=3, names=["M-110"])]
    screen = PolarScreen(aspectRatio=1.5, centrePosition=PolarPosition(10.0, 20.0, 2.0), widthAzimuth=30.0)

    new_layout, upmix = layout.with_speakers(speakers)
    npt.assert_allclose(new_layout.positions, [cart(25, 0, 1.5), cart(-30, 0, 2)])
    npt.assert_allclose(upmix, [[0, 0], [1, 0], [0, 1], [0, 0]])

    new_layout, upmix = layout.with_real_layout(RealLayout(speakers=speakers, screen=screen))
    npt.assert_allclose(new_layout.positions, [cart(25, 0, 1.5), cart(-30, 0, 2)])
    npt.assert_allclose(upmix, [[0, 0], [1, 0], [0, 1], [0, 0]])
    assert new_layout.screen == screen


def test_Layout_check_upmix_matrix(layout):
    errors = []
    upmix = np.array([[0, 0],
                      [1, 0],
                      [0, 0.5],
                      [0, 0]])
    layout.check_upmix_matrix(upmix, callback=errors.append)
    assert errors == []

    errors = []
    upmix = np.array([[0, 0],
                      [1, 0],
                      [0, 0],
                      [0, 0]])
    layout.check_upmix_matrix(upmix, callback=errors.append)
    assert errors == ["Channel M-030 not mapped to any output."]

    errors = []
    upmix = np.array([[0, 0],
                      [1, 0],
                      [0, 1],
                      [0, 1]])
    layout.check_upmix_matrix(upmix, callback=errors.append)
    assert errors == ["Channel M-030 mapped to multiple outputs: [2, 3]."]

    errors = []
    upmix = np.array([[0, 0],
                      [1, 1],
                      [0, 0],
                      [0, 0]])
    layout.check_upmix_matrix(upmix, callback=errors.append)
    assert errors == ["Speaker idx 1 used by multiple channels: ['M+030', 'M-030']"]


def test_load_layout_info():
    def run_test(yaml_obj, expected, func=load_real_layout):
        from six import StringIO
        yaml_str = dump_yaml_str(yaml_obj)

        result = func(StringIO(yaml_str))

        assert expected == result

    run_test(dict(speakers=[dict(channel=0, names="M+000")]),
             RealLayout(speakers=[Speaker(0, ["M+000"])]))

    run_test(dict(speakers=[dict(channel=0, names=["M+000"])]),
             RealLayout(speakers=[Speaker(0, ["M+000"])]))

    run_test(dict(speakers=[dict(channel=0, names=["M+000"], position=dict(az=10, el=5, r=1))]),
             RealLayout(speakers=[Speaker(0, ["M+000"], PolarPosition(10, 5, 1))]))

    run_test(dict(speakers=[dict(channel=0, names=["M+000"], gain_linear=0.5)]),
             RealLayout(speakers=[Speaker(0, ["M+000"], gain_linear=0.5)]))

    with pytest.raises(Exception) as excinfo:
        run_test(dict(speakers=[dict(channel=0, names=["M+000"], position=dict(az=10, el=5))]),
                 RealLayout(speakers=[Speaker(0, ["M+000"], PolarPosition(10, 5, 1))]))
        assert "Unknown position format" in str(excinfo.value)

    # old style with speakers at the top level
    run_test([dict(channel=0, names="M+000")],
             RealLayout(speakers=[Speaker(0, ["M+000"])]))

    # polar screen
    run_test(dict(screen=dict(type="polar", aspectRatio=1.5, centrePosition=dict(az=10, el=20, r=2), widthAzimuth=30)),
             RealLayout(screen=PolarScreen(aspectRatio=1.5, centrePosition=PolarPosition(10.0, 20.0, 2.0), widthAzimuth=30.0)))

    # Cartesian screen
    run_test(dict(screen=dict(type="cart", aspectRatio=1.5, centrePosition=dict(X=0.1, Y=0.9, Z=0.2), widthX=0.3)),
             RealLayout(screen=CartesianScreen(aspectRatio=1.5, centrePosition=CartesianPosition(0.1, 0.9, 0.2), widthX=0.3)))

    # passes through null screens
    run_test(dict(screen=None),
             RealLayout(screen=None))

    # legacy speakers wrapper
    run_test(dict(speakers=[dict(channel=0, names="M+000")]),
             [Speaker(0, ["M+000"])],
             func=load_speakers)
