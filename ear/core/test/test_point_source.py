import numpy as np
import numpy.testing as npt
from .. import bs2051
from ..point_source import Triplet, VirtualNgon, StereoPanDownmix, PointSourcePanner, configure, AllocentricPanner
from ..geom import cart, azimuth, PolarPosition
from ..layout import Speaker
import pytest


def test_virtual():
    positions = np.array([cart(30, 0, 1), cart(-30, 0, 1),
                          cart(30, 30, 1), cart(-30, 30, 1)])
    virtual_downmix = np.array([0.2, 0.2, 0.3, 0.3])
    virtual_pos = virtual_downmix.dot(positions)

    ng = VirtualNgon(range(4), positions, virtual_pos, virtual_downmix)

    # if we pan to the virtual speaker, the output should be the normalised downmix
    npt.assert_allclose(ng.handle(virtual_pos), virtual_downmix / np.linalg.norm(virtual_downmix))

    # for random linear combinations of the loudspeakers positions...
    proportions = np.random.random((100, 4))
    for proportion in proportions:
        # ... we can calculate a position within the ngon...
        pos = np.dot(positions.T, proportion)
        pos /= np.linalg.norm(pos)

        # ... which when rendered...
        pv = ng.handle(pos)

        # ... can be multiplied by the speaker positions to produce another position...
        pos_calc = pv.dot(positions)
        pos_calc /= np.linalg.norm(pos_calc)

        # ... that should be the same as the one we started with
        npt.assert_allclose(pos, pos_calc)


def test_stereo_downmix():
    p = StereoPanDownmix(0, 1)

    pos_gains = [
        (cart(0, 0, 1), np.sqrt([0.5, 0.5])),
        (cart(-30, 0, 1), np.sqrt([0.0, 1.0])),
        (cart(-110, 0, 1), np.sqrt([0.0, 0.5])),
        (cart(-180, 0, 1), np.sqrt([0.25, 0.25])),
    ]

    for pos, gains in pos_gains:
        npt.assert_allclose(p.handle(pos), gains, atol=1e-5)

    spk_pos = [cart(30, 0, 1), cart(-30, 0, 1)]
    pv = p.handle(cart(15, 0, 1))
    npt.assert_allclose(azimuth(np.dot(pv, spk_pos)), 15)


def test_PointSourcePanner():
    positions = np.array([
        cart(30, 0, 1), cart(0, 0, 1), cart(-30, 0, 1),
        cart(0, 30, 1)
    ])

    tris = [[0, 1, 3], [2, 1, 3]]
    regions = [Triplet(tri, positions[tri]) for tri in tris]

    # should fail if not given enough channels
    with pytest.raises(AssertionError):
        PointSourcePanner(regions, len(positions) - 1)

    psp = PointSourcePanner(regions)
    assert psp.num_channels == len(positions)

    for i, position in enumerate(positions):
        pv_req = np.zeros(len(positions))
        pv_req[i] = 1.0

        npt.assert_allclose(psp.handle(position), pv_req)

    assert psp.handle(np.array([0, -1, 0])) is None


