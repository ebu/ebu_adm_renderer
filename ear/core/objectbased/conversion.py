from attr import evolve, attrib, attrs
from ...fileio.adm.elements import (
    AudioBlockFormatObjects,
    ObjectPolarPosition,
    ObjectCartesianPosition,
)
from ..geom import azimuth, inside_angle_range, local_coordinate_system, relative_angle
import numpy as np


def to_polar(block_format: AudioBlockFormatObjects) -> AudioBlockFormatObjects:
    """Convert a block format to use polar coordinates according to ITU-R
    BS.2127-0 section 10.

    The cartesian flag will be set to match the coordinates used.

    The position, width, height and depth will be converted; the rest of the
    parameters will be unmodified.
    """
    block_format = _fix_cartesian_flag(block_format)
    if not block_format.cartesian:
        return block_format
    else:
        (azimuth, elevation, distance,
         width, height, depth) = extent_cart_to_polar(block_format.position.X,
                                                      block_format.position.Y,
                                                      block_format.position.Z,
                                                      block_format.width,
                                                      block_format.depth,
                                                      block_format.height)

        return evolve(block_format,
                      position=ObjectPolarPosition(azimuth, elevation, distance,
                                                   screenEdgeLock=block_format.position.screenEdgeLock),
                      width=width, height=height, depth=depth,
                      cartesian=False
                      )


def to_cartesian(block_format: AudioBlockFormatObjects) -> AudioBlockFormatObjects:
    """Convert a block format to use Cartesian coordinates according to ITU-R
    BS.2127-0 section 10.

    The cartesian flag will be set to match the coordinates used.

    The position, width, height and depth will be converted; the rest of the
    parameters will be unmodified.
    """
    block_format = _fix_cartesian_flag(block_format)
    if block_format.cartesian:
        return block_format
    else:
        (X, Y, Z,
         width, depth, height) = extent_polar_to_cart(block_format.position.azimuth,
                                                      block_format.position.elevation,
                                                      block_format.position.distance,
                                                      block_format.width,
                                                      block_format.height,
                                                      block_format.depth)

        return evolve(block_format,
                      position=ObjectCartesianPosition(X, Y, Z,
                                                       screenEdgeLock=block_format.position.screenEdgeLock),
                      width=width, height=height, depth=depth,
                      cartesian=True
                      )


def _fix_cartesian_flag(block_format):
    if hasattr(block_format.position, 'X') and hasattr(block_format.position, 'Y'):
        return evolve(block_format, cartesian=True)
    elif hasattr(block_format.position, 'azimuth') and hasattr(block_format.position, 'elevation'):
        return evolve(block_format, cartesian=False)
    return block_format


