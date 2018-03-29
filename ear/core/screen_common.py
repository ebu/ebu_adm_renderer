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

        return cls(left_azimuth=azimuth(centre - x_vec),
                   right_azimuth=azimuth(centre + x_vec),
                   bottom_elevation=elevation(centre - z_vec),
                   top_elevation=elevation(centre + z_vec))


@attrs(slots=True)
class CartesianEdges(object):
    """Internal screen representation for scaling cartesian coordinates.

    This stores the Xs of the right and left edges, and the Zs of
    the top and bottom edges.
    """
    left_X = attrib()
    right_X = attrib()
    bottom_Z = attrib()
    top_Z = attrib()

    @classmethod
    def from_screen(cls, screen):
        if isinstance(screen, PolarScreen):
            centre_position = screen.centrePosition.as_cartesian_position()
            width_x = (2.0 * screen.centrePosition.distance *
                       np.tan(np.radians(screen.widthAzimuth / 2.0)))
            height_z = width_x / screen.aspectRatio
            return cls(left_X=centre_position.X - width_x / 2.0,
                       right_X=centre_position.X + width_x / 2.0,
                       bottom_Z=centre_position.Z - height_z / 2.0,
                       top_Z=centre_position.Z + height_z / 2.0)

        elif isinstance(screen, CartesianScreen):
            height_z = screen.widthX / screen.aspectRatio

            return cls(left_X=screen.centrePosition.X - screen.widthX / 2.0,
                       right_X=screen.centrePosition.X + screen.widthX / 2.0,
                       bottom_Z=screen.centrePosition.Z - height_z / 2.0,
                       top_Z=screen.centrePosition.Z + height_z / 2.0)

        else:
            assert False