def test_all_layouts(layout):
    config = configure(layout)

    # calculate gains for every position on a grid
    azimuths, elevations = np.meshgrid(np.linspace(-180, 180, 61),
                                       np.linspace(-90, 90, 31))

    positions = cart(azimuths, elevations, 1)

    pv = np.apply_along_axis(config.handle, 2, positions)

    assert np.all(pv >= 0)

    # check that symmetric positions produce symmetric panning values

    spk_positions = layout.norm_positions
    # channel map that exchanges speakers which have inverse x positions; this
    # assumes that the layout is left-right symmetric
    flip_remap = [
        np.argmin(np.linalg.norm(spk_positions - [-pos[0], pos[1], pos[2]], axis=1))
        for pos in spk_positions]

    npt.assert_allclose(pv, pv[:, ::-1, flip_remap], atol=1e-10)

    # check that the gains are normalised

    # stereo is normalised only at the front, and at the back at -3dB
    if layout.name == "0+2+0":
        gains_normalised = (elevations == 0) & ((np.abs(azimuths) <= 30) | (np.abs(azimuths) >= 110))

        gains_target = np.zeros_like(azimuths)
        gains_target[(np.abs(azimuths) <= 30) & (elevations == 0)] = 1.0
        gains_target[(np.abs(azimuths) >= 110) & (elevations == 0)] = np.sqrt(0.5)

        npt.assert_allclose(np.linalg.norm(pv[gains_normalised], axis=1),
                            gains_target[gains_normalised])
        assert np.all(np.linalg.norm(pv, axis=2) >= np.sqrt(0.5) - 1e-6)
    else:

        npt.assert_allclose(np.linalg.norm(pv, axis=2), 1)

    # check that the velocity vector matches the source position

    # true if the panner should pass the tests at the corresponding position
    vv_at_pos = np.ones_like(azimuths, dtype=bool)

    if layout.name == "0+2+0":
        vv_at_pos = (np.abs(azimuths) <= 30) & (elevations == 0)
    elif layout.name in ["0+5+0", "2+5+0", "0+7+0"]:
        vv_at_pos = elevations == 0
    elif layout.name.endswith("+0"):
        vv_at_pos = elevations >= 0
    else:
        vv_at_pos = np.ones_like(azimuths, dtype=bool)

    # all layouts have remapping below the horizontal plane
    vv_at_pos &= elevations >= 0
    # only 9+10+3 has no remapping above the horizontal plane
    if "U+180" not in layout.channel_names and "UH+180" not in layout.channel_names:
        vv_at_pos &= elevations <= 0

    assert np.count_nonzero(vv_at_pos) > 0

    vv = np.dot(pv, layout.positions)
    vv /= np.linalg.norm(vv, axis=2, keepdims=True)
    npt.assert_allclose(vv[vv_at_pos], positions[vv_at_pos], atol=1e-10)


def test_screen_pos_check():
    invalid_screen_speakers = [
        Speaker(channel=0,
                names=["M+SC"], polar_position=PolarPosition(azimuth=30.0,
                                                             elevation=0.0,
                                                             distance=1.0)),
        Speaker(channel=1,
                names=["M-SC"], polar_position=PolarPosition(azimuth=-30.0,
                                                             elevation=0.0,
                                                             distance=1.0)),
    ]

    layout = bs2051.get_layout("4+9+0").without_lfe.with_speakers(invalid_screen_speakers)[0]

    expected = ("channel M\\+SC has azimuth 30.0, which is not "
                "in the allowed ranges of 5 to 25 and 35 to 60 "
                "degrees.")
    with pytest.raises(ValueError, match=expected):
        configure(layout)


def test_allocentric_single_balance_pan():
    fn = AllocentricPanner._single_balance_pan

    # Halfway
    npt.assert_allclose(np.array(fn(0.0, 1.0, 0.5)), np.array([2.0**-0.5]*2))
    npt.assert_allclose(np.array(fn(-1.0, 1.0, 0.0)), np.array([2.0**-0.5]*2))
    npt.assert_allclose(np.array(fn(-1.0, 0.0, -0.5)), np.array([2.0**-0.5]*2))

    # Outside range
    npt.assert_allclose(np.array(fn(-1.0, 0.0, 1.0)), np.array([1.0, 0.0]))
    npt.assert_allclose(np.array(fn(0.0, 1.0, -1.0)), np.array([0.0, 1.0]))

    # No range (this feels like a bit of a special case - we want the
    # result to be 1.0/1.0, instead of something where a^2+b^2=1.0,
    # but this is helpful behaviour to have here for implementation
    # to avoid ugliness in avoiding multiplication by 0.0.
    npt.assert_allclose(np.array(fn(0.0, 0.0, 0.0)), np.array([1.0, 1.0]))
    npt.assert_allclose(np.array(fn(0.0, 0.0, 1.0)), np.array([1.0, 1.0]))
    npt.assert_allclose(np.array(fn(0.0, 0.0, -1.0)), np.array([1.0, 1.0]))

    # At range
    npt.assert_allclose(np.array(fn(0.0, 1.0, 1.0)), np.array([1.0, 0.0]))
    npt.assert_allclose(np.array(fn(0.0, 1.0, 0.0)), np.array([0.0, 1.0]))

    # Quarter/Three-quarter
    npt.assert_allclose(np.array(fn(0.0, 1.0, 0.25)), np.array([np.cos(np.pi * 0.125), np.sin(np.pi * 0.125)]))
    npt.assert_allclose(np.array(fn(0.0, 1.0, 0.75)), np.array([np.sin(np.pi * 0.125), np.cos(np.pi * 0.125)]))
    assert fn(0.0, 1.0, 0.25)[0] < fn(0.0, 0.1, 0.75)[0]
    assert fn(0.0, 1.0, 0.25)[1] > fn(0.0, 0.1, 0.75)[1]


