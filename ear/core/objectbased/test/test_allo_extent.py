from ..allo_extent import (_scale_size, _s_eff, _p, _h, _d_bound, _mu, _calc_w,
                           _calc_f, _dim, _find_plane_z, _find_row_y,
                           _find_column_x, _calc_g_point_separated, _calc_Nz, get_gains)
import numpy as np
import numpy.testing as npt
# flake8: noqa


def speaker_positions(names):
    P = lambda x, y, z: np.array([x, y, z])
    pos = {"M+000": P( 0.0,      1.0,       0.0),
           "M+SC":  P(-0.414214, 1.0,       0.0),
           "M-SC":  P( 0.414214, 1.0,       0.0),
           "M+030": P(-1.0,      1.0,       0.0),
           "M-030": P( 1.0,      1.0,       0.0),
           "M+060": P(-1.0,      0.414214,  0.0),
           "M-060": P( 1.0,      0.414214,  0.0),
           "M+090": P(-1.0,      0.0,       0.0),
           "M-090": P( 1.0,      0.0,       0.0),
           "M+110": P(-1.0,     -1.0,       0.0),  # M?110 and M?135 are treated as synonyms
           "M-110": P( 1.0,     -1.0,       0.0),
           "M+135": P(-1.0,     -1.0,       0.0),
           "M-135": P( 1.0,     -1.0,       0.0),
           "M+180": P( 0.0,     -1.0,       0.0),
           "U+000": P( 0.0,      1.0,       1.0),
           "U+030": P(-1.0,      1.0,       1.0),  # U?030 and U?045 are treated as synonyms
           "U-030": P( 1.0,      1.0,       1.0),
           "U+045": P(-1.0,      1.0,       1.0),
           "U-045": P( 1.0,      1.0,       1.0),
           "U+090": P(-1.0,      0.0,       1.0),
           "U-090": P( 1.0,      0.0,       1.0),
           "U+110": P(-1.0,     -1.0,       1.0),  # U?110 and U?135 are treated as synonyms
           "U-110": P( 1.0,     -1.0,       1.0),
           "U+135": P(-1.0,     -1.0,       1.0),
           "U-135": P( 1.0,     -1.0,       1.0),
           "U+180": P( 0.0,     -1.0,       1.0),
           "T+000": P( 0.0,      0.0,       1.0),
           "B+000": P( 0.0,      1.0,      -1.0),
           "B+045": P(-1.0,      1.0,      -1.0),
           "B-045": P( 1.0,      1.0,      -1.0)}
    return np.array([pos[s] for s in names])


def test_allo_extent_scale_size():
    # Check interpolation boundary points
    npt.assert_almost_equal(_scale_size(0.0), 0.0)
    npt.assert_almost_equal(_scale_size(0.2), 0.3)
    npt.assert_almost_equal(_scale_size(0.5), 1.0)
    npt.assert_almost_equal(_scale_size(0.75), 1.8)
    npt.assert_almost_equal(_scale_size(1.0), 2.8)

    # Check interpolation quarter and 3-quarter points
    npt.assert_almost_equal(_scale_size(0.2 * (1.0 / 4.0)), 0.3 * (1.0 / 4.0))
    npt.assert_almost_equal(_scale_size(0.2 * (3.0 / 4.0)), 0.3 * (3.0 / 4.0))

    npt.assert_almost_equal(_scale_size(0.2 + 0.3 * (1.0 / 4.0)), 0.3 + 0.7 * (1.0 / 4.0))
    npt.assert_almost_equal(_scale_size(0.2 + 0.3 * (3.0 / 4.0)), 0.3 + 0.7 * (3.0 / 4.0))

    npt.assert_almost_equal(_scale_size(0.2 + 0.3 + 0.25 * (1.0 / 4.0)), 0.3 + 0.7 + 0.8 * (1.0 / 4.0))
    npt.assert_almost_equal(_scale_size(0.2 + 0.3 + 0.25 * (3.0 / 4.0)), 0.3 + 0.7 + 0.8 * (3.0 / 4.0))

    npt.assert_almost_equal(_scale_size(0.2 + 0.3 + 0.25 + 0.25 * (1.0 / 4.0)), 0.3 + 0.7 + 0.8 + 1.0 * (1.0 / 4.0))
    npt.assert_almost_equal(_scale_size(0.2 + 0.3 + 0.25 + 0.25 * (3.0 / 4.0)), 0.3 + 0.7 + 0.8 + 1.0 * (3.0 / 4.0))

    # Test clipping
    npt.assert_almost_equal(_scale_size(1.5), 2.8)
    npt.assert_almost_equal(_scale_size(2.0), 2.8)
    npt.assert_almost_equal(_scale_size(3.0), 2.8)


