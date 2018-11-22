from collections import namedtuple
import numpy as np
import warnings
from . import extent
from .. import point_source
from ...options import SubOptions, OptionsHandler
from ..geom import azimuth, elevation, cart, inside_angle_range, local_coordinate_system
from .zone import ZoneExclusionDownmix
from ...fileio.adm.elements import CartesianZone, PolarZone, ObjectCartesianPosition, ObjectPolarPosition
from ..screen_scale import ScreenScaleHandler
from ..screen_edge_lock import ScreenEdgeLockHandler


def cube_to_sphere(position):
    """Warp from positions in a cube to positions in a sphere by scaling
    dependant on the direction.

    Parameters:
        position (array of length 3): Cartesian position

    Returns:
        array of length 3: warped position
    """
    norm = np.linalg.norm(position)
    if norm > 1e-10:
        return position * (np.max(np.abs(position)) / norm)
    else:
        return position


def sphere_to_cube(position):
    """Warp from positions in a sphere to positions in a cube by scaling
    dependant on the direction.

    Parameters:
        position (array of length 3): Cartesian position

    Returns:
        array of length 3: warped position
    """
    norm = np.linalg.norm(position)
    if norm > 1e-10:
        return position * (norm / np.max(np.abs(position)))
    else:
        return position


def coord_trans(position, cartesian):
    """Transform from ADM position information to a unit Cartesian direction
    vector and a distance.

    Parameters:
        position (PolarPosition or CartesianPosition): If Cartesian, has keys X, Y, Z; otherwise has keys
            azimuth, elevation, distance.
        cartesian (bool): Block format 'cartesian' flag.

    Returns:
        array of shape (3,): The direction component as a normalised Cartesian vector.
        float: The distance component of the source.
    """
    if isinstance(position, ObjectPolarPosition):
        cart_pos = cart(position.azimuth, position.elevation, position.distance)
    elif isinstance(position, ObjectCartesianPosition):
        cart_pos = position.as_cartesian_array()
    else:
        assert False, "position should be ObjectPolarPosition or ObjectCartesianPosition"  # pragma: no cover

    if cartesian:
        cart_pos = cube_to_sphere(cart_pos)

    return cart_pos


class ChannelLockHandler(object):
    """Implementation of channel locking as a position transformation."""

    def __init__(self, layout):
        self.positions = layout.norm_positions

        azimuths = np.array([channel.polar_position.azimuth for channel in layout.channels])
        elevations = np.array([channel.polar_position.elevation for channel in layout.channels])

        # define a priority for channels, used to select a single channel when
        # multiple channels are the same distance from the position. Channels
        # with the lowest absolute elevation have the highest priority, with
        # ties broken by elevation, absolute azimuth then azimuth.
        priority_order = np.lexsort((azimuths, np.abs(azimuths),
                                     elevations, np.abs(elevations)))
        self.channel_priority = np.arange(len(layout.channels))[priority_order]

    def handle(self, position, channelLock):
        """Apply channel lock to a position.

        Parameters:
            position (array of length 3): Cartesian source position
            channelLock (fileio.adm.elements.ChannelLock or None):
                Channel lock information if it is enabled
        Returns:
            array of shape (3,) representing a Cartesian position.
        """
        tol = 1e-5

        if channelLock is not None:
            distances = np.linalg.norm(position - self.positions, axis=1)
            min_dist = np.min(distances)

            all_closest = np.where(distances < min_dist + tol)[0]
            all_closest_priorities = self.channel_priority[all_closest]

            closest = all_closest[np.argmin(all_closest_priorities)]

            if channelLock.maxDistance is None or distances[closest] <= channelLock.maxDistance + tol:
                return self.positions[closest]
        return position


