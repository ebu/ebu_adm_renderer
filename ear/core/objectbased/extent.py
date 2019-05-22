from attr import attrs, attrib
import numpy as np
from ..geom import cart, azimuth, elevation, local_coordinate_system
from ..util import safe_norm_position


class SpreadingPanner(object):
    """A wrapper around another panner that pans using a uniform spread of
    points around the sphere given a weighting function."""

    def __init__(self, panning_func, n_rows):
        """
        Args:
            panner: panner used to find panning values of virtual sources
            n_rows (int): number of rows rows to place on sphere, e.g. 37 for 5 degree spacing
        """
        self.panning_func = panning_func
        self.n_rows = n_rows
        self.panning_positions = self.generate_panning_positions_even(n_rows)
        self.panning_positions_results = np.apply_along_axis(panning_func, 1, self.panning_positions)

    @classmethod
    def generate_panning_positions_even(cls, n_rows):
        """Generate points spread evenly on the sphere.
        Based on http://web.archive.org/web/20150108040043/http://www.math.niu.edu/~rusin/known-math/95/equispace.elect

        Args:
            n_rows (int): number of rows rows to place on sphere, e.g. 37 for 5 degree spacing

        Returns:
            (n,3) cartesian array.
        """
        elevations = np.linspace(-90, 90, num=n_rows, endpoint=True)

        positions = []

        for el in elevations:
            radius = np.cos(np.radians(el))
            perimiter = 2 * np.pi * radius
            perimiter_centre = 2 * np.pi

            n_points = int(round((perimiter / perimiter_centre) * 2 * (n_rows - 1)))
            if n_points == 0: n_points = 1

            azimuths = np.linspace(0, 360, num=n_points, endpoint=False)
            for az in azimuths:
                positions.append(cart(az, el, 1))
        return np.array(positions)

    def panning_values_for_weight(self, weight_for_vec):
        """Panning values for a given weighting function.

        Args:
            weight_for_vec: function from Cartesian position to weight in range (0, 1).
                            This must accept a np array of size (n, 3) for n
                            points (i.e. it must be vectorised)

        Returns:
            panning value for each speaker.
        """
        values_for_pos = weight_for_vec(self.panning_positions)
        total_pv = np.dot(values_for_pos, self.panning_positions_results)
        return total_pv / np.linalg.norm(total_pv)


@attrs
class ExtentPanner(object):
    """Base class for extent panners that use a SpreadingPanner."""

    panning_func = attrib()
    n_rows = attrib(default=37)
    spreading_panner = attrib()

    @spreading_panner.default
    def init_spreading_panner(self):
        return SpreadingPanner(self.panning_func, self.n_rows)

    @spreading_panner.validator
    def validate_spreading_panner(self, attribute, value):
        assert value.panning_func == self.panning_func
        assert value.n_rows == self.n_rows


