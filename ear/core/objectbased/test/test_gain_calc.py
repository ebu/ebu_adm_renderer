from attr import attrs, attrib, Factory, evolve
import pytest
import numpy as np
import numpy.testing as npt
from ..gain_calc import GainCalc
from ....fileio.adm.elements import (AudioBlockFormatObjects, ChannelLock, ObjectDivergence,
                                     CartesianZone, PolarZone, Frequency, ScreenEdgeLock, ObjectPolarPosition)
from ...metadata_input import ObjectTypeMetadata, ExtraData
from ...geom import cart, elevation, PolarPosition
from ....common import PolarScreen
from ...test.test_screen_common import default_edge_elevation


@attrs
class GainCalcTestCase(object):
    name = attrib()
    block_format = attrib()
    extra_data = attrib(default=Factory(ExtraData))

    direct_gains = attrib(default=Factory(list))
    diffuse_gains = attrib(default=Factory(list))

    direct_position = attrib(default=None)
    diffuse_position = attrib(default=None)

    def _get_gains(self, layout, gain_calc, position, gains):
        if position is not None:
            gains = gain_calc.point_source_panner.handle(position)
            gains_full = np.zeros(len(layout.channels))
            gains_full[~layout.is_lfe] = gains
            return gains_full

        else:
            expected_direct = np.zeros(len(layout.channels))
            for name, gain in gains:
                expected_direct[layout.channel_names.index(name)] = gain
            return expected_direct

    def get_direct_gains(self, layout, gain_calc):
        return self._get_gains(layout, gain_calc, self.direct_position, self.direct_gains)

    def get_diffuse_gains(self, layout, gain_calc):
        return self._get_gains(layout, gain_calc, self.diffuse_position, self.diffuse_gains)

    def run(self, layout, gain_calc):
        block_format = AudioBlockFormatObjects(**self.block_format)
        gains = gain_calc.render(ObjectTypeMetadata(block_format=block_format,
                                                    extra_data=self.extra_data))

        expected_direct = self.get_direct_gains(layout, gain_calc)
        expected_diffuse = self.get_diffuse_gains(layout, gain_calc)

        npt.assert_allclose(gains.diffuse, expected_diffuse, atol=1e-10)
        npt.assert_allclose(gains.direct, expected_direct, atol=1e-10)


test_cases = []


def add_test(*args, **kwargs):
    test_cases.append(GainCalcTestCase(*args, **kwargs))


add_test("basic_centre",
         dict(position=dict(azimuth=0.0, elevation=0.0, distance=1.0)),
         direct_gains=[("M+000", 1.0)])
add_test("basic_left",
         dict(position=dict(azimuth=30.0, elevation=0.0, distance=1.0)),
         direct_gains=[("M+030", 1.0)])
add_test("basic_left_up",
         dict(position=dict(azimuth=30.0, elevation=30.0, distance=1.0)),
         direct_gains=[("U+030", 1.0)])

add_test("diffuse_half",
         dict(position=dict(azimuth=0.0, elevation=0.0, distance=1.0), diffuse=0.5),
         direct_gains=[("M+000", np.sqrt(0.5))],
         diffuse_gains=[("M+000", np.sqrt(0.5))])
add_test("diffuse_full",
         dict(position=dict(azimuth=0.0, elevation=0.0, distance=1.0), diffuse=1.0),
         diffuse_gains=[("M+000", 1.0)])

add_test("gain",
         dict(position=dict(azimuth=0.0, elevation=0.0, distance=1.0), gain=0.5),
         direct_gains=[("M+000", 0.5)])

add_test("coord_trans_cart_cart",
         dict(position=dict(zip("XYZ", cart(30, 30, 4.0/3.0))), cartesian=True),
         direct_gains=[("U+030", 1.0)])
add_test("coord_trans_polar_cart",
         dict(position=dict(azimuth=30.0, elevation=30.0, distance=4.0/3.0), cartesian=True),
         direct_gains=[("U+030", 1.0)])
add_test("coord_trans_cart_polar",
         dict(position=dict(zip("XYZ", cart(30, 30, 1.0)))),
         direct_gains=[("U+030", 1.0)])
add_test("coord_trans_polar_polar",
         dict(position=dict(azimuth=30.0, elevation=30.0, distance=1.0)),
         direct_gains=[("U+030", 1.0)])

add_test("channel_lock_on_speaker",
         dict(channelLock=ChannelLock(maxDistance=1.0),
              position=dict(azimuth=0.0, elevation=0.0, distance=1.0)),
         direct_gains=[("M+000", 1.0)])
