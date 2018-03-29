import numpy as np
import numpy.testing as npt
from ..point_source import Triplet, VirtualNgon, StereoPanDownmix, PointSourcePanner, configure
from ..geom import cart, azimuth
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
