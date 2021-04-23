from ..conversion import to_cartesian, to_polar, point_cart_to_polar, point_polar_to_cart, Conversion
from ....fileio.adm.elements import AudioBlockFormatObjects, ObjectCartesianPosition, ObjectPolarPosition
from attr import asdict
import numpy as np
import numpy.testing as npt
import pytest
from pytest import approx


def check_bf_equal(a, b):
    dict_a = asdict(a)
    dict_B = asdict(b)

    pos_a = dict_a.pop("position")
    pos_b = dict_B.pop("position")

    assert ("azimuth" in pos_a) == ("azimuth" in pos_b)

    if "azimuth" in pos_a:
        azimuth_a, elevation_a, distance_a = pos_a.pop("azimuth"), pos_a.pop("elevation"), pos_a.pop("distance")
        azimuth_b, elevation_b, distance_b = pos_b.pop("azimuth"), pos_b.pop("elevation"), pos_b.pop("distance")

        assert elevation_a == approx(elevation_b)
        if np.abs(elevation_a) < 90.0 - 1e6:
            assert azimuth_a == approx(azimuth_b)
        assert distance_a == approx(distance_b)
    elif "X" in pos_a:
        x_a, y_a, z_a = pos_a.pop("X"), pos_a.pop("Y"), pos_a.pop("Z")
        x_b, y_b, z_b = pos_b.pop("X"), pos_b.pop("Y"), pos_b.pop("Z")

        assert x_a == approx(x_b)
        assert y_a == approx(y_b)
        assert z_a == approx(z_b)
    else:
        assert False

    assert pos_a == pos_b

    assert dict_a == dict_B


@pytest.mark.parametrize("bf", [
    AudioBlockFormatObjects(position=ObjectPolarPosition(azimuth=az, elevation=el, distance=dist))
    for az in [0.0, -10.0, 10.0, 90.0, -90.0, 150.0, -150.0]
    for el in [0.0, -10.0, 10.0, -45.0, 45.0, -90, 90.0]
    for dist in [0.5, 1.0]
])
def test_cartesian_polar_loop(bf):
    bf_cart = to_cartesian(bf)
    bf_polar = to_polar(bf_cart)
    check_bf_equal(bf, bf_polar)


def test_conversion_corners():
    for el, z in (-30, -1), (0, 0), (30, 1):
        for az, x, y in [(0, 0, 1), (-30, 1, 1), (30, -1, 1), (-110, 1, -1), (110, -1, -1)]:
            for d in [0.5, 1, 2]:
                if el == 0 or az != 0:
                    npt.assert_allclose(point_polar_to_cart(az, el, d),
                                        [x*d, y*d, z*d], atol=1e-10)
                    npt.assert_allclose(point_cart_to_polar(x*d, y*d, z*d),
                                        (az, el, d), atol=1e-10)


def test_conversion_poles():
    for sign in [-1, 1]:
        for d in [0.5, 1, 2]:
            npt.assert_allclose(point_polar_to_cart(0, sign * 90, d),
                                [0.0, 0.0, sign * d], atol=1e-10)
            npt.assert_allclose(point_cart_to_polar(0.0, 0.0, sign * d),
                                (0, sign * 90, d), atol=1e-10)


def test_conversion_centre():
    for az in [-90, 0, 90]:
        for el in [-90, 0, 90]:
            npt.assert_allclose(point_polar_to_cart(az, el, 0.0),
                                [0.0, 0.0, 0.0], atol=1e-10)

    _az, _el, dist = point_cart_to_polar(0.0, 0.0, 0.0)
    assert dist == approx(0.0)


def test_conversion_reversible():
    n = 1000
    pos_cart = np.random.uniform(-2, 1, (n, 3))
    for pos in pos_cart:
        az, el, d = point_cart_to_polar(*pos)
        pos2 = point_polar_to_cart(az, el, d)
        npt.assert_allclose(pos, pos2, atol=1e-10)


def test_map_linear_az():
    assert Conversion._map_az_to_linear(0, -30, 0) == approx(0)
    assert Conversion._map_az_to_linear(0, -30, -30) == approx(1)
    assert Conversion._map_az_to_linear(0, -30, -15) == approx(0.5)

    # test reversible
    for az in np.linspace(0, 30):
        x = Conversion._map_az_to_linear(0, -30, az)
        assert Conversion._map_linear_to_az(0, -30, x) == approx(az)


# tests for mapping between width height and depth at different positions
whd_mappings = [
    # azimuth, elevation, Cartesian equivalent of Width, Height, Depth
    (0.0, 0.0, "whd"),
    (90.0, 0.0, "dhw"),  # polar width -> Cartesian depth etc.
    (-90.0, 0.0, "dhw"),
    (180.0, 0.0, "whd"),
    (0.0, 90.0, "wdh"),
    (0.0, -90.0, "wdh"),
]


@pytest.mark.parametrize("az,el,whd", whd_mappings)
@pytest.mark.parametrize("polar_axis", "whd")
def test_whd_mapping_to_cartesian(az, el, whd, polar_axis):
    cart_axis = "whd"[whd.index(polar_axis)]

    bf = AudioBlockFormatObjects(
        position=ObjectPolarPosition(az, el, 1.0),
        cartesian=False,
        width=20.0 if polar_axis == "w" else 0.0,
        height=20.0 if polar_axis == "h" else 0.0,
        depth=0.2 if polar_axis == "d" else 0.0,
    )
    bf_c = to_cartesian(bf)
    assert cart_axis == "whd"[np.argmax([bf_c.width, bf_c.height, bf_c.depth])]


@pytest.mark.parametrize("az,el,whd", whd_mappings)
@pytest.mark.parametrize("polar_axis", "whd")
def test_whd_mapping_to_polar(az, el, whd, polar_axis):
    cart_axis = "whd"[whd.index(polar_axis)]
    bf = AudioBlockFormatObjects(
        position=ObjectCartesianPosition(*point_polar_to_cart(az, el, 1.0)),
        cartesian=True,
        width=0.1 if cart_axis == "w" else 0.0,
        height=0.1 if cart_axis == "h" else 0.0,
        depth=0.1 if cart_axis == "d" else 0.0,
    )
    bf_p = to_polar(bf)
    assert polar_axis == "whd"[np.argmax([bf_p.width, bf_p.height, bf_p.depth * 10])]