def test_allo_extent_s_eff():
    sp = speaker_positions

    # 1D cases => Expect _s_eff to be size_x
    speaker_positions_A = sp(["M+030", "M-030"])
    npt.assert_almost_equal(_s_eff(speaker_positions_A, 0.0,  0.5, 1.0), 0.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_A, 0.25, 0.5, 1.0), 0.25)
    npt.assert_almost_equal(_s_eff(speaker_positions_A, 0.5,  0.0, 0.0), 0.5)

    # Adding in the M+000 speaker should keep this as a 1D case
    npt.assert_almost_equal(_s_eff(sp(["M+030", "M-030", "M+000"]), 0.5, 0.25, 0.75), 0.5)

    # Just M-110 and M+110 speakers is also 1D
    npt.assert_almost_equal(_s_eff(sp(["M-110", "M+110"]), 0.5, 0.25, 0.75), 0.5)

    # 2D cases => Expect _s_eff to be 0.75*s1 + 0.25*s2 for s1, s2 = descend_sorted(size_x, size_y)
    speaker_positions_B = sp(["M+000", "M+030", "M-030", "M+110", "M-110"])
    npt.assert_almost_equal(_s_eff(speaker_positions_B, 1.0, 0.0, 0.0), 0.75 * 1.0 + 0.25 * 0.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_B, 0.0, 1.0, 0.0), 0.75 * 1.0 + 0.25 * 0.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_B, 0.0, 0.0, 1.0), 0.75 * 0.0 + 0.25 * 0.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_B, 1.0, 1.0, 0.0), 0.75 * 1.0 + 0.25 * 1.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_B, 0.5, 1.0, 0.0), 0.75 * 1.0 + 0.25 * 0.5)

    # Adding M+090 and M-090 speakers is still 2D
    npt.assert_almost_equal(_s_eff(sp(["M+000", "M+030", "M-030", "M+110", "M-110", "M+090", "M-090"]), 0.5, 1.0, 0.25), 0.75 * 1.0 + 0.25 * 0.5)

    # 3D cases => Expect _s_eff to be (6/9)s1 + (2/9)s2 + (1/9)s3 for s1, s2 = descend_sorted(size_x, size_y, size_z)
    speaker_positions_C = sp(["M+000", "M-030", "M-030", "M+110", "M-110", "U+030", "U-030"])
    npt.assert_almost_equal(_s_eff(speaker_positions_C, 1.0, 0.0, 0.0 ), (6 * 1.0 + 2 * 0.0 + 1 * 0.0 ) / 9.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_C, 0.0, 1.0, 0.0 ), (6 * 1.0 + 2 * 0.0 + 1 * 0.0 ) / 9.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_C, 0.0, 0.0, 1.0 ), (6 * 1.0 + 2 * 0.0 + 1 * 0.0 ) / 9.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_C, 1.0, 1.0, 0.0 ), (6 * 1.0 + 2 * 1.0 + 1 * 0.0 ) / 9.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_C, 0.0, 1.0, 1.0 ), (6 * 1.0 + 2 * 1.0 + 1 * 0.0 )  / 9.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_C, 1.0, 0.0, 1.0 ), (6 * 1.0 + 2 * 1.0 + 1 * 0.0 ) / 9.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_C, 1.0, 1.0, 1.0 ), (6 * 1.0 + 2 * 1.0 + 1 * 1.0 ) / 9.0)
    npt.assert_almost_equal(_s_eff(speaker_positions_C, 1.0, 0.5, 0.25), (6 * 1.0 + 2 * 0.5 + 1 * 0.25) / 9.0)


def test_allo_extent_p():
    # p = 6                          if s_eff <= 0.5
    #          (s_eff - 0.5)
    #   = 6 +  ------------- * -4    if s_eff > 0.5
    #          (s_max - 0.5)
    #
    # where s_max = 2.8
    npt.assert_almost_equal(_p(0.0), 6.0)
    npt.assert_almost_equal(_p(0.25), 6.0)
    npt.assert_almost_equal(_p(0.5), 6.0)

    npt.assert_almost_equal(_p(1.0), 6.0 + ((0.5 / 2.3) * -4))
    npt.assert_almost_equal(_p(2.0), 6.0 + ((1.5 / 2.3) * -4))
    npt.assert_almost_equal(_p(2.8), 2.0)