def diverge(position, objectDivergence, cartesian):
    """Implement object divergence by duplicating and modifying source
    directions.

    Parameters:
        position (array of length 3): Cartesian source position
        objectDivergence (fileio.adm.elements.ObjectDivergence): object divergence information
        cartesian (bool): Block format 'cartesian' flag.

    Returns:
        array of length n: gain for each position
        array of shape (n, 3): modified source positions
    """
    if objectDivergence is None or objectDivergence.value == 0.0:
        return np.array([1.0]), position[np.newaxis]
    else:
        # Find gains g_l, g_c, g_r for the left, centre and right objects for
        # divergence value x such that:
        # - g_l + g_r + g_c = 1 for all x
        # - g_l = g_r = 0 and g_c = 1 for x = 0
        # - g_l = g_r = g_c = 1/3 for x = 0.5
        # - g_l = g_r = 0.5 and g_c = 0 for x = 1
        value = objectDivergence.value
        g_l = g_r = value / (value + 1)
        g_c = (1 - value) / (value + 1)

        if cartesian:
            if objectDivergence.azimuthRange is not None:
                warnings.warn("azimuthRange specified for blockFormat in Cartesian mode; using Cartesian divergence")

            # apply divergence in cube-space then translate back
            pos_cube = sphere_to_cube(position)

            positionRange = (objectDivergence.positionRange
                             if objectDivergence.positionRange is not None
                             else 0.0)

            pos_left_cube = pos_cube + np.array([positionRange, 0, 0])
            pos_right_cube = pos_cube - np.array([positionRange, 0, 0])

            pos_centre = cube_to_sphere(pos_cube)
            pos_left = cube_to_sphere(pos_left_cube)
            pos_right = cube_to_sphere(pos_right_cube)

            return np.array([g_l, g_c, g_r]), np.array([pos_left, pos_centre, pos_right])
        else:
            if objectDivergence.positionRange is not None:
                warnings.warn("positionRange specified for blockFormat in polar mode; using polar divergence")

            azimuthRange = (objectDivergence.azimuthRange
                            if objectDivergence.azimuthRange is not None
                            else 45.0)

            distance = np.linalg.norm(position)
            p_l, p_r = cart(azimuthRange, 0, distance), cart(-azimuthRange, 0, distance)

            M = local_coordinate_system(azimuth(position), elevation(position)).T
            p_l = np.dot(M, p_l)
            p_r = np.dot(M, p_r)

            return np.array([g_l, g_c, g_r]), np.array([p_l, position, p_r])


class ExtentHandler(object):
    """Implementation of extent panning that also handles point source panning
    for zero-size objects.
    """

    def __init__(self, point_source_panner):
        """
        Parameters:
            point_source_panner (point_source.PointSourcePanner): point source
                panner to use
        """
        self.polar_extent_panner = extent.PolarExtentPanner(point_source_panner.handle)
        self.cart_extent_panner = extent.CartExtentPanner(point_source_panner.handle,
                                                          spreading_panner=self.polar_extent_panner.spreading_panner)

    @classmethod
    def extent_mod(cls, extent, distance):
        """Modify an extent parameter given a distance.

        A right triangle if formed, with the adjacent edge being the distance,
        and the opposite edge being determined from the extent. The angle
        formed is then used to determine the new extent.

        - at distance=0, the extent is always 360
        - at distance=1, the original extent is used
        - at distance>1, the extent decreases
        - in 0 < distance < 1, the extent changes more steeply around 0 for smaller extents
        """
        min_size = 0.2
        size = np.interp(extent, [0, 360], [min_size, 1.0])
        extent_1 = 4 * np.degrees(np.arctan2(size, 1.0))
        return np.interp(4 * np.degrees(np.arctan2(size, distance)),
                         [0, extent_1, 360.0],
                         [0, extent, 360.0])

    def handle(self, position, width, height, depth, cartesian):
        """Calculate loudspeaker gains given position and extent parameters.

        Parameters:
            position (array of length 3): Cartesian source position
            width (float): block format width parameter
            height (float): block format height parameter
            depth (float): block format depth parameter
            distance (float): distance part of the position
            cartesian (bool): is this block format in Cartesian mode?
        Returns:
            gain (array of length n): loudspeaker gains of length
            self.point_source_panner.num_channels.
        """
        if cartesian:
            size = np.array([width, depth, height])
            return self.cart_extent_panner.calc_pv_spread(position, size)
        else:
            distance = np.linalg.norm(position)

            if depth != 0:
                distances = np.array([distance + depth / 2.0,
                                      distance - depth / 2.0])
                distances[distances < 0] = 0.0
            else:
                distances = [distance]

            pvs = [self.polar_extent_panner.calc_pv_spread(position,
                                                           self.extent_mod(width, end_distance),
                                                           self.extent_mod(height, end_distance))
                   for end_distance in distances]

            if len(pvs) == 1:
                return pvs[0]
            else:
                return np.sqrt(np.mean(np.square(pvs), axis=0))