class PolarExtentPanner(ExtentPanner):

    fade_width = 10.0  # degrees

    @classmethod
    def get_weight_func(cls, position, width, height):
        """Weighting function for spread sources.

        The weighting function is one inside a region approximately determined
        by a width x height rectangle in azimuth-elevation space, with
        maximally-sized rounded corners; the shape of the corners is calculated
        using the vector angle from their centres (always directly above or
        below the source position) so as to avoid issues at the poles.

        The two straight edges of the rectangle are always parallel in
        Cartesian space; this is achieved by following azimuth lines; for tall
        sources, the whole coordinate system is rotated 90 degrees about the
        source position to achieve this.

        Note that for sources where width == height, this degrades to a
        circular region relative to the source position.

        To make the two ends meet, the width is adjusted such that a width of
        180 degrees is mapped to width + height.

        Parameters:
            position (array of shape (3,)): Centre of the extent.
            width (float): Width of the extent in degrees from one edge to the other.
            height (float): Height of the extent in degrees from one edge to the other.

        Returns:
            weighting function from array of (n, 3) to (n)
        """
        width = np.radians(width) / 2
        height = np.radians(height) / 2

        # basis vectors to rotate the vsource positions towards position
        basises = calc_basis(position)

        circle_radius = min(width, height)

        # Flip the width and the height such that it is always wider than it is
        # high from here in.
        if height > width:
            width, height = height, width
            flipped_basises = basises[[2, 1, 0]]
        else:
            flipped_basises = basises

        # modify the width to make it meet at the back.
        width_full = np.pi + height  # width we'd need to make it meet at the back
        # interpolate to this from a width of pi/2 to pi
        width_mod = np.interp(width,
                              [0, np.pi/2, np.pi],
                              [0, np.pi/2, width_full])
        # apply this fully for a height of less than pi/4; tail off until pi/2
        width = np.interp(height,
                          [0,         np.pi/4,   np.pi/2, np.pi],  # noqa
                          [width_mod, width_mod, width,   width])  # noqa

        # angle of the circle centres from the source position; width is to the end of the rectangle.
        circle_pos = width - circle_radius

        # Cartesian circle centres
        circle_positions = cart_on_basis(flipped_basises,
                                         np.array([-circle_pos, circle_pos]),
                                         np.zeros(2))

        def f(vsource_positions):
            # Flipped azimuths and elevations; the straight edges are always along azimuth lines.
            azimuths, elevations = azimuth_elevation_on_basis(flipped_basises, vsource_positions)

            # The distance is the angle away from the defined shape; 0 or negative is inside.
            distances = np.zeros(len(vsource_positions))

            # for the straight lines
            on_flat_part = abs(azimuths) <= circle_pos
            distances[on_flat_part] = np.abs(elevations[on_flat_part]) - circle_radius

            # distance from the closest circle centre
            on_circle = ~on_flat_part
            circle_distances = np.arccos(np.clip(np.dot(vsource_positions[on_circle], circle_positions.T), -1, 1))
            distances[on_circle] = np.min(circle_distances, axis=1) - circle_radius

            # fade the weight from one to zero over fade_width
            return np.interp(distances, [0, np.radians(cls.fade_width)], [1, 0])

        return f

    @classmethod
    def plot_weight_func(cls, weight_func, points):
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa

        weights = weight_func(points)

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d', aspect=1)

        nonzero_points, nonzero_weights = points[weights > 0], weights[weights > 0]

        colors = np.zeros((len(nonzero_points), 4))
        colors[:, 0:3] = (nonzero_points + 1) / 2
        colors[:, 0:3] /= np.linalg.norm(colors[:, 0:3], ord=1, axis=1, keepdims=True)
        colors[:, 3] = nonzero_weights

        ax.scatter(*nonzero_points.T, color=colors, depthshade=0)
        ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_zlim(-1, 1)
        # fig.colorbar(plot, shrink=0.5, aspect=10)
        plt.show()

    def calc_pv_spread(self, position, width, height):
        """Calculate the speaker panning values for the position, width, and
        height of a source; this just deals with the positioning and spreading.
        """
        # When calculating the spread panning values the width and height are
        # set to at least fade_width. For sizes where any of the dimensions is
        # less than this, interpolate linearly between the point and spread
        # panning values.
        ammount_spread = np.interp(max(width, height), [0, self.fade_width], [0, 1])
        ammount_point = 1.0 - ammount_spread

        pv = 0.0
        if ammount_point > 1e-10:
            pv += ammount_point * self.panning_func(position) ** 2
        if ammount_spread > 1e-10:
            # minimum width and height as above
            width = np.maximum(width, self.fade_width / 2)
            height = np.maximum(height, self.fade_width / 2)

            weight_f = self.get_weight_func(position, width, height)
            pv += ammount_spread * self.spreading_panner.panning_values_for_weight(weight_f) ** 2

        return np.sqrt(pv)


def calc_basis(source_pos):
    """Calculate basis vectors that rotate (0, 1, 0) onto source_pos."""
    source_pos = safe_norm_position(source_pos)
    az, el = azimuth(source_pos), elevation(source_pos)

    # points near the poles have indeterminate azimuth; assume 0
    if np.abs(el) > 90 - 1e-5:
        az = 0

    return local_coordinate_system(az, el)


def cart_on_basis(basis, az, el):
    """Polar to Cartesian in radians with no distance, in a given basis."""
    cart_pos_rel = np.array([
        np.sin(az) * np.cos(el),
        np.cos(az) * np.cos(el),
        np.sin(el)]).T

    return np.dot(cart_pos_rel, basis)


def azimuth_elevation_on_basis(basis, vsource_pos):
    """Cartesian to polar in radians, in a given basis, assuming unit-length vectors."""
    # project onto each basis
    components = np.dot(vsource_pos, basis.T)

    # clip components to keep arcsin happy
    components = np.clip(components, -1.0, 1.0)

    azimuth = np.arctan2(components[..., 0],   # right
                         components[..., 1])   # forward
    elevation = np.arcsin(components[..., 2])  # up

    return azimuth, elevation