def test_allo_extent_h():
    #                     [ max(2s, 0.4)^3 ]^(1/3)
    # h(c, s, d_bound) =  [ -------------- ]                 if d_bound >= 2*s and d_bound >= 0.4
    #                     [    0.16 * 2s   ]

    # Note that 'c' isn't used, so we don't even take it as a parameter
    # in our reference
    def h1(s, d_bound):
        return ((max(2.0*s, 0.4) ** 3.0) / (0.16 * 2.0 * s)) ** (1.0/3.0)

    npt.assert_almost_equal(_h(0.0, 0.2,  0.4), h1(0.2,  0.4))
    npt.assert_almost_equal(_h(1.0, 0.2,  0.5), h1(0.2,  0.5))
    npt.assert_almost_equal(_h(0.5, 0.25, 0.5), h1(0.25, 0.5))
    npt.assert_almost_equal(_h(0.4, 0.2,  0.6), h1(0.2,  0.6))
    npt.assert_almost_equal(_h(0.3, 0.25, 0.6), h1(0.25, 0.6))
    npt.assert_almost_equal(_h(0.2, 0.3,  0.6), h1(0.3,  0.6))

    #                    [ d_bound   ( d_bound )^2 ]^(1/3)
    # h(c, s, d_bound) = [ ------- * ( ------- )   ]        otherwise
    #                    [    2      (   0.4   )   ]
    def h2(s, d_bound):
        return (((d_bound / 0.4) ** 2.0) * (d_bound/(2.0))) ** (1.0 / 3.0)

    npt.assert_almost_equal(_h(0.0, 0.2,  0.3), h2(0.2,  0.3))
    npt.assert_almost_equal(_h(0.0, 0.2,  0.2), h2(0.2,  0.2))
    npt.assert_almost_equal(_h(0.0, 0.2,  0.1), h2(0.2,  0.1))
    npt.assert_almost_equal(_h(0.0, 0.2,  0.0), h2(0.2,  0.0))
    npt.assert_almost_equal(_h(0.0, 0.25, 0.4), h2(0.25, 0.4))
    npt.assert_almost_equal(_h(0.0, 0.25, 0.3), h2(0.25, 0.3))
    npt.assert_almost_equal(_h(0.0, 0.25, 0.2), h2(0.25, 0.2))
    npt.assert_almost_equal(_h(0.0, 0.25, 0.1), h2(0.25, 0.1))
    npt.assert_almost_equal(_h(0.0, 0.25, 0.0), h2(0.25, 0.0))

    # We expect the piecemeal function to be continuous
    # npt.assert_almost_equal(h1(0.4, 0.4), h2(0.4, 0.4))
    # npt.assert_almost_equal(h1(0.5, 0.5), h2(0.5, 0.5))
    # npt.assert_almost_equal(h1(0.6, 0.6), h2(0.6, 0.6))
    # npt.assert_almost_equal(h1(0.7, 0.7), h2(0.7, 0.7))