def speaker_positions(names):
    def P(x, y, z):
        return np.array([x, y, z])
    pos = {"M+000": P( 0.0,      1.0,       0.0),  # noqa
           "M+SC":  P(-0.414214, 1.0,       0.0),  # noqa
           "M-SC":  P( 0.414214, 1.0,       0.0),  # noqa
           "M+030": P(-1.0,      1.0,       0.0),  # noqa
           "M-030": P( 1.0,      1.0,       0.0),  # noqa
           "M+060": P(-1.0,      0.414214,  0.0),  # noqa
           "M-060": P( 1.0,      0.414214,  0.0),  # noqa
           "M+090": P(-1.0,      0.0,       0.0),  # noqa
           "M-090": P( 1.0,      0.0,       0.0),  # noqa
           # M?110 and M?135 are treated as synonyms
           "M+110": P(-1.0,     -1.0,       0.0),  # noqa
           "M-110": P( 1.0,     -1.0,       0.0),  # noqa
           "M+135": P(-1.0,     -1.0,       0.0),  # noqa
           "M-135": P( 1.0,     -1.0,       0.0),  # noqa
           "M+180": P( 0.0,     -1.0,       0.0),  # noqa
           "U+000": P( 0.0,      1.0,       1.0),  # noqa
           # U?030 and U?045 are treated as synonyms
           "U+030": P(-1.0,      1.0,       1.0),  # noqa
           "U-030": P( 1.0,      1.0,       1.0),  # noqa
           "U+045": P(-1.0,      1.0,       1.0),  # noqa
           "U-045": P( 1.0,      1.0,       1.0),  # noqa
           "U+090": P(-1.0,      0.0,       1.0),  # noqa
           "U-090": P( 1.0,      0.0,       1.0),  # noqa
           # U?110 and U?135 are treated as synonyms
           "U+110": P(-1.0,     -1.0,       1.0),  # noqa
           "U-110": P( 1.0,     -1.0,       1.0),  # noqa
           "U+135": P(-1.0,     -1.0,       1.0),  # noqa
           "U-135": P( 1.0,     -1.0,       1.0),  # noqa
           "U+180": P( 0.0,     -1.0,       1.0),  # noqa
           "T+000": P( 0.0,      0.0,       1.0),  # noqa
           "B+000": P( 0.0,      1.0,      -1.0),  # noqa
           "B+045": P(-1.0,      1.0,      -1.0),  # noqa
           "B-045": P( 1.0,      1.0,      -1.0)}  # noqa
    return np.array([pos[s] for s in names])


def test_allocentric_find_planes():
    spks = speaker_positions(["M+000", "U+000", "B+000"])
    a = AllocentricPanner(spks)

    # Note that the outputs here have B+000=0, M+000=1, U+000=2, even
    # though the order of speakers given to the constructor was different.
    # This is correct, and we want these to be based on the (z) sorted order
    assert a._find_planes(0.0) == [1, 1]
    assert a._find_planes(1.0) == [2, 2]
    assert a._find_planes(-1.0) == [0, 0]
    assert a._find_planes(0.5) == [1, 2]
    assert a._find_planes(-0.5) == [0, 1]
    assert a._find_planes(2.0) == [2, 2]
    assert a._find_planes(-2.0) == [0, 0]

    # Just M and U planes
    spks = speaker_positions(["M+000", "U+000", "M+030", "M-030", "U+110", "U-110"])
    a = AllocentricPanner(spks)

    assert a._find_planes(0.0) == [0, 0]
    assert a._find_planes(1.0) == [1, 1]
    assert a._find_planes(-1.0) == [0, 0]
    assert a._find_planes(0.5) == [0, 1]
    assert a._find_planes(-0.5) == [0, 0]
    assert a._find_planes(2.0) == [1, 1]
    assert a._find_planes(-2.0) == [0, 0]


