import numpy as np
import numpy.testing as npt
from .. import bs2051
from ..geom import cart
from ..subwoofer import render_subwoofers, subwoofer_upmix_matrix, lfe_downmix_matrix


def test_render_twosubs():
    positions = np.array([
        cart(30, -30, 1),
        cart(-30, -30, 1),
    ])
    npt.assert_allclose(render_subwoofers(positions, cart(0, 0, 1)),
                        [0.5, 0.5])
    npt.assert_allclose(render_subwoofers(positions, cart(30, 0, 1)),
                        [1.0, 0.0])
    npt.assert_allclose(render_subwoofers(positions, cart(30, -30, 1)),
                        [1.0, 0.0])
    npt.assert_allclose(render_subwoofers(positions, cart(-30, 0, 1)),
                        [0.0, 1.0])
    npt.assert_allclose(render_subwoofers(positions, cart(-30, -30, 1)),
                        [0.0, 1.0])
    npt.assert_allclose(render_subwoofers(positions, cart(180, 0, 1)),
                        [0.5, 0.5])


def test_render_onesub():
    positions = np.array([
        cart(0, -30, 1),
    ])
    npt.assert_allclose(render_subwoofers(positions, cart(15, 3, 1)),
                        [1.0])


def test_upmix():
    layout = bs2051.get_layout("0+5+0")
    M = subwoofer_upmix_matrix(layout)

    ident = np.eye(5)
    npt.assert_allclose(M, np.vstack((ident[:3], np.ones((1, 5)), ident[3:])))
    npt.assert_allclose(np.dot(M, [1, 0, 0, 0, 0]), [1, 0, 0, 1, 0, 0])


def test_downmix():
    layout = bs2051.get_layout("0+5+0")
    M = lfe_downmix_matrix(layout)

    npt.assert_allclose(M[layout.is_lfe], 1)
    npt.assert_allclose(M[~layout.is_lfe], 0)