add_test("channel_lock_close",
         dict(channelLock=ChannelLock(maxDistance=1.0),
              position=dict(azimuth=14.0, elevation=0.0, distance=1.0)),
         direct_gains=[("M+000", 1.0)])
add_test("channel_lock_not_close_enough",
         dict(channelLock=ChannelLock(maxDistance=np.linalg.norm(cart(0, 0, 1) - cart(15, 0, 1)) - 0.01),
              position=dict(azimuth=15.0, elevation=0.0, distance=1.0)),
         direct_gains=[("M+000", np.sqrt(0.5)), ("M+030", np.sqrt(0.5))])

add_test("channel_lock_abs_elevation_priority",
         dict(channelLock=ChannelLock(),
              position=dict(azimuth=30.0, elevation=15.0, distance=1.0)),
         direct_gains=[("M+030", 1.0)])
add_test("channel_lock_abs_az_priority_left",
         dict(channelLock=ChannelLock(),
              position=dict(azimuth=15.0, elevation=0.0, distance=1.0)),
         direct_gains=[("M+000", 1.0)])
add_test("channel_lock_abs_az_priority_right",
         dict(channelLock=ChannelLock(),
              position=dict(azimuth=-15.0, elevation=0.0, distance=1.0)),
         direct_gains=[("M+000", 1.0)])
add_test("channel_lock_az_priority_front_top",
         dict(channelLock=ChannelLock(),
              position=dict(azimuth=0.0, elevation=30.0, distance=1.0)),
         direct_gains=[("U-030", 1.0)])
add_test("channel_lock_az_priority_rear_top",
         dict(channelLock=ChannelLock(),
              position=dict(azimuth=180.0, elevation=30.0, distance=1.0)),
         direct_gains=[("U-110", 1.0)])
add_test("channel_lock_az_priority_rear_mid",
         dict(channelLock=ChannelLock(),
              position=dict(azimuth=180.0, elevation=0.0, distance=1.0)),
         direct_gains=[("M-110", 1.0)])

add_test("diverge_half",
         dict(position=dict(azimuth=0.0, elevation=0.0, distance=1.0),
              objectDivergence=ObjectDivergence(0.5, azimuthRange=30.0)),
         direct_gains=[("M+000", np.sqrt(1.0/3.0)), ("M+030", np.sqrt(1.0/3.0)), ("M-030", np.sqrt(1.0/3.0))])
add_test("diverge_full",
         dict(position=dict(azimuth=0.0, elevation=0.0, distance=1.0),
              objectDivergence=ObjectDivergence(1.0, azimuthRange=30.0)),
         direct_gains=[("M+030", np.sqrt(0.5)), ("M-030", np.sqrt(0.5))])

add_test("diverge_cart",
         dict(position=dict(azimuth=0.0, elevation=0.0, distance=1.0), cartesian=True,
              objectDivergence=ObjectDivergence(0.5, positionRange=np.tan(np.radians(30.0)))),
         direct_gains=[("M+000", np.sqrt(1.0/3.0)), ("M+030", np.sqrt(1.0/3.0)), ("M-030", np.sqrt(1.0/3.0))])

add_test("diverge_azimuth",
         dict(position=dict(azimuth=(30.0+110.0)/2.0, elevation=0.0, distance=1.0),
              objectDivergence=ObjectDivergence(1.0, azimuthRange=(110-30.0)/2.0)),
         direct_gains=[("M+030", np.sqrt(0.5)), ("M+110", np.sqrt(0.5))])
add_test("diverge_elevation",
         dict(position=dict(azimuth=0.0, elevation=elevation(cart(30, 30, 1) * [0, 1, 1]), distance=1.0),
              objectDivergence=ObjectDivergence(1.0, azimuthRange=np.degrees(np.arcsin(cart(-30, 30, 1)[0])))),
         direct_gains=[("U+030", np.sqrt(0.5)), ("U-030", np.sqrt(0.5))])
add_test("diverge_azimuth_elevation",
         dict(position=dict(azimuth=70.0, elevation=elevation(cart(40, 30, 1) * [0, 1, 1]), distance=1.0),
              objectDivergence=ObjectDivergence(1.0, azimuthRange=np.degrees(np.arcsin(cart(-40, 30, 1)[0])))),
         direct_gains=[("U+030", np.sqrt(0.5)), ("U+110", np.sqrt(0.5))])

add_test("zone_front",
         dict(position=dict(azimuth=0.0, elevation=0.0, distance=1.0),
              zoneExclusion=[PolarZone(minAzimuth=0.0, maxAzimuth=0.0, minElevation=0.0, maxElevation=0.0)]),
         direct_gains=[("M+030", np.sqrt(0.5)), ("M-030", np.sqrt(0.5))])