def test_allocentric_find_rows():
    # Two row case
    spks = speaker_positions(["M+000", "M+030", "M-030", "M+110", "M-110"])
    a = AllocentricPanner(spks)
    assert a._find_rows(a.st[0], 0.0) == [0, 1]
    assert a._find_rows(a.st[0], 1.0) == [1, 1]
    assert a._find_rows(a.st[0], -1.0) == [0, 0]
    assert a._find_rows(a.st[0], 0.5) == [0, 1]
    assert a._find_rows(a.st[0], -0.5) == [0, 1]
    assert a._find_rows(a.st[0], 2.0) == [1, 1]
    assert a._find_rows(a.st[0], -2.0) == [0, 0]

    # Three row case
    spks = speaker_positions(["M+000", "M+030", "M-030", "M+090", "M-090", "M+135", "M-135"])
    a = AllocentricPanner(spks)
    assert a._find_rows(a.st[0], 0.0) == [1, 1]
    assert a._find_rows(a.st[0], 1.0) == [2, 2]
    assert a._find_rows(a.st[0], -1.0) == [0, 0]
    assert a._find_rows(a.st[0], 0.5) == [1, 2]
    assert a._find_rows(a.st[0], -0.5) == [0, 1]
    assert a._find_rows(a.st[0], 2.0) == [2, 2]
    assert a._find_rows(a.st[0], -2.0) == [0, 0]


def test_allocentric_find_columns():
    # Two column case
    spks = speaker_positions(["M+030", "M-030", "M+110", "M-110"])
    a = AllocentricPanner(spks)
    assert a._find_columns(a.st[0][0], 0.0) == [0, 1]
    assert a._find_columns(a.st[0][0], 1.0) == [1, 1]
    assert a._find_columns(a.st[0][0], -1.0) == [0, 0]
    assert a._find_columns(a.st[0][0], 0.5) == [0, 1]
    assert a._find_columns(a.st[0][0], -0.5) == [0, 1]
    assert a._find_columns(a.st[0][0], 2.0) == [1, 1]
    assert a._find_columns(a.st[0][0], -2.0) == [0, 0]

    # Three column case
    spks = speaker_positions(["M+000", "M+030", "M-030", "M+110", "M-110"])
    a = AllocentricPanner(spks)
    assert a._find_columns(a.st[0][1], 0.0) == [1, 1]
    assert a._find_columns(a.st[0][1], 1.0) == [2, 2]
    assert a._find_columns(a.st[0][1], -1.0) == [0, 0]
    assert a._find_columns(a.st[0][1], 0.5) == [1, 2]
    assert a._find_columns(a.st[0][1], -0.5) == [0, 1]
    assert a._find_columns(a.st[0][1], 2.0) == [2, 2]
    assert a._find_columns(a.st[0][1], -2.0) == [0, 0]


def test_allocentric_speaker_tree():
    def check_tree_invariants(st):
        # if  A = ret[az][ay][ax]
        # and B = ret[bz][by][bx]
        # then A[0] < B[0] <=> ax < bx
        #      A[1] < B[1] <=> ay < by
        #      A[2] < B[2] <=> az < bz
        speakers = []
        for az in range(len(st)):
            for ay in range(len(st[az])):
                for ax in range(len(st[az][ay])):
                    A = st[az][ay][ax]
                    speakers.append(A)
                    for bz in range(len(st)):
                        for by in range(len(st[bz])):
                            for bx in range(len(st[bz][by])):
                                B = st[bz][by][bx]
                                if az == bz:
                                    if ay == by:
                                        assert (ax < bx) == (A[1][0] < B[1][0])
                                    assert (ay < by) == (A[1][1] < B[1][1])
                                assert (az < bz) == (A[1][2] < B[1][2])
        return speakers

    for spkrs in [speaker_positions(["M-030", "M+030"]),
                  speaker_positions(["M-030", "M+030", "M+000", "M-110", "M+110"]),
                  speaker_positions(["M-030", "M+030", "M+000", "M-135", "M+135", "M+090", "M-090"]),
                  speaker_positions(["M-030", "M+030", "M+000", "M-135", "M+135", "M+090", "M-090", "U-030", "U+030", "B+000", "B+045", "B-045"]),
                  speaker_positions(["M-030", "M+030", "M+000", "M-110", "M+110", "U+030", "U-030", "U+110", "U-110"])]:
        t = AllocentricPanner._speaker_tree(spkrs)
        speakers_from_tree = check_tree_invariants(t)
        assert len(spkrs) == len(speakers_from_tree)
        for idx, pos in speakers_from_tree:
            assert all(pos == spkrs[idx])


