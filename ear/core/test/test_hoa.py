import numpy as np
import numpy.testing as npt
import pytest
from .. import hoa


def test_acn():
    acn = 0
    for n in range(10):
        for m in range(-n, n+1):
            assert hoa.to_acn(n, m) == acn
            assert hoa.from_acn(acn) == (n, m)
            acn += 1


def test_Alegendre():
    # associsted Legendre polynomials for specific n, m, including the
    # condon-shortley phase.
    # from http://mathworld.wolfram.com/AssociatedLegendrePolynomial.html
    testcases = {
        (0, 0): lambda x: 1.0,
        (1, 0): lambda x: x,
        (1, 1): lambda x: -np.sqrt(1-x**2.0),
        (2, 0): lambda x: 0.5 * (3.0 * x**2.0 - 1.0),
        (2, 1): lambda x: -3.0 * x * np.sqrt(1.0 - x**2.0),
        (2, 2): lambda x: 3.0 * (1.0 - x**2),
    }

    @np.vectorize
    def test_Alegendre(n, m, x):
        # test version of hoa.Alegendre without the condon-shortley phase
        return (-1.0)**m * testcases[(n, m)](x)

    x = np.linspace(0, 1, 10)
    n, m = np.array(list(testcases)).T

    N, M, X = np.broadcast_arrays(n, m, x[:, np.newaxis])

    expected_res = test_Alegendre(N, M, X)
    res = hoa.Alegendre(N, M, X)
    npt.assert_allclose(res, expected_res)

    # test cases from "Ambix-a suggested ambisonics format."
    npt.assert_allclose(hoa.Alegendre(np.arange(4), np.arange(4), 0.0),
                        [1, 1, 3, 15])


def test_sph_harm_first_order():  # noqa
    # check that first order gives the same results as b-format panning

    # conversion matrix from "Ambix-a suggested ambisonics format.", omitting
    # the W scale both here and in testcases.
    b_to_acn = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1], [0, 1, 0, 0]])
    acn_to_b = b_to_acn.T

    testcases = [
    #   ((az,   el), [W,  X,  Y,  Z]),  # noqa: E122
        ((0,     0), [1,  1,  0,  0]),  # noqa: E241
        ((90,    0), [1,  0,  1,  0]),  # noqa: E241
        ((-90,   0), [1,  0, -1,  0]),  # noqa: E241
        ((180,   0), [1, -1,  0,  0]),  # noqa: E241
        ((0,    90), [1,  0,  0,  1]),  # noqa: E241
        ((0,   -90), [1,  0,  0, -1]),  # noqa: E241
    ]

    azimuths   = np.array([az for (az, el), xs in testcases])  # noqa: E221
    elevations = np.array([el for (az, el), xs in testcases])  # noqa: E221
    expected_b = np.array([xs for (az, el), xs in testcases])  # noqa: E221

    n, m = hoa.from_acn(np.arange(4))

    res_acn = hoa.sph_harm(n[np.newaxis], m[np.newaxis],
                           np.radians(azimuths)[:, np.newaxis],
                           np.radians(elevations)[:, np.newaxis])
    res_b = np.dot(acn_to_b, res_acn.T).T

    npt.assert_allclose(res_b, expected_b, atol=1e-10)


def test_allrad_design():
    from .. import bs2051
    from .. import point_source

    layout = bs2051.get_layout("4+5+0").without_lfe
    psp = point_source.configure(layout)

    order = 3
    n, m = hoa.from_acn(range((order + 1)**2))

    points = hoa.load_points()
    decoder = hoa.allrad_design(points, psp.handle, n, m)

    assert decoder.shape == (psp.num_channels, len(n))

    # test that for each channel, encoding an HOA signal located at the
    # position of this channel results in that channel having the largest gain
    # after decoding; this is not guaranteed in general, but should be true for
    # high orders and small layouts
    for i, channel in enumerate(layout.channels):
        # hoa coord system is in radians
        az, el = np.radians([channel.polar_position.azimuth,
                             channel.polar_position.elevation])

        encoded = hoa.sph_harm(n, m, az, el)
        decoded = np.dot(decoder, encoded)
        assert np.argmax(decoded) == i


@pytest.mark.filterwarnings("ignore::SyntaxWarning")
def test_maxRE():
    """Check that the approximate and numeric versions of maxRE are compatible."""
    for order in range(1, 5):
        npt.assert_allclose(
            hoa.ApproxMaxRECoefficients(order),
            hoa.MaxRECoefficients(order),
            rtol=1e-2)


def plot_sph_harm(n, m):
    """Plot the spherical harmonics with order n and degree m."""
    az, el = np.ogrid[-180:181:5, -90:91:5]
    value = hoa.sph_harm(n, m, np.radians(az), np.radians(el))

    from ..geom import cart
    x, y, z = cart(az, el, np.abs(value))

    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa

    fig = plt.figure()
    plt.title("Spherical harmonic order {n} degree {m}".format(n=n, m=m))
    plt.axis('off')
    ax = fig.add_subplot(111, projection='3d', aspect=1)

    colors = np.empty(value.shape, dtype=str)
    colors[value > 0] = "r"
    colors[value <= 0] = "b"

    ax.plot_surface(x, y, z, facecolors=colors)

    ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_zlim(-1, 1)
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z")

    plt.show()