def test_allo_extent_d_bound():
    #                            { min(xo + 1, 1 - xo)                                   if dim=1
    # d_bound(dim, xo, yo, zo) = { min(xo + 1, 1 - xo, yo + 1, 1 - yo)                   if dim=2
    #                            { min(xo + 1, 1 - xo, yo + 1, 1 - yo, zo + 1, 1 - zo)   otherwise

    # dim=1 cases
    npt.assert_almost_equal(_d_bound(1, 0, 0, 0), 1)
    npt.assert_almost_equal(_d_bound(1, 0, 1, 1), 1)
    npt.assert_almost_equal(_d_bound(1, 0.5, 1, 1), 0.5)
    npt.assert_almost_equal(_d_bound(1, 0.75, 1, 1), 0.25)
    npt.assert_almost_equal(_d_bound(1, -0.5, -1, 1), 0.5)
    npt.assert_almost_equal(_d_bound(1, -0.75, 1, 1), 0.25)
    npt.assert_almost_equal(_d_bound(1, 1, 0.25, 0.5), 0.0)
    npt.assert_almost_equal(_d_bound(1, -1, -0.5, 0.75), 0.0)

    # dim=2 cases
    npt.assert_almost_equal(_d_bound(2, 0, 0, 0), 1)
    npt.assert_almost_equal(_d_bound(2, 0, 1, 1), 0)
    npt.assert_almost_equal(_d_bound(2, 0.5, 0, 0), 0.5)
    npt.assert_almost_equal(_d_bound(2, -0.5, 0, 0), 0.5)
    npt.assert_almost_equal(_d_bound(2, 0, 0.75, 1), 0.25)
    npt.assert_almost_equal(_d_bound(2, 0, -0.75, -1), 0.25)

    # dim=3 cases
    npt.assert_almost_equal(_d_bound(3, 0, 0, 0), 1)
    npt.assert_almost_equal(_d_bound(3, 0, 0, 1), 0)
    npt.assert_almost_equal(_d_bound(3, 0, 1, 0), 0)
    npt.assert_almost_equal(_d_bound(3, 1, 0, 0), 0)
    npt.assert_almost_equal(_d_bound(3, 0, 0, -1), 0)
    npt.assert_almost_equal(_d_bound(3, 0, -1, 0), 0)
    npt.assert_almost_equal(_d_bound(3, -1, 0, 0), 0)
    npt.assert_almost_equal(_d_bound(3, 0, 0, 0.25), 0.75)
    npt.assert_almost_equal(_d_bound(3, 0, 0.25, 0), 0.75)
    npt.assert_almost_equal(_d_bound(3, 0.25, 0, 0), 0.75)
    npt.assert_almost_equal(_d_bound(3, 0, 0, -0.25), 0.75)
    npt.assert_almost_equal(_d_bound(3, 0, -0.25, 0), 0.75)
    npt.assert_almost_equal(_d_bound(3, -0.25, 0, 0), 0.75)
    npt.assert_almost_equal(_d_bound(3, 0.75, 0, 0.25), 0.25)
    npt.assert_almost_equal(_d_bound(3, 0, -0.25, 0.75), 0.25)
    npt.assert_almost_equal(_d_bound(3, 0.25, 0, -0.75), 0.25)


def test_allo_extent_mu():
    #                                   { h(xo, sx)^3                 if dim=1
    # mu(dim, sx, sy, sz, xo, yo, zo) = { h(xo, sx)h(yo, sy)^(3/2)    if dim=2
    #                                   { h(xo, sx)h(yo, sy)h(zo, sz) if dim=3

    for dim in range(1, 4):
        #                               sx   sy   sz    xo    yo    zo
        for sx, sy, sz, xo, yo, zo in [(0.2, 0.1, 0.1,  0.0,  0.0,  0.0),
                                       (0.2, 0.1, 0.1,  1.0,  0.0,  0.0),
                                       (0.2, 0.1, 0.1,  0.5,  0.0,  0.0),
                                       (0.1, 0.1, 0.1, -1.0,  0.0,  0.0),
                                       (0.5, 1.0, 0.1,  0.0,  0.1,  0.0),
                                       (0.1, 0.1, 0.1,  0.7,  0.8,  0.9),
                                       (0.2, 0.3, 0.4, -1.0, -0.9, -0.5),
                                       (0.8, 0.7, 0.6,  0.5, -0.4,  0.3),
                                       (1.0, 1.0, 1.0,  0.0,  0.0,  0.0)]:
            if dim == 1:
                npt.assert_almost_equal(_mu(dim, sx, sy, sz, xo, yo, zo), _h(xo, sx, _d_bound(dim, xo, yo, zo)) ** 3)
            elif dim == 2:
                db = _d_bound(dim, xo, yo, zo)
                npt.assert_almost_equal(_mu(dim, sx, sy, sz, xo, yo, zo), (_h(xo, sx, db) * _h(yo, sy, db)) ** (1.5))
            else:
                db = _d_bound(dim, xo, yo, zo)
                npt.assert_almost_equal(_mu(dim, sx, sy, sz, xo, yo, zo), _h(xo, sx, db) * _h(yo, sy, db) * _h(zo, sz, db))