add_test("zone_mid_front",
         dict(position=dict(azimuth=0.0, elevation=0.0, distance=1.0),
              zoneExclusion=[PolarZone(minAzimuth=-180.0, maxAzimuth=180.0, minElevation=0.0, maxElevation=0.0)]),
         direct_gains=[("U+030", np.sqrt(0.5)), ("U-030", np.sqrt(0.5))])
add_test("zone_mid_rear",
         dict(position=dict(azimuth=180.0, elevation=0.0, distance=1.0),
              zoneExclusion=[PolarZone(minAzimuth=-180.0, maxAzimuth=180.0, minElevation=0.0, maxElevation=0.0)]),
         direct_gains=[("U+110", np.sqrt(0.5)), ("U-110", np.sqrt(0.5))])

add_test("lfe_direct",
         dict(position=dict(azimuth=0.0, elevation=0.0, distance=1.0)),
         extra_data=ExtraData(channel_frequency=Frequency(lowPass=120.0)),
         direct_gains=[("LFE1", 1.0)])
add_test("lfe_diffuse",
         dict(position=dict(azimuth=15.0, elevation=0.0, distance=1.0), diffuse=1.0),
         extra_data=ExtraData(channel_frequency=Frequency(lowPass=120.0)),
         direct_gains=[("LFE1", 1.0)])

add_test("screen_scale_null",
         dict(position=dict(azimuth=0.0, elevation=0.0, distance=1.0), screenRef=True),
         direct_gains=[("M+000", 1.0)])

add_test("screen_scale_right",
         dict(position=dict(azimuth=30.0, elevation=0.0, distance=1.0), screenRef=True),
         direct_gains=[("M+000", 1.0)],
         extra_data=ExtraData(
             reference_screen=PolarScreen(aspectRatio=1.5,
                                          centrePosition=PolarPosition(30.0, 0.0, 1.0),
                                          widthAzimuth=30.0)))

add_test("screen_edge_lock_right",
         dict(position=ObjectPolarPosition(azimuth=0.0, elevation=0.0, distance=1.0,
                                           screenEdgeLock=ScreenEdgeLock(horizontal="right"))),
         direct_position=cart(-29, 0, 1))
add_test("screen_edge_lock_left",
         dict(position=ObjectPolarPosition(azimuth=0.0, elevation=0.0, distance=1.0,
                                           screenEdgeLock=ScreenEdgeLock(horizontal="left"))),
         direct_position=cart(29, 0, 1))
add_test("screen_edge_lock_top",
         dict(position=ObjectPolarPosition(azimuth=0.0, elevation=0.0, distance=1.0,
                                           screenEdgeLock=ScreenEdgeLock(vertical="top"))),
         direct_position=cart(0, default_edge_elevation, 1))
add_test("screen_edge_lock_bottom",
         dict(position=ObjectPolarPosition(azimuth=0.0, elevation=0.0, distance=1.0,
                                           screenEdgeLock=ScreenEdgeLock(vertical="bottom"))),
         direct_position=cart(0, -default_edge_elevation, 1))
add_test("screen_edge_lock_top_right",
         dict(position=ObjectPolarPosition(azimuth=0.0, elevation=0.0, distance=1.0,
                                           screenEdgeLock=ScreenEdgeLock(vertical="top", horizontal="right"))),
         direct_position=cart(-29, default_edge_elevation, 1))


@pytest.mark.parametrize("test_case", test_cases, ids=[case.name for case in test_cases])
def test_objectbased(layout, gain_calc, test_case):
    test_case.run(layout, gain_calc)


def test_no_screen_scale(layout):
    layout = evolve(layout, screen=None)
    gain_calc = GainCalc(layout)

    GainCalcTestCase(
        "screen_scale_no_screen",
        dict(position=dict(azimuth=30.0, elevation=0.0, distance=1.0), screenRef=True),
        direct_gains=[("M+030", 1.0)],
        extra_data=ExtraData(
            reference_screen=PolarScreen(aspectRatio=1.5,
                                         centrePosition=PolarPosition(30.0, 0.0, 1.0),
                                         widthAzimuth=30.0)),
    ).run(layout, gain_calc)

    GainCalcTestCase(
        "screen_edge_lock_right_no_screen",
        dict(position=ObjectPolarPosition(azimuth=0.0, elevation=0.0, distance=1.0,
                                          screenEdgeLock=ScreenEdgeLock(horizontal="right"))),
        direct_gains=[("M+000", 1.0)],
    ).run(layout, gain_calc)


