from ..extent import calc_basis, azimuth_elevation_on_basis, cart_on_basis, PolarExtentPanner
from ...geom import cart
from ... import bs2051, point_source
import numpy as np
import numpy.testing as npt


def test_basis():
    # cardinal directions
    npt.assert_allclose(calc_basis(cart(0, 0, 1)),
                        np.eye(3), atol=1e-10)
    npt.assert_allclose(calc_basis(cart(90, 0, 1)),
                        [[0, 1, 0],
                         [-1, 0, 0],
                         [0, 0, 1]], atol=1e-10)
    npt.assert_allclose(calc_basis(cart(-90, 0, 1)),
                        [[0, -1, 0],
                         [1, 0, 0],
                         [0, 0, 1]], atol=1e-10)
    npt.assert_allclose(calc_basis(cart(180, 0, 1)),
                        [[-1, 0, 0],
                         [0, -1, 0],
                         [0, 0, 1]], atol=1e-10)
    npt.assert_allclose(calc_basis(cart(0, 90, 1)),
                        [[1, 0, 0],
                         [0, 0, 1],
                         [0, -1, 0]], atol=1e-10)
    npt.assert_allclose(calc_basis(cart(0, -90, 1)),
                        [[1, 0, 0],
                         [0, 0, -1],
                         [0, 1, 0]], atol=1e-10)

    # slight offset from pole should behave as if pointing forwards
    npt.assert_allclose(calc_basis(cart(90, 90-1e-6, 1)),
                        [[1, 0, 0],
                         [0, 0, 1],
                         [0, -1, 0]], atol=1e-7)
    npt.assert_allclose(calc_basis(cart(90, -90+1e-6, 1)),
                        [[1, 0, 0],
                         [0, 0, -1],
                         [0, 1, 0]], atol=1e-7)


def test_az_el_on_basis():
    basis = calc_basis(cart(0, 10, 1))
    npt.assert_allclose(azimuth_elevation_on_basis(basis, cart(0, 10, 1)), (0, 0), atol=1e-10)
    npt.assert_allclose(azimuth_elevation_on_basis(basis, cart(0, 20, 1)), (0, np.radians(10)), atol=1e-10)
    basis = calc_basis(cart(-10, 0, 1))
    npt.assert_allclose(azimuth_elevation_on_basis(basis, cart(-20, 0, 1)), (np.radians(10), 0), atol=1e-10)


def test_cart_on_basis():
    basis = calc_basis(cart(0, 10, 1))
    npt.assert_allclose(cart_on_basis(basis, 0, np.radians(10)), cart(0, 20, 1), atol=1e-10)
    basis = calc_basis(cart(-10, 0, 1))
    npt.assert_allclose(cart_on_basis(basis, np.radians(10), 0), cart(-20, 0, 1), atol=1e-10)


def test_weight_func():
    fade = PolarExtentPanner.fade_width
    height = 10

    for swap in [lambda a, b, *args: (a, b) + args, lambda a, b, *args: (b, a) + args]:
        for width, azimuth in [(20, 0), (360, 0), (360, 180)]:
            elevations = np.linspace(-90, 90)
            points = cart(*swap(azimuth, elevations, 1))
            expected = np.interp(elevations,
                                 [-(height/2+fade), -height/2, height/2, height/2+fade],
                                 [0, 1, 1, 0])
            actual = PolarExtentPanner.get_weight_func(cart(0, 0, 1), *swap(width, height))(points)
            npt.assert_allclose(actual, expected)

        azimuths = np.linspace(-180, 180)
        points = cart(*swap(azimuths, 0, 1))
        expected = np.interp(azimuths,
                             [-(width/2+fade), -width/2, width/2, width/2+fade],
                             [0, 1, 1, 0])
        actual = PolarExtentPanner.get_weight_func(cart(0, 0, 1), *swap(width, height))(points)
        npt.assert_allclose(actual, expected)


def test_pv():
    layout = bs2051.get_layout("9+10+3").without_lfe
    psp = point_source.configure(layout)
    ep = PolarExtentPanner(psp.handle)

    npt.assert_allclose(ep.calc_pv_spread(cart(0, 0, 1), 0, 0), psp.handle(cart(0, 0, 1)))
    npt.assert_allclose(ep.calc_pv_spread(cart(10, 20, 1), 0, 0), psp.handle(cart(10, 20, 1)))

    for pos, tol in [(cart(0, 0, 1), 1e-10), (cart(30, 10, 1), 1e-2)]:
        spread_pv = ep.calc_pv_spread(pos, 20, 10)
        npt.assert_allclose(np.linalg.norm(spread_pv), 1)
        vv = np.dot(spread_pv, layout.positions)
        vv /= np.linalg.norm(vv)
        npt.assert_allclose(vv, pos, atol=tol)