def test_allo_extent_calc_w():
    # w(xo, yo, zo, sx, sy, sz, xs, ys, zs) = [w(xs, xo, sx), w(ys, yo, sy), w(zs, zo, sz)]

    #                     [  3  ( xs - xo ) ]^4
    # w(xs, xo, sx) = 10^-[ --- (---------) ]
    #                     [  2  (  2*sx   ) ]
    #
    # definitions of w(ys, yo, sy) is just like the
    # definition of w(xs, xo, sx), just with x replaced by y/z)
    #
    #                     [  3  ( zs - zo ) ]^4
    # w(zs, zo, sz) = 10^-[ --- (---------) ]
    #                     [  2  (   sz    ) ]

    NEG130DB_LIM = 2.0*np.power(6.5,0.25)/3.0

    def wxy(_s, _o, s_):
        return 10.0 ** -((1.5 * np.minimum(np.abs(_s - _o) / (2*s_), np.ones(_s.shape)*NEG130DB_LIM)) ** 4.0)

    def wz(_s, _o, s_):
        return 10.0 ** -((1.5 * np.minimum(np.abs(_s - _o) / s_, np.ones(_s.shape)*NEG130DB_LIM)) ** 4.0)*np.cos(zs*np.pi/(7.0/3.0))

    for  xo,   yo,   zo,   sx,   sy,   sz,   xs,   ys,   zs in [
       ( 0.0,  0.0,  0.0,  0.1,  0.1,  0.1, np.linspace(-1.0,1.0,5),  np.linspace(-1.0,1.0,5),  np.linspace(-1.0,1.0,5)),
       ( 0.1,  0.1,  0.1,  0.2,  0.2,  0.2, np.linspace(-1.0,1.0,5),  np.linspace(-1.0,1.0,5),  np.linspace(-1.0,1.0,5)),
       (-0.1,  0.8, -0.4,  0.9,  0.2,  0.4, np.linspace(-1.0,1.0,5),  np.linspace(-1.0,1.0,5),  np.linspace(-1.0,1.0,5)),
       ( 0.0,  0.0,  0.0,  0.5,  0.5,  0.5, np.linspace(-1.0,1.0,5),  np.linspace(-1.0,1.0,5),  np.linspace(-1.0,1.0,5)),
       ( 0.0,  0.0,  0.0,  0.2,  0.2,  0.2, np.linspace(-1.0,1.0,5),  np.linspace(-1.0,1.0,5),  np.linspace(-1.0,1.0,5))]:
        npt.assert_almost_equal(_calc_w(xo, yo, zo, sx, sy, sz, xs, ys, zs), np.array([wxy(xs, xo, sx), wxy(ys, yo, sy), wz(zs, zo, sz)]))


def test_allo_extent_dim():
    sp = speaker_positions

    assert _dim(sp(["M+000"])) == 0

    assert _dim(sp(["M+030", "M-030", "M+000"])) == 1
    assert _dim(sp(["M+110", "M-110"])) == 1
    assert _dim(sp(["U+030", "U-030"])) == 1
    assert _dim(sp(["B+045", "B-045", "B+000"])) == 1

    assert _dim(sp(["M+030", "M-030", "M+110", "M-110"])) == 2
    assert _dim(sp(["M+030", "M-030", "M+000", "M+110", "M-110"])) == 2
    assert _dim(sp(["M+030", "M-030", "M+000", "M-110", "M+090", "M-090"])) == 2
    assert _dim(sp(["U+030", "U-030", "U+090", "U-090"])) == 2
    assert _dim(sp(["U+030", "U-030", "U+090", "U-090", "U+180"])) == 2

    assert _dim(sp(["M+030", "M-030", "M+110", "M-110", "U+030", "U-030"])) == 3
    assert _dim(sp(["M+030", "M-030", "M+000", "M+110", "M-110", "U+030", "U-030"])) == 3
    assert _dim(sp(["M+030", "M-030", "M+000", "M+110", "M-110", "M+090", "M-090", "U+030", "U-030"])) == 3
    assert _dim(sp(["U+030", "U-030", "U+090", "U-090", "B+045", "B-045", "B+000"])) == 3


def test_allo_extent_calc_f():
    # def _calc_f(p, w, g_point):

    #     ===
    #     \                         p
    # f = /    [g_point(ss) * w(ss)]
    #     ===
    #     ss

    V = lambda l: np.array(l).reshape([1, len(l)])
    for p,      w,             g_point,    expect in [
       (1.0, V([1.0     ]), V([1.0     ]), 1.0),   # (1*1)^1
       (1.0, V([0.0     ]), V([1.0     ]), 0.0),   # (0*1)^1
       (0.5, V([2.0     ]), V([2.0     ]), 2.0),   # (2*2)^0.5
       (1.0, V([2.0     ]), V([2.0     ]), 4.0),   # (2*2)^1
       (1.0, V([1.0, 1.0]), V([1.0, 1.0]), 2.0),   # (1*1)^1 + (1*1)^1
       (2.0, V([1.0, 1.0]), V([1.0, 1.0]), 2.0),   # (1*1)^2 + (1*1)^2
       (0.5, V([3.0, 5.0]), V([3.0, 5.0]), 8.0)]:  # (3*3)^0.5 + (5*5)^0.5
        npt.assert_almost_equal(_calc_f(p, w, g_point), expect)


