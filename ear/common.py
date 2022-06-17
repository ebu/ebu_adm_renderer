from attr import attrs, attrib
from attr.validators import instance_of
import numpy as np


def validate_range(minimum, maximum):
    def f(instance, attribute, value):
        if not (minimum <= value <= maximum):
            raise ValueError('value "%s" out of range ( % s, % s)'
                             % (value, minimum, maximum))
    return f


def list_of(type):
    """Attrs validator that checks for a list containing only a given type.

    Parameters:
        type: expected type of list items

    Returns:
        function: Validation function as required by the attr.attrib validator
        argument.
    """
    list_validator = instance_of(list)

    def f(inst, attr, value):
        list_validator(inst, attr, value)

        for item in value:
            if not isinstance(item, type):
                raise TypeError(
                    "'{name}' items must be {type!r} (got {item!r} that is a "
                    "{actual!r})."
                    .format(name=attr.name, type=type,
                            actual=item.__class__, item=item),
                    attr, type, item,
                )
    return f


def cart(az, el, dist, axis=-1):
    """Convert ADM-format polar positions to ADM-format Cartesian.

    Parameters:
        az: Azimuths in degrees, angle measured anticlockwise from front.
        el: Elevations in degrees, angle measured up from equator.
        r: Radii.
        axis: Index of the new axis in the result; see :func:`numpy.stack`. -1
            (default) adds a new axis at the end.

    Returns:
        ndarray: Same shape as broadcasting az, el and r together, with a new
        axis at `axis` containing the X, Y and Z coordinates.

    Examples:
        >>> cart(0, 0, 1)
        array([0., 1., 0.])
        >>> cart(90, 0, 1).round(6)
        array([-1.,  0.,  0.])
        >>> cart(0, 90, 1).round(6)
        array([0., 0., 1.])
        >>> # inputs are broadcast together...
        >>> cart([0, 90], 0, 1).round(6)
        array([[ 0.,  1.,  0.],
               [-1.,  0.,  0.]])
        >>> # ... along the given axis
        >>> cart([0, 90], 0, 1, axis=0).round(6)
        array([[ 0., -1.],
               [ 1.,  0.],
               [ 0.,  0.]])
    """
    az, el, dist = np.broadcast_arrays(az, el, dist)

    return np.stack((np.sin(np.radians(-az)) * np.cos(np.radians(el)) * dist,
                     np.cos(np.radians(-az)) * np.cos(np.radians(el)) * dist,
                     np.sin(np.radians(el)) * dist),
                    axis=axis)


def azimuth(positions, axis=-1):
    """Get the azimuth in degrees from ADM-format Cartesian positions.

    Parameters:
        positions (array of float): Cartesian positions, with X, Y and Z
            positions along axis `axis`.
        axis (int): Axis to find coordinates along. -1 (default) indicates the
            last axis.

    Returns:
        array: Azimuths of the positions in degrees; has the same shape as
            positions, with `axis` removed.

    Raises:
        ValueError: If positions does not have the right length along axis.

    Examples:

        >>> azimuth([0, 1, 0]).round(0).astype(int)
        0
        >>> azimuth([[1, 0, 0], [0, 1, 0]]).round(0).astype(int)
        array([-90,   0])
        >>> azimuth([[1, 0], [0, 1], [0, 0]], axis=0).round(0).astype(int)
        array([-90,   0])
    """
    x, y, z = np.moveaxis(positions, axis, 0)
    return -np.degrees(np.arctan2(x, y))


def elevation(positions, axis=-1):
    """Get the elevation in degrees from ADM-format Cartesian positions.

    See :func:`azimuth`.
    """
    x, y, z = np.moveaxis(positions, axis, 0)
    radius = np.hypot(x, y)
    return np.degrees(np.arctan2(z, radius))


def distance(positions, axis=-1):
    """Get the distance from ADM-format Cartesian positions.

    See :func:`azimuth`.
    """
    return np.linalg.norm(positions, axis=axis)


