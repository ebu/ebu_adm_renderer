from ..common import cart, PolarPosition
import numpy.testing as npt
import numpy as np


def test_PolarPosition():
    # check that each attribute is passed through and converted to float
    pos = PolarPosition(10, 11, 1)
    assert pos.azimuth == 10 and isinstance(pos.azimuth, float)
    assert pos.elevation == 11 and isinstance(pos.elevation, float)
    assert pos.distance == 1 and isinstance(pos.distance, float)

    # should have the same behaviour as cart (tested below)
    for az, el in [(0, 0), (0, 30), (30, 0)]:
        npt.assert_allclose(PolarPosition(az, el, 1).as_cartesian_array(), cart(az, el, 1))
        npt.assert_allclose(PolarPosition(az, el, 2).as_cartesian_array(), cart(az, el, 2))
        npt.assert_allclose(PolarPosition(az, el, 2).norm_position, cart(az, el, 1))


def test_cart():
    npt.assert_allclose(cart(0.0, 0.0, 1.0), np.array([0.0, 1.0, 0.0]))
    npt.assert_allclose(cart(0.0, 0.0, 2.0), np.array([0.0, 2.0, 0.0]))
    npt.assert_allclose(cart(45.0, 0.0, np.sqrt(2)), np.array([-1.0, 1.0, 0.0]))
    npt.assert_allclose(cart(0.0, 45.0, np.sqrt(2)), np.array([0.0, 1.0, 1.0]))