def test_allo_extent_find_plane_z():
    sp = speaker_positions

    # We could have a bit of tolerance in these tests for the None
    # cases. Things should behave just fine if instead of returning None,
    # the _find_plane_z returned the same number twice, or flipped the
    # order of the number and the None.
    assert _find_plane_z( 0.0, sp(["M+030"])) == (0.0, 0.0)
    assert _find_plane_z( 0.5, sp(["M+030"])) == (0.0, None)
    assert _find_plane_z(-0.5, sp(["M+030"])) == (None, 0.0)

    assert _find_plane_z( 0.0, sp(["M+030", "U+030"])) == (0.0, 0.0)
    assert _find_plane_z( 0.5, sp(["M+030", "U+030"])) == (0.0, 1.0)
    assert _find_plane_z( 1.0, sp(["M+030", "U+030"])) == (1.0, 1.0)
    assert _find_plane_z(-0.5, sp(["M+030", "U+030"])) == (None, 0.0)

    assert _find_plane_z( 0.0, sp(["M+030", "U+030", "B+000"])) == (0.0, 0.0)
    assert _find_plane_z( 0.5, sp(["M+030", "U+030", "B+000"])) == (0.0, 1.0)
    assert _find_plane_z( 1.0, sp(["M+030", "U+030", "B+000"])) == (1.0, 1.0)
    assert _find_plane_z(-0.5, sp(["M+030", "U+030", "B+000"])) == (-1.0, 0.0)
    assert _find_plane_z(-1.0, sp(["M+030", "U+030", "B+000"])) == (-1.0, -1.0)


def test_allo_extent_find_row_y():
    sp = speaker_positions

    # Like with test_allo_extent_find_plane_z(), our pass fail criteria
    # is a little bit strict.
    assert _find_row_y( 0.0, 0.0, sp(["M+030"])) == (None, 1.0)
    assert _find_row_y( 0.0, 0.0, sp(["M+030", "M-030"])) == (None, 1.0)
    assert _find_row_y( 0.0, 0.0, sp(["M+030", "M-030", "U+000", "U+110", "U-110"])) == (None, 1.0)
    assert _find_row_y( 0.5, 0.0, sp(["M+030"])) == (None, 1.0)
    assert _find_row_y( 0.5, 0.0, sp(["M+030", "M-030"])) == (None, 1.0)
    assert _find_row_y( 0.5, 0.0, sp(["M+030", "M-030", "U+000", "U+110", "U-110"])) == (None, 1.0)
    assert _find_row_y( 0.5, 1.0, sp(["M+030", "M-030", "U+000", "U+110", "U-110"])) == (-1.0, 1.0)
    assert _find_row_y( 1.0, 1.0, sp(["M+030", "M-030", "U+000", "U+110", "U-110"])) == (1.0, 1.0)
    assert _find_row_y( 1.0, 1.0, sp(["M+030", "M-030", "U+000", "U+110", "U-110", "B+000", "B+045", "B-045"])) == (1.0, 1.0)
    assert _find_row_y( 1.0, -1.0, sp(["M+030", "M-030", "U+000", "U+110", "U-110", "B+000", "B+045", "B-045"])) == (1.0, 1.0)
    assert _find_row_y( 1.0, 0.0, sp(["M+110", "M-110", "U+000", "U+110", "U-110", "B+000", "B+045", "B-045"])) == (-1.0, None)
    assert _find_row_y(-1.0, 0.0, sp(["M+110", "M-110", "U+000", "U+110", "U-110", "B+000", "B+045", "B-045"])) == (-1.0, -1.0)
    assert _find_row_y(-1.0, 0.0, sp(["M+030", "M-030", "M+110", "M-110", "U+000", "U+110", "U-110", "B+000", "B+045", "B-045"])) == (-1.0, -1.0)