class PolarPositionMixin(object):
    """Methods to be defined on all polar position objects which have azimuth,
    elevation and distance attributes."""
    __slots__ = ()

    def as_cartesian_array(self):
        """Get the position as a Cartesian array.

        Returns:
            np.array of shape (3,): equivalent X, Y and Z coordinates
        """
        return cart(self.azimuth, self.elevation, self.distance)

    def as_cartesian_position(self) -> "CartesianPosition":
        """Get the equivalent cartesian position."""
        x, y, z = self.as_cartesian_array()
        return CartesianPosition(x, y, z)

    @property
    def norm_position(self):
        return cart(self.azimuth, self.elevation, 1.0)


class CartesianPositionMixin(object):
    """Methods to be defined on all Cartesian position objects which have X, Y
    and Z attributes."""
    __slots__ = ()

    def as_cartesian_array(self):
        """Get the position as a Cartesian array.

        Returns:
            np.array of shape (3,): equivalent X, Y and Z coordinates
        """
        return np.array([self.X, self.Y, self.Z])

    def as_polar_position(self) -> "PolarPosition":
        """Get the equivalent cartesian position."""
        cart_array = self.as_cartesian_array()
        return PolarPosition(azimuth(cart_array), elevation(cart_array), distance(cart_array))


class Position(object):
    """A 3D position represented in polar or Cartesian coordinates."""
    __slots__ = ()


@attrs(slots=True)
class PolarPosition(Position, PolarPositionMixin):
    """A 3D position represented in ADM-format polar coordinates.

    Attributes:
        azimuth (float): anti-clockwise azimuth in degrees, measured from the
            front
        elevation (float): elevation in degrees, measured upwards from the
            equator
        distance (float): distance relative to the audioPackFormat
            absoluteDistance parameter
    """

    azimuth = attrib(converter=float, validator=validate_range(-180, 180))
    elevation = attrib(converter=float, validator=validate_range(-90, 90))
    distance = attrib(converter=float, validator=validate_range(0, float('inf')),
                      default=1.0)


@attrs(slots=True)
class CartesianPosition(Position, CartesianPositionMixin):
    """A 3D position represented in ADM-format Cartesian coordinates.

    Attributes:
        X (float): left-to-right position, from -1 to 1
        Y (float): back-to-front position, from -1 to 1
        Z (float): bottom-to-top position, from -1 to 1
    """

    X = attrib(converter=float)
    Y = attrib(converter=float)
    Z = attrib(converter=float)


@attrs(slots=True, frozen=True)
class CartesianScreen(object):
    """ADM screen representation using Cartesian coordinates.

    This is used to represent the audioProgrammeReferenceScreen, as well as the
    screen position in the reproduction room.

    Attributes:
        aspectRatio (float): aspect ratio
        centrePosition (CartesianPosition): screenCentrePosition element
        widthX (float): screenWidth X attribute
    """
    aspectRatio = attrib(validator=instance_of(float))
    centrePosition = attrib(validator=instance_of(CartesianPosition))
    widthX = attrib(validator=instance_of(float))


@attrs(slots=True, frozen=True)
class PolarScreen(object):
    """ADM screen representation using Cartesian coordinates.

    This is used to represent the audioProgrammeReferenceScreen, as well as the
    screen position in the reproduction room.

    Attributes:
        aspectRatio (float): aspect ratio
        centrePosition (PolarPosition): screenCentrePosition element
        widthX (float): screenWidth azimuth attribute
    """
    aspectRatio = attrib(validator=instance_of(float))
    centrePosition = attrib(validator=instance_of(PolarPosition))
    widthAzimuth = attrib(validator=instance_of(float))


default_screen = PolarScreen(aspectRatio=1.78,
                             centrePosition=PolarPosition(
                                 azimuth=0.0,
                                 elevation=0.0,
                                 distance=1.0),
                             widthAzimuth=58.0)
"""The default screen position, size and shape."""
