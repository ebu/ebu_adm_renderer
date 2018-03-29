import numpy as np
from ..screen_common import PolarEdges, PolarScreen, CartesianEdges, CartesianScreen
from ...common import default_screen, PolarPosition, CartesianPosition, cart, azimuth

default_edge_elevation = np.degrees(np.arctan(np.tan(np.radians(58.0/2.0)) / 1.78))


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


def test_cartesian_edges():
    screen_edges = CartesianEdges.from_screen(default_screen)
    assert np.isclose(screen_edges.left_X, -0.554309051452769)
    assert np.isclose(screen_edges.right_X, 0.554309051452769)
    assert np.isclose(screen_edges.top_Z, 0.31140957946784775)
    assert np.isclose(screen_edges.bottom_Z, -0.31140957946784775)

    cartesian_default_screen = CartesianScreen(
        aspectRatio=1.78,
        centrePosition=CartesianPosition(
            X=0.0,
            Y=1.0,
            Z=0.0),
        widthX=1.108618102905538)
    screen_edges = CartesianEdges.from_screen(cartesian_default_screen)
    assert np.isclose(screen_edges.left_X, -0.554309051452769)
    assert np.isclose(screen_edges.right_X, 0.554309051452769)
    assert np.isclose(screen_edges.top_Z, 0.31140957946784775)
    assert np.isclose(screen_edges.bottom_Z, -0.31140957946784775)