def test_allo_extent_find_column_x():
    sp = speaker_positions

    # Like with test_allo_extent_find_plane_z(), our pass fail criteria
    # is a little bit strict.
    assert _find_column_x( 0.0, 1.0, 0.0, sp(["M+000", "M+030", "M-030"])) == (0.0, 0.0)
    assert _find_column_x(-0.5, 1.0, 0.0, sp(["M+000", "M+030", "M-030"])) == (-1.0, 0.0)
    assert _find_column_x( 0.5, 1.0, 0.0, sp(["M+000", "M+030", "M-030"])) == ( 0.0, 1.0)
    assert _find_column_x(-1.0, 1.0, 0.0, sp(["M+000", "M+030", "M-030"])) == (-1.0, -1.0)
    assert _find_column_x( 1.0, 1.0, 0.0, sp(["M+000", "M+030", "M-030"])) == ( 1.0, 1.0)

    assert _find_column_x( 0.0, 1.0, 0.0, sp(["M+030", "M-030", "B-045", "B+000", "B+045"])) == (-1.0, 1.0)
    assert _find_column_x( 0.0, 1.0, -1.0, sp(["M+030", "M-030", "B-045", "B+000", "B+045"])) == (0.0, 0.0)

    assert _find_column_x( 0.0, -1.0, 0.0, sp(["M+030", "M-030", "M+000", "M+110", "M-110"])) == (-1.0, 1.0)
    assert _find_column_x( 0.0,  1.0, 0.0, sp(["M+030", "M-030", "M+000", "M+110", "M-110"])) == (0.0, 0.0)


def test_allo_extent_calc_g_point_separated():
    sp = speaker_positions

    # Gains for 0+2+0 case with object halfway between the speakers are
    # easy to calculate in your head
    # (M+030)<---1.0--->(OBJ)<---1.0--->(M-030)
    # We expect 2^-0.5 for both gains since we are doing a power preserving pan
    xs = [0.0]
    ys = [-1.0, -0.5, 0.0, 0.5, 1.0]
    zs = [-1.0, -0.5, 0.0, 0.5, 1.0]
    spks = sp(["M+030", "M-030"])
    gx, gy, gz = _calc_g_point_separated(spks, xs, ys, zs)
    npt.assert_almost_equal(gx, np.array([[2.0 ** -0.5], [2.0 ** -0.5]]))
    npt.assert_almost_equal(gy, np.array([[1.0] * len(ys)] * len(spks)))
    npt.assert_almost_equal(gz, np.array([[1.0] * len(zs)] * len(spks)))

    # (M+030)<---1.5--->(OBJ)<---0.5--->(M-030)
    # x-gains should be sin(1.5/2 * (PI/2)) and cos(1.5/2 * (PI/2))
    xs = [0.5]
    gx, gy, gz = _calc_g_point_separated(spks, xs, ys, zs)
    gx_M_030 = np.cos(1.5/2 * np.pi/2)
    gx_MN030 = np.sin(1.5/2 * np.pi/2)
    npt.assert_almost_equal(gx, np.array([[gx_M_030], [gx_MN030]]))
    assert gx_M_030 < gx_MN030  # we expect the gain for the M-030 speaker to be bigger (make sure we didn't flip cos/sin...)

    # (M+030)<---1.5--->(OBJ)<---0.5--->(M+110)
    spks = sp(["M+030", "M+110"])
    xs = [-1.0, -0.5, 0.0, 0.5, 1.0]
    ys = [-0.5]
    zs = [-1.0, -0.5, 0.0, 0.5, 1.0]
    gx, gy, gz = _calc_g_point_separated(spks, xs, ys, zs)
    gy_M_110 = np.sin(1.5/2 * np.pi/2)
    gy_M_030 = np.cos(1.5/2 * np.pi/2)
    npt.assert_almost_equal(gx, np.array([[1.0] * len(xs)] * len(spks)))
    npt.assert_almost_equal(gy, np.array([[gy_M_030], [gy_M_110]]))
    npt.assert_almost_equal(gz, np.array([[1.0] * len(zs)] * len(spks)))
    assert gy_M_030 < gy_M_110

    # (B+000)<---1.5--->(OBJ)<---0.5--->(U+000)
    spks = sp(["B+000", "U+000"])
    xs = [-1.0, -0.5, 0.0, 0.5, 1.0]
    ys = [-1.0, -0.5, 0.0, 0.5, 1.0]
    zs = [0.5]
    gx, gy, gz = _calc_g_point_separated(spks, xs, ys, zs)
    gz_B_000 = np.cos(1.5/2 * np.pi/2)
    gz_U_000 = np.sin(1.5/2 * np.pi/2)
    npt.assert_almost_equal(gx, np.array([[1.0] * len(xs)] * len(spks)))
    npt.assert_almost_equal(gy, np.array([[1.0] * len(ys)] * len(spks)))
    npt.assert_almost_equal(gz, np.array([[gz_B_000], [gz_U_000]]))
    assert gz_B_000 < gz_U_000


