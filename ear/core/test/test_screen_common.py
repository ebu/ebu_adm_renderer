import numpy as np
from pytest import approx, raises
from ..screen_common import PolarEdges, PolarScreen, CartesianScreen, compensate_position
from ...common import default_screen, PolarPosition, CartesianPosition, cart, azimuth
from ..objectbased.conversion import point_polar_to_cart
from .. import bs2051

default_edge_elevation = np.degrees(np.arctan(np.tan(np.radians(58.0/2.0)) / 1.78))

default_edge_x = point_polar_to_cart(-58.0 / 2.0, 0.0, 1.0)[0]
default_edge_z = point_polar_to_cart(0.0, default_edge_elevation, 1.0)[2]


def test_polar_edges_from_polar():
    screen_edges = PolarEdges.from_screen(default_screen)
    assert np.isclose(screen_edges.left_azimuth, 29.0)
    assert np.isclose(screen_edges.right_azimuth, -29.0)
    assert np.isclose(screen_edges.top_elevation, default_edge_elevation)
    assert np.isclose(screen_edges.bottom_elevation, -default_edge_elevation)


def test_polar_edges_from_polar_left():
    shifted_center_screen = PolarScreen(
        aspectRatio=1.78,
        centrePosition=PolarPosition(
            azimuth=20.0,
            elevation=0.0,
            distance=1.0),
        widthAzimuth=58.0)
    screen_edges = PolarEdges.from_screen(shifted_center_screen)
    assert np.isclose(screen_edges.left_azimuth, 49.0)
    assert np.isclose(screen_edges.right_azimuth, -9.0)
    assert np.isclose(screen_edges.top_elevation, default_edge_elevation)
    assert np.isclose(screen_edges.bottom_elevation, -default_edge_elevation)


def test_polar_edges_from_polar_up():
    shifted_center_screen = PolarScreen(
        aspectRatio=1.78,
        centrePosition=PolarPosition(
            azimuth=0.0,
            elevation=10.0,
            distance=1.0),
        widthAzimuth=58.0)
    screen_edges = PolarEdges.from_screen(shifted_center_screen)
    assert np.isclose(screen_edges.left_azimuth, azimuth(cart(0, 10, 1) - [np.tan(np.radians(58/2)), 0, 0]))
    assert np.isclose(screen_edges.right_azimuth, azimuth(cart(0, 10, 1) + [np.tan(np.radians(58/2)), 0, 0]))
    assert np.isclose(screen_edges.top_elevation, default_edge_elevation + 10)
    assert np.isclose(screen_edges.bottom_elevation, -default_edge_elevation + 10)


def test_polar_edge_error_az():
    screen = PolarScreen(
        aspectRatio=1.78,
        centrePosition=PolarPosition(
            azimuth=161.0,
            elevation=0.0,
            distance=1.0),
        widthAzimuth=40.0)
    expected = "invalid screen specification: screen must not extend past -y"
    with raises(ValueError, match=expected):
        PolarEdges.from_screen(screen)

    screen.centrePosition.azimuth = 159.0
    PolarEdges.from_screen(screen)


def test_polar_edge_error_el():
    screen = PolarScreen(
        aspectRatio=1.0,
        centrePosition=PolarPosition(
            azimuth=30.0,
            elevation=71.0,
            distance=1.0),
        widthAzimuth=40.0)
    expected = "invalid screen specification: screen must not extend past \\+z or -z"
    with raises(ValueError, match=expected):
        PolarEdges.from_screen(screen)

    screen.centrePosition.elevation = 69.0
    PolarEdges.from_screen(screen)


def test_polar_edges_from_cart_default():
    cartesian_default_screen = CartesianScreen(
        aspectRatio=1.78,
        centrePosition=CartesianPosition(
            X=0.0,
            Y=1.0,
            Z=0.0),
        widthX=2 * np.tan(np.radians(58.0/2.0)))
    screen_edges = PolarEdges.from_screen(cartesian_default_screen)
    assert np.isclose(screen_edges.left_azimuth, 29.0)
    assert np.isclose(screen_edges.right_azimuth, -29.0)
    assert np.isclose(screen_edges.top_elevation, default_edge_elevation)
    assert np.isclose(screen_edges.bottom_elevation, -default_edge_elevation)


def test_compensate_position():
    layout = bs2051.get_layout("4+7+0")
    # no compensation
    for el in [-90, -30, 0, 90]:
        for az in [-180, -30, 0, 30, 180]:
            assert compensate_position(az, el, layout) == approx((az, el))

    # full compensation
    for az in [-30, 0, 30]:
        assert compensate_position(az, 30, layout) == approx(((30.0 / 45.0) * az, 30))

    # half compensation
    for az in [-30, 0, 30]:
        assert compensate_position(az, 15, layout) == approx(((37.5 / 45.0) * az, 15))

    # only in layouts with U+-045
    assert compensate_position(30, 30, bs2051.get_layout("0+5+0")) == approx((30, 30))