class ZoneExclusionHandler(object):

    def __init__(self, layout):
        self.num_channels = len(layout.channels)

        self.positions = layout.nominal_positions
        self.azimuths = np.array([channel.polar_nominal_position.azimuth for channel in layout.channels])
        self.elevations = np.array([channel.polar_nominal_position.elevation for channel in layout.channels])

        self.zed = ZoneExclusionDownmix(layout)

    def get_excluded(self, zoneExclusion):
        excluded = np.zeros(self.num_channels, dtype=bool)

        epsilon = 1e-6

        for zone in zoneExclusion:
            if isinstance(zone, CartesianZone):
                excluded |= (
                    (self.positions[:, 0] - epsilon < zone.maxX) &
                    (self.positions[:, 1] - epsilon < zone.maxY) &
                    (self.positions[:, 2] - epsilon < zone.maxZ) &
                    (self.positions[:, 0] + epsilon > zone.minX) &
                    (self.positions[:, 1] + epsilon > zone.minY) &
                    (self.positions[:, 2] + epsilon > zone.minZ)
                )
            elif isinstance(zone, PolarZone):
                excluded |= (
                    (self.elevations - epsilon < zone.maxElevation) &
                    (self.elevations + epsilon > zone.minElevation) &
                    (
                        # speakers at the poles have indeterminate elevation and should match any range
                        (np.abs(self.elevations) > 90.0 - epsilon) |
                        [inside_angle_range(az, zone.minAzimuth, zone.maxAzimuth, tol=epsilon)
                         for az in self.azimuths]
                    )
                )
            else:
                assert False, "wrong type in zone"  # pragma: no cover

        return excluded

    def handle(self, gains, zoneExclusion):
        excluded = self.get_excluded(zoneExclusion)
        downmix = self.zed.downmix_for_excluded(excluded)
        return np.sqrt(np.dot(gains**2, downmix))


DirectDiffuseGains = namedtuple("DirectDiffuseGains", ["direct", "diffuse"])


def direct_diffuse_split(gains, diffuse):
    """Split gains into a direct and diffuse path.

    Parameters:
        gains (array of n floats): input gains
        diffuse (float): ADM diffuse parameter

    Returns:
        DirectDiffuseGains: gains for direct and diffuse paths
    """
    return DirectDiffuseGains(
        direct=gains * np.sqrt(1.0 - diffuse),
        diffuse=gains * np.sqrt(diffuse)
    )


class GainCalc(object):
    options = OptionsHandler(
        point_source_opts=SubOptions(
            handler=point_source.configure_options,
            description="options for point source panner",
        ),
    )

    @options.with_defaults
    def __init__(self, layout, point_source_opts):
        self.point_source_panner = point_source.configure(layout.without_lfe, **point_source_opts)
        self.screen_edge_lock_handler = ScreenEdgeLockHandler(layout.screen)
        self.screen_scale_handler = ScreenScaleHandler(layout.screen)
        self.channel_lock_handler = ChannelLockHandler(layout.without_lfe)
        self.extent_panner = ExtentHandler(self.point_source_panner)
        self.zone_exclusion_handler = ZoneExclusionHandler(layout.without_lfe)

        self.is_lfe = layout.is_lfe

    def render(self, object_meta):
        block_format = object_meta.block_format

        position = coord_trans(block_format.position, block_format.cartesian)

        position = self.screen_scale_handler.handle(position, block_format.screenRef, object_meta.extra_data.reference_screen)

        position = self.screen_edge_lock_handler.handle_vector(position, block_format.position.screenEdgeLock)

        position = self.channel_lock_handler.handle(position, block_format.channelLock)

        diverged_gains, diverged_positions = diverge(position, block_format.objectDivergence, block_format.cartesian)

        gains_for_each_pos = np.apply_along_axis(self.extent_panner.handle, 1, diverged_positions,
                                                 block_format.width, block_format.height, block_format.depth,
                                                 block_format.cartesian)

        gains = np.sqrt(np.dot(diverged_gains, gains_for_each_pos**2))

        gains = self.zone_exclusion_handler.handle(gains, block_format.zoneExclusion)

        gains = np.nan_to_num(gains)

        gains *= block_format.gain

        # add in silent LFE channels
        gains_full = np.zeros(len(self.is_lfe))
        gains_full[~self.is_lfe] = gains

        return direct_diffuse_split(gains_full, block_format.diffuse)