def test_allocentric_point_source():
    spks = speaker_positions(["M+000", "M+030", "M-030", "M+110", "M-110"])
    a = AllocentricPanner(spks)

    # Objects on speakers only go to those speakers
    npt.assert_allclose(a.handle(np.array([ 0.0,  1.0, 0.0])), [1.0, 0.0, 0.0, 0.0, 0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([-1.0,  1.0, 0.0])), [0.0, 1.0, 0.0, 0.0, 0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([ 1.0,  1.0, 0.0])), [0.0, 0.0, 1.0, 0.0, 0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([-1.0, -1.0, 0.0])), [0.0, 0.0, 0.0, 1.0, 0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([ 1.0, -1.0, 0.0])), [0.0, 0.0, 0.0, 0.0, 1.0])  # noqa

    # Z doesn't do anything on a one plane layout
    npt.assert_allclose(a.handle(np.array([ 0.0,  1.0,  1.0])), [1.0, 0.0, 0.0, 0.0, 0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([-1.0,  1.0,  0.5])), [0.0, 1.0, 0.0, 0.0, 0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([ 1.0,  1.0,  0.0])), [0.0, 0.0, 1.0, 0.0, 0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([-1.0, -1.0, -0.5])), [0.0, 0.0, 0.0, 1.0, 0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([ 1.0, -1.0, -1.0])), [0.0, 0.0, 0.0, 0.0, 1.0])  # noqa

    # Objects between speakers are panned evenly to those speakers
    _707 = 2.0 ** -0.5
    npt.assert_allclose(a.handle(np.array([-0.5,  1.0, 0.0])), [_707, _707,  0.0,  0.0,  0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([ 0.5,  1.0, 0.0])), [_707,  0.0, _707,  0.0,  0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([-1.0,  0.0, 0.0])), [ 0.0, _707,  0.0, _707,  0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([ 1.0,  0.0, 0.0])), [ 0.0,  0.0, _707,  0.0, _707])  # noqa
    npt.assert_allclose(a.handle(np.array([ 0.0, -1.0, 0.0])), [ 0.0,  0.0,  0.0, _707, _707])  # noqa

    # Object in the centre of the room is another simple case
    npt.assert_allclose(a.handle(np.array([ 0.0,  0.0, 0.0])), [_707, 0.0, 0.0, 0.5, 0.5])  # noqa

    # Add top and bottom planes
    spks = speaker_positions(["M+000", "M+030", "M-030", "M+110", "M-110", "U+000", "B+045", "B+000", "B-045"])
    a = AllocentricPanner(spks)

    # Objects on plane with only one speaker will only go to that speaker
    npt.assert_allclose(a.handle(np.array([ 0.0,  0.0, 1.0])), [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0])  # noqa

    # Panning between layers
    npt.assert_allclose(a.handle(np.array([ 0.0,  1.0, -0.5])), [_707, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, _707, 0.0])  # noqa
    npt.assert_allclose(a.handle(np.array([ 0.0,  1.0,  0.5])), [_707, 0.0, 0.0, 0.0, 0.0, _707, 0.0, 0.0, 0.0])  # noqa


def test_all_layouts_allo(layout):
    """Basic tests of the allocentric panner on all layouts"""
    from ..allocentric import positions_for_layout
    spks = positions_for_layout(layout)
    a = AllocentricPanner(spks)

    # gains on a grid of points
    positions = np.stack(np.mgrid[-1:1:11j, -1:1:11j, -1:1:11j], -1)
    gains = np.apply_along_axis(a.handle, -1, positions)

    # positive
    assert np.all(gains >= 0)
    # normalised
    npt.assert_allclose(np.linalg.norm(gains, axis=-1), 1)

    # not changing too quickly
    for dim in 0, 1, 2:
        gains_d = np.moveaxis(gains, dim, 0)
        assert np.max(np.abs(gains_d[:-1] - gains_d[1:])) < 0.9