def test_objectbased_extent(layout, gain_calc):
    block_formats = [
        AudioBlockFormatObjects(position=dict(azimuth=0, elevation=0, distance=1),
                                width=360, height=360),
        AudioBlockFormatObjects(position=dict(X=0.0, Y=1.0, Z=0.0),
                                width=360, height=360),
        AudioBlockFormatObjects(position=dict(azimuth=0, elevation=0, distance=0)),
        AudioBlockFormatObjects(position=dict(X=0.0, Y=0.0, Z=0.0)),
    ]

    gains_0 = gain_calc.render(ObjectTypeMetadata(block_formats[0]))

    npt.assert_allclose(np.linalg.norm(gains_0), 1.0)
    assert (np.all(gains_0.direct[~layout.is_lfe] > 0.1) and
            np.all(gains_0.diffuse == 0))

    for block_format in block_formats[1:]:
        gains = gain_calc.render(ObjectTypeMetadata(block_format))
        npt.assert_allclose(gains.direct, gains_0.direct)
        npt.assert_allclose(gains.diffuse, gains_0.diffuse)


def test_distance(layout, gain_calc):
    """Check that as the distance is decreased there is more spreading, by
    calculating the energy vector for a range of distances and checking that
    the length increases with the distance.
    """
    def direct_gains(size, distance):
        block_format = AudioBlockFormatObjects(position=dict(azimuth=0, elevation=0, distance=distance),
                                               width=size, height=size)
        return gain_calc.render(ObjectTypeMetadata(block_format)).direct

    for size in [0, 30]:
        distances = np.linspace(0, 1, 10)
        pvs = np.array([direct_gains(size, distance) for distance in distances])
        ev_len = np.linalg.norm(np.square(pvs).dot(layout.norm_positions), axis=1)
        assert np.all(np.diff(ev_len) > 0)


def test_objectbased_depth(layout, gain_calc):
    """Check that with depth behaves like spreading but with more weight in the
    direction of the source."""
    bf_no_depth = AudioBlockFormatObjects(position=dict(azimuth=0, elevation=0, distance=1),
                                          width=360, height=360, depth=0)
    bf_with_depth = AudioBlockFormatObjects(position=dict(azimuth=0, elevation=0, distance=0.5),
                                            width=0, height=0, depth=1)
    gains_no_depth = gain_calc.render(ObjectTypeMetadata(bf_no_depth)).direct
    gains_with_depth = gain_calc.render(ObjectTypeMetadata(bf_with_depth)).direct

    npt.assert_allclose(np.linalg.norm(gains_no_depth), 1.0)
    npt.assert_allclose(np.linalg.norm(gains_with_depth), 1.0)

    front_idx = layout.channel_names.index("M+000")
    assert np.all(gains_with_depth[~layout.is_lfe]) > 0 and gains_with_depth[front_idx] > gains_no_depth[front_idx]


def test_steps(layout, gain_calc):
    """Check for steps in combinations of extent-related parameters"""
    from itertools import product

    e = 1e-4
    params = [
        # distance
        [[0.0, 0.0+e], [0.5], [1.0-e, 1.0, 1.0+e], [2.0]],
        # width
        [[0.0, 0.0+e], [180.0], [360.0-e, 360.0]],
        # height
        [[0.0, 0.0+e], [180.0-e, 180.0, 180.0+e], [360.0-e, 360.0]],
        # depth
        [[0.0, 0.0+e], [0.5], [1.0-e, 1.0]],
    ]

    for params_region in product(*params):
        similar_gains = []
        for distance, width, height, depth in product(*params_region):
            bf = AudioBlockFormatObjects(position=dict(azimuth=0, elevation=0, distance=distance),
                                         width=width, height=height, depth=depth)
            similar_gains.append(gain_calc.render(ObjectTypeMetadata(bf)).direct)
        for gains in similar_gains[1:]:
            npt.assert_allclose(gains, similar_gains[0], atol=1e-3)


def test_divergence_normalised(layout, gain_calc):
    for value, azimuthRange in [(1.0, 0.0), (1.0, 10.0), (0.5, 10.0), (1.0, 40.0), (0.3, 10.0), (0.7, 10.0)]:
        block_format = AudioBlockFormatObjects(position=dict(azimuth=0, elevation=0, distance=1),
                                               objectDivergence=ObjectDivergence(value, azimuthRange=azimuthRange))
        gains = gain_calc.render(ObjectTypeMetadata(block_format))
        npt.assert_allclose(np.linalg.norm(gains), 1.0)


