from ..geom import azimuth, elevation, cart, relative_angle, inside_angle_range, ngon_vertex_order, local_coordinate_system
import numpy as np
import numpy.testing as npt


def test_azimuth():
    npt.assert_allclose(azimuth(np.array([1.0, 1.0, 0.0])), -45)


def test_elevation():
    npt.assert_allclose(elevation(np.array([0.0, 1.0, 1.0])), 45)
    npt.assert_allclose(elevation(np.array([np.sqrt(2), np.sqrt(2), 2.0])), 45)


def test_relative_angle():
    assert relative_angle(0, 10) == 10
    assert relative_angle(10, 10) == 10
    assert relative_angle(11, 10) == 370
    assert relative_angle(370, 10) == 370
    assert relative_angle(371, 10) == 360 + 370


def test_inside_angle_range():
    assert inside_angle_range(0, 0, 10)
    assert inside_angle_range(5, 0, 10)
    assert inside_angle_range(10, 0, 10)

    assert inside_angle_range(0, 10, 00)
    assert not inside_angle_range(5, 10, 0)
    assert inside_angle_range(15, 10, 0)
    assert inside_angle_range(10, 10, 0)

    assert inside_angle_range(0, -10, 10)
    assert not inside_angle_range(180, -10, 10)
    assert not inside_angle_range(-180, -10, 10)

    assert inside_angle_range(0, -180, 180)
    assert not inside_angle_range(0, -181, 181)
    assert inside_angle_range(0, -180, 180, 1)

    assert inside_angle_range(180, 180, -180)
    assert inside_angle_range(180, 180, -180, 1)
    assert not inside_angle_range(90, 180, -180)

    assert inside_angle_range(0, 0, 0)
    assert inside_angle_range(0, 0, 0, 1)
    assert not inside_angle_range(90, 0, 0)

    assert inside_angle_range(0, 1, 2, 2)
    assert inside_angle_range(-1, 1, 2, 2)
    assert inside_angle_range(359, 1, 2, 2)


def test_order_vertices():
    import itertools

    def random_linear_transforms(ngon):
        yield ngon

        for i in range(10):
            T = np.random.normal(size=(3, 3))
            offset = np.random.normal(size=3)

            # ... providing that the transform isn't rank deficient
            if np.linalg.matrix_rank(T, tol=1e-3) < 3:
                continue

            yield ngon.dot(T) + offset

    def no_random(ngon):
        yield ngon

    ordered_ngons = [
        (random_linear_transforms, np.array([cart(30, 0, 1), cart(-30, 0, 1),
                                             cart(-30, 30, 1), cart(30, 30, 1)])),
        (no_random, np.array([cart(30, 0, 1), cart(0, 0, 1), cart(-30, 0, 1),
                              cart(-30, 30, 1), cart(30, 30, 1)])),
        (random_linear_transforms, np.array([cart(30, 30, 1), cart(-30, 30, 1),
                                             cart(-110, 30, 1), cart(110, 30, 1)])),
        (random_linear_transforms, np.array([cart(30, 30, 1), cart(0, 30, 1), cart(-30, 30, 1),
                                             cart(-110, 30, 1), cart(110, 30, 1)])),
        (random_linear_transforms, np.array([cart(30, 0, 1), cart(0, 0, 1), cart(-30, 0, 1),
                                             cart(-110, 0, 1), cart(110, 0, 1)])),
    ]

    def in_same_order(a, b):
        """Are a and b the same, module some reversal or shift?"""
        # just produce all shifted and reversed versions of a, and compare
        # against b. Inefficient but simple.
        for offset in range(len(a)):
            a_shift = np.concatenate((a[offset:], a[:offset]))
            for reversal in (1, -1):
                a_reorder = a_shift[::reversal]
                if np.all(a_reorder == b):
                    return True
        return False

    for randomize, ordered_ngon in ordered_ngons:
        for ordered_ngon_T in randomize(ordered_ngon):
            # for each permutation, check that reordering results in the same
            # ordering out
            for unordered_ngon in itertools.permutations(ordered_ngon_T):
                order = ngon_vertex_order(unordered_ngon)
                reordered_ngon = np.array(unordered_ngon)[order]

                assert in_same_order(reordered_ngon, ordered_ngon_T)


def test_local_coordinate_system():
    x, y, z = np.eye(3)
    npt.assert_allclose(local_coordinate_system(0, 0),
                        [x, y, z], atol=1e-15)
    npt.assert_allclose(local_coordinate_system(-90, 0),
                        [-y, x, z], atol=1e-15)
    npt.assert_allclose(local_coordinate_system(90, 0),
                        [y, -x, z], atol=1e-15)
    npt.assert_allclose(local_coordinate_system(180, 0),
                        [-x, -y, z], atol=1e-15)

    npt.assert_allclose(local_coordinate_system(0, 90),
                        [x, z, -y], atol=1e-15)
    npt.assert_allclose(local_coordinate_system(0, -90),
                        [x, -z, y], atol=1e-15)

    npt.assert_allclose(local_coordinate_system(-90, 90),
                        [-y, z, -x], atol=1e-15)