def test_allo_extent_calc_Nz():
    assert _calc_Nz(speaker_positions(["M+000"])) == 20
    assert _calc_Nz(speaker_positions(["M+000", "U+000"])) == 20
    assert _calc_Nz(speaker_positions(["M+000", "U+000", "B+000"])) == 40

    assert _calc_Nz(speaker_positions(["M+000", "M+030", "M-030"])) == 20
    assert _calc_Nz(speaker_positions(["M+000", "U+000", "M+030", "M+110", "U+030"])) == 20
    assert _calc_Nz(speaker_positions(["M+000", "U+000", "B+000", "M-030", "M-110", "U-030", "B+045", "B-045"])) == 40


def get_gains_check(speakers, position, sx, sy, sz):
    """call get_gains, and check that the return is normalised and positive"""
    g = get_gains(speakers, position, sx, sy, sz)

    assert np.all(g >= 0)
    npt.assert_allclose(np.linalg.norm(g), 1)

    return g


def test_allo_extent_get_gains():
    sp = speaker_positions

    # sizes in y/z directions don't do anything for a 0+2+0 layout
    spks = sp(["M+030", "M-030"])
    g1 = get_gains_check(spks, np.array([0, 0, 0]), 1.0, 0.0, 0.0)
    g2 = get_gains_check(spks, np.array([0, 0, 0]), 1.0, 1.0, 1.0)
    npt.assert_almost_equal(g1, g2)

    # changing size for object halfway between our two speakers doesn't
    # do anything (since we still normalize gains)
    g1 = get_gains_check(spks, np.array([0, 0, 0]), 1.0, 0.0, 0.0)
    g2 = get_gains_check(spks, np.array([0, 0, 0]), 0.5, 0.0, 0.0)
    npt.assert_almost_equal(g1, g2)

    # changing size for object NOT halfway between the two speakers
    # does change the gains
    g1 = get_gains_check(spks, np.array([0.5, 0, 0]), 1.0, 0.0, 0.0)
    g2 = get_gains_check(spks, np.array([0.5, 0, 0]), 0.5, 0.0, 0.0)
    assert all(abs(g1 - g2) > 1e-9)

    # object on top of a speaker fires the other speaker when
    # size is nonzero
    g = get_gains_check(spks, np.array([-1.0, 0, 0]), 1.0, 1.0, 1.0)
    assert all(g > 1e-7)

    # # object on top of speaker doesn't fire the other speaker when
    # # size is zero
    # g = get_gains(spks, np.array([-1.0, 0, 0]), 0.0, 0.0, 0.0)
    # npt.assert_almost_equal(g, np.array([1.0, 0.0]))

    # 4+9+0 layout
    spks = sp(["M+000", "M+SC", "M-SC", "M+030", "M-030", "M+090", "M-090", "M+135", "M-135", "U+045", "U-045", "U+110", "U-110"])

    # size=1 will fill the room
    g = get_gains_check(spks, np.array([0.0, 0.0, 0.0]), 1.0, 1.0, 1.0)
    assert all(g > 1e-7)

    # ... even from the corners
    g = get_gains_check(spks, np.array([-1.0, -1.0, -1.0]), 1.0, 1.0, 1.0)
    assert all(g > 1e-7)
    g = get_gains_check(spks, np.array([1.0, 1.0, 1.0]), 1.0, 1.0, 1.0)
    assert all(g > 1e-7)

    # size=0.25 will fire all speakers in the room from the centre
    g = get_gains_check(spks, np.array([0.0, 0.0, 0.0]), 0.25, 0.25, 0.25)
    assert all(g > 1e-9)

    # ... but not from the corners
    g = get_gains_check(spks, np.array([-1.0, -1.0, -1.0]), 0.25, 0.25, 0.25)
    assert any(g < 1e-9)
    g = get_gains_check(spks, np.array([1.0, 1.0, 1.0]), 0.25, 0.25, 0.25)
    assert any(g < 1e-9)

    # size=2 behaves the same as size=1
    g1 = get_gains_check(spks, np.array([-1.0, -1.0, -1.0]), 1.0, 1.0, 1.0)
    g2 = get_gains_check(spks, np.array([-1.0, -1.0, -1.0]), 2.0, 2.0, 2.0)
    npt.assert_almost_equal(g1, g2)