@attrs
class Conversion(object):

    mapping = attrib()
    el_top = attrib()
    el_top_tilde = attrib()

    @classmethod
    def init(cls):
        mapping = [
            (0, np.r_[0, 1, 0]),
            (-30, np.r_[1, 1, 0]),
            (-110, np.r_[1, -1, 0]),
            (110, np.r_[-1, -1, 0]),
            (30, np.r_[-1, 1, 0]),
        ]

        return cls(
            mapping=mapping,
            el_top=30,
            el_top_tilde=45,
        )

    @classmethod
    def _map_az_to_linear(cls, left_az, right_az, azimuth):
        mid_az = (left_az + right_az) / 2.0
        az_range = right_az - mid_az

        rel_az = azimuth - mid_az

        gain_r = 0.5 + 0.5 * np.tan(np.radians(rel_az)) / np.tan(np.radians(az_range))

        return np.arctan2(gain_r, 1-gain_r) * (2 / np.pi)

    @classmethod
    def _map_linear_to_az(cls, left_az, right_az, x):
        mid_az = (left_az + right_az) / 2.0
        az_range = right_az - mid_az

        gain_l_, gain_r_ = np.cos(x * (np.pi / 2)), np.sin(x * (np.pi / 2))
        gain_r = gain_r_ / (gain_l_ + gain_r_)

        rel_az = np.degrees(np.arctan(2 * (gain_r - 0.5) * np.tan(np.radians(az_range))))

        return mid_az + rel_az

    def _find_sector(self, az):
        for i in range(len(self.mapping)):
            j = (i + 1) % len(self.mapping)

            if inside_angle_range(az, self.mapping[j][0], self.mapping[i][0]):
                return self.mapping[i], self.mapping[j]

        assert False

    def point_polar_to_cart(self, az, el, d):
        """Convert a position from polar to Cartesian according to ITU-R
        BS.2127-0 section 10.

        Parameters:
            az (float): azimuth
            el (float): elevation
            d (float): distance

        Returns:
            np.ndarray of shape (3,): converted Cartesian position
        """
        if np.abs(el) > self.el_top:
            el_tilde = self.el_top_tilde + (90.0 - self.el_top_tilde) * (np.abs(el) - self.el_top) / (90 - self.el_top)
            z = d * np.sign(el)
            r_xy = d * np.tan(np.radians(90 - el_tilde))
        else:
            el_tilde = self.el_top_tilde * el / self.el_top
            z = np.tan(np.radians(el_tilde)) * d
            r_xy = d

        (left_az, left_pos), (right_az, right_pos) = self._find_sector(az)

        rel_az = relative_angle(right_az, az)
        rel_left_az = relative_angle(right_az, left_az)
        p = self._map_az_to_linear(rel_left_az, right_az, rel_az)

        x, y, _z = r_xy * (left_pos + (right_pos - left_pos) * p)

        return np.array([x, y, z])

    def _find_cart_sector(self, az):
        for i in range(len(self.mapping)):
            j = (i + 1) % len(self.mapping)

            if inside_angle_range(az, azimuth(self.mapping[j][1]), azimuth(self.mapping[i][1])):
                return self.mapping[i], self.mapping[j]

        assert False

    def point_cart_to_polar(self, x, y, z):
        """Convert a position from Cartesian to polar according to ITU-R
        BS.2127-0 section 10.

        Parameters:
            x (float): X coordinate
            y (float): Y coordinate
            z (float): Z coordinate

        Returns:
            (float, float, float): converted azimuth, elevation and distance
        """
        eps = 1e-10
        if np.abs(x) < eps and np.abs(y) < eps:
            if np.abs(z) < eps:
                return 0.0, 0.0, 0.0
            else:
                return 0.0, np.sign(z) * 90, np.abs(z)

        (left_az, left_pos), (right_az, right_pos) = self._find_cart_sector(azimuth([x, y, 0]))

        g_lr = np.dot([x, y], np.linalg.inv([left_pos[[0, 1]], right_pos[[0, 1]]]))
        r_xy = np.sum(g_lr)

        rel_left_az = relative_angle(right_az, left_az)
        az = self._map_linear_to_az(rel_left_az, right_az, g_lr[1] / r_xy)
        az = relative_angle(-180, az)

        el_tilde = np.degrees(np.arctan(z / r_xy))

        if np.abs(el_tilde) > self.el_top_tilde:
            abs_el = self.el_top + (90.0 - self.el_top) * (np.abs(el_tilde) - self.el_top_tilde) / (90 - self.el_top_tilde)
            el = np.sign(el_tilde) * abs_el
            d = np.abs(z)
        else:
            el = self.el_top * el_tilde / self.el_top_tilde
            d = r_xy

        return az, el, d

    def extent_polar_to_cart(self, az, el, dist, width, height, depth):
        """Convert a position and extent parameters from polar to Cartesian
        according to ITU-R BS.2127-0 section 10.

        Parameters:
            az (float): azimuth
            el (float): elevation
            dist (float): distance
            width (float): width parameter
            height (float): height parameter
            depth (float): depth parameter

        Returns:
            (float, float, float, float, float, float): converted X, Y, Z,
            width (X size), depth (Y size) and height (Z size)
        """
        x, y, z = self.point_polar_to_cart(az, el, dist)

        front_xs, front_ys, front_zs = self._whd2xyz(width, height, depth)
        M = local_coordinate_system(az, el) * np.array([[front_xs], [front_ys], [front_zs]])
        xs, ys, zs = np.linalg.norm(M, axis=0)

        return x, y, z, xs, ys, zs

    def extent_cart_to_polar(self, x, y, z, xs, ys, zs):
        """Convert a position and extent parameters from Cartesian to polar
        according to ITU-R BS.2127-0 section 10.

        Parameters:
            x (float): X coordinate
            y (float): Y coordinate
            z (float): Z coordinate
            xs (float): width (X size)
            ys (float): depth (Y size)
            zs (float): height (Z size)

        Returns:
            (float, float, float, float, float, float): converted azimuth,
            elevation, distance, width, height and depth
        """
        az, el, dist = self.point_cart_to_polar(x, y, z)

        M = local_coordinate_system(az, el).T * np.array([[xs], [ys], [zs]])
        xs, ys, zs = np.linalg.norm(M, axis=0)
        width, height, depth = self._xyz2whd(xs, ys, zs)

        return az, el, dist, width, height, depth

    @classmethod
    def _whd2xyz(cls, width, height, depth):
        x_size_width = np.sin(np.radians(width / 2.0)) if width < 180.0 else 1.0
        y_size_width = (1 - np.cos(np.radians(width / 2.0))) / 2.0

        z_size_height = np.sin(np.radians(height / 2.0)) if height < 180.0 else 1.0
        y_size_height = (1 - np.cos(np.radians(height / 2.0))) / 2.0

        y_size_depth = depth

        return x_size_width, max(y_size_width, y_size_height, y_size_depth), z_size_height

    @classmethod
    def _xyz2whd(cls, s_x, s_y, s_z):
        width_from_sx = 2 * np.degrees(np.arcsin(s_x))
        width_from_sy = 2 * np.degrees(np.arccos(1 - 2 * s_y))

        width = width_from_sx + s_x * max(width_from_sy - width_from_sx, 0)

        height_from_sz = 2 * np.degrees(np.arcsin(s_z))
        height_from_sy = 2 * np.degrees(np.arccos(1 - 2 * s_y))

        height = height_from_sz + s_z * max(height_from_sy - height_from_sz, 0)

        # depth is the y size that is not accounted for by the calculated width and
        # height
        equiv_y = cls._whd2xyz(width, height, 0.0)[1]
        depth = max(0.0, s_y - equiv_y)

        return width, height, depth


conversion = Conversion.init()

point_polar_to_cart = conversion.point_polar_to_cart
point_cart_to_polar = conversion.point_cart_to_polar
extent_polar_to_cart = conversion.extent_polar_to_cart
extent_cart_to_polar = conversion.extent_cart_to_polar
