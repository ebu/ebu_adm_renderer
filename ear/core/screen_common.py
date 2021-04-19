from attr import attrs, attrib
from ..common import CartesianScreen, PolarScreen
from ..common import azimuth, elevation
from .geom import local_coordinate_system
import numpy as np


@attrs(slots=True)
class PolarEdges(object):
    """Internal screen representation for scaling polar coordinates.

    This stores the azimuths of the right and left edges, and the elevations of
    the top and bottom edges.
    """
    left_azimuth = attrib()
    right_azimuth = attrib()
    bottom_elevation = attrib()
    top_elevation = attrib()

    @classmethod
    def from_screen(cls, screen):
        # Determine the Cartesian position, angle and size of the screen, then
        # use that to determine the edge azimuths and elevations. The screen surface is given by
        #
        #     centre + x * x_vec + y * y_vec
        #
        # for x and y in the range [-1, 1], where x=1, y=1 is the top right
        # corner, and x=1, y=-1 is the bottom right corner.
        centre = screen.centrePosition.as_cartesian_array()

        if isinstance(screen, PolarScreen):
            width = screen.centrePosition.distance * np.tan(np.radians(screen.widthAzimuth / 2.0))
            height = width / screen.aspectRatio

            axes = local_coordinate_system(screen.centrePosition.azimuth, screen.centrePosition.elevation)

            x_vec = axes[0] * width
            z_vec = axes[2] * height

        elif isinstance(screen, CartesianScreen):
            width = screen.widthX / 2.0
            height = width / screen.aspectRatio

            x_vec, z_vec = np.array([[width, 0.0, 0.0], [0.0, 0.0, height]])

        else:
            assert False

        left_azimuth = azimuth(centre - x_vec)
        right_azimuth = azimuth(centre + x_vec)
        if right_azimuth > left_azimuth:
            raise ValueError("invalid screen specification: screen must not extend past -y")

        if (azimuth(centre - z_vec) - azimuth(centre + z_vec)) > 1e-3:
            raise ValueError("invalid screen specification: screen must not extend past +z or -z")

        return cls(left_azimuth=left_azimuth,
                   right_azimuth=right_azimuth,
                   bottom_elevation=elevation(centre - z_vec),
                   top_elevation=elevation(centre + z_vec))


def compensate_position(az, el, layout):
    """Modify az and el so that vertical panning in allocentric coordinates
    produces vertical source positions in the given layout."""
    if "U+045" in layout.channel_names:
        right_az = np.interp(el, [0, 30, 90], [30, 30.0 * (30.0/45.0), 30])
        new_az = np.interp(az, [-180, -30, 30, 180], [-180, -right_az, right_az, 180])

        return new_az, el
    else:
        return az, el