def test_zone_exclusion():
    from ... import bs2051
    from ..gain_calc import ZoneExclusionHandler

    layout = bs2051.get_layout("9+10+3").without_lfe
    zeh = ZoneExclusionHandler(layout)

    def check(zoneExclusion, *excludes):
        expected = np.zeros(len(layout.channels), dtype=bool)
        for exclude in excludes:
            expected[layout.channel_names.index(exclude)] = True

        assert np.all(zeh.get_excluded(zoneExclusion) == expected)

    # polar tests around U+045

    # no tolerance
    check([PolarZone(minAzimuth=40.0, maxAzimuth=50.0, minElevation=25.0, maxElevation=35.0)],
          "U+045")
    # wide tolerance
    check([PolarZone(minAzimuth=45.0, maxAzimuth=45.0, minElevation=30.0, maxElevation=30.0)],
          "U+045")
    # each edge of zone just past channel
    check([PolarZone(minAzimuth=45.1, maxAzimuth=50.0, minElevation=25.0, maxElevation=35.0)])
    check([PolarZone(minAzimuth=40.0, maxAzimuth=44.9, minElevation=25.0, maxElevation=35.0)])
    check([PolarZone(minAzimuth=40.0, maxAzimuth=50.0, minElevation=30.1, maxElevation=35.0)])
    check([PolarZone(minAzimuth=40.0, maxAzimuth=50.0, minElevation=25.0, maxElevation=29.9)])

    # polar tests around M+180; min and max azimuth are always specified clockwise

    # no tolerance
    check([PolarZone(minAzimuth=180.0, maxAzimuth=-180.0, minElevation=0.0, maxElevation=0.0)],
          "M+180")
    # wide tolerance
    check([PolarZone(minAzimuth=175.0, maxAzimuth=-175.0, minElevation=0.0, maxElevation=0.0)],
          "M+180")
    # each edge of zone just past channel
    check([PolarZone(minAzimuth=-179.9, maxAzimuth=-175.0, minElevation=0.0, maxElevation=0.0)])
    check([PolarZone(minAzimuth=175.0, maxAzimuth=179.9, minElevation=0.0, maxElevation=0.0)])

    # cartesian tests around M+000
    check([CartesianZone(minX=0.0, maxX=0.0, minY=1.0, maxY=1.0, minZ=0.0, maxZ=0.0)], "M+000")
    check([CartesianZone(minX=-0.2, maxX=0.2, minY=0.8, maxY=1.2, minZ=-0.2, maxZ=0.2)], "M+000")
    # cartesian tests around M+090
    check([CartesianZone(minX=1.0, maxX=1.0, minY=0.0, maxY=0.0, minZ=0.0, maxZ=0.0)], "M-090")
    check([CartesianZone(minX=0.9, maxX=1.1, minY=-0.1, maxY=0.1, minZ=-0.1, maxZ=0.1)], "M-090")
    # cartesian tests around T+000
    check([CartesianZone(minX=0.0, maxX=0.0, minY=0.0, maxY=0.0, minZ=1.0, maxZ=1.0)], "T+000")
    check([CartesianZone(minX=-0.1, maxX=0.1, minY=-0.1, maxY=0.1, minZ=0.9, maxZ=1.1)], "T+000")

    check([PolarZone(minAzimuth=-180.0, maxAzimuth=180.0, minElevation=0.0, maxElevation=0.0)],
          'M+060', 'M-060', 'M+000', 'M+135', 'M-135', 'M+030', 'M-030', 'M+180', 'M+090', 'M-090')

    check([PolarZone(minAzimuth=0.0, maxAzimuth=0.0, minElevation=90.0, maxElevation=90.0)],
          "T+000")
    check([PolarZone(minAzimuth=90.0, maxAzimuth=90.0, minElevation=90.0, maxElevation=90.0)],
          "T+000")


def test_cube_to_sphere():
    from ..gain_calc import cube_to_sphere, sphere_to_cube
    pos = np.array([1, 1, 0])
    pos_sph = cube_to_sphere(pos)
    pos_cube = sphere_to_cube(pos_sph)

    npt.assert_allclose(pos, pos_cube)
    npt.assert_allclose(cart(-45, 0, 1), pos_sph)

    npt.assert_allclose(np.array([0.0, 0.0, 0.0]),
                        sphere_to_cube(np.array([0.0, 0.0, 0.0])))
    npt.assert_allclose(np.array([0.0, 0.0, 0.0]),
                        cube_to_sphere(np.array([0.0, 0.0, 0.0])))
