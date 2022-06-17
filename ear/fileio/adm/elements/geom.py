from attr import attrs, attrib, Factory
from attr.validators import instance_of, optional
from ....common import PolarPositionMixin, CartesianPositionMixin, PolarPosition, CartesianPosition, cart, validate_range

try:
    # moved in py3.3
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping


def convert_object_position(value):
    if isinstance(value, (ObjectPolarPosition, ObjectCartesianPosition)):
        return value
    elif isinstance(value, PolarPosition):
        return ObjectPolarPosition.from_PolarPosition(value)
    elif isinstance(value, CartesianPosition):
        return ObjectCartesianPosition.from_CartesianPosition(value)
    elif isinstance(value, Mapping):
        if 'azimuth' in value:
            return ObjectPolarPosition(**value)
        else:
            return ObjectCartesianPosition(**value)
    else:
        raise TypeError("cannot convert {value!r} to ObjectPolarPosition or ObjectCartesianPosition".format(value=value))


@attrs(slots=True)
class ScreenEdgeLock(object):
    """ADM screenEdgeLock information from position elements

    Attributes:
        horizontal (Optional[str]): screenEdgeLock from azimuth or X
            coordinates; must be ``left`` or ``right``.
        vertical (Optional[str]): screenEdgeLock from elevation or Z
            coordinates; must be ``top`` or ``bottom``.
    """

    horizontal = attrib(default=None)
    vertical = attrib(default=None)


class ObjectPosition(object):
    """Base for classes representing data contained in `audioBlockFormat`
    `position` elements for Objects.

    See Also:
        :class:`ObjectPolarPosition` and :class:`ObjectCartesianPosition`
    """

    __slots__ = ()


@attrs(slots=True)
class ObjectPolarPosition(ObjectPosition, PolarPositionMixin):
    """Represents data contained in `audioBlockFormat` `position` elements for
    Objects where polar coordinates are used.

    Attributes are formatted according to the ADM coordinate convention.

    Attributes:
        azimuth (float): anti-clockwise azimuth in degrees, measured from the
            front
        elevation (float): elevation in degrees, measured upwards from the
            equator
        distance (float): distance relative to the audioPackFormat
            absoluteDistance parameter
        screenEdgeLock (ScreenEdgeLock)
    """

    azimuth = attrib(converter=float, validator=validate_range(-180, 180))
    elevation = attrib(converter=float, validator=validate_range(-90, 90))
    distance = attrib(converter=float, validator=validate_range(0, float('inf')),
                      default=1.0)
    screenEdgeLock = attrib(default=Factory(ScreenEdgeLock), validator=instance_of(ScreenEdgeLock))

    @classmethod
    def from_PolarPosition(cls, position):
        return cls(azimuth=position.azimuth, elevation=position.elevation, distance=position.distance)


@attrs(slots=True)
class ObjectCartesianPosition(ObjectPosition, CartesianPositionMixin):
    """Represents data contained in `audioBlockFormat` `position` elements for
    Objects where Cartesian coordinates are used.

    Attributes are formatted according to the ADM coordinate convention.

    Attributes:
        X (float): left-to-right position, from -1 to 1
        Y (float): back-to-front position, from -1 to 1
        Z (float): bottom-to-top position, from -1 to 1
        screenEdgeLock (ScreenEdgeLock)
    """

    X = attrib(converter=float)
    Y = attrib(converter=float)
    Z = attrib(converter=float)
    screenEdgeLock = attrib(default=Factory(ScreenEdgeLock), validator=instance_of(ScreenEdgeLock))

    @classmethod
    def from_CartesianPosition(cls, position):
        return cls(X=position.X, Y=position.Y, Z=position.Z)


@attrs(slots=True)
class BoundCoordinate(object):
    """ADM position coordinate for DirectSpeakers

    This represents multiple position elements with the same coordinate, so for
    azimuth this translates to:

    .. code-block:: xml

        <position coordinate="azimuth">{value}</position>
        <position coordinate="azimuth" bound="min">{min}</position>
        <position coordinate="azimuth" bound="max">{max}</position>

    Attributes are formatted according to the ADM coordinate convention.

    Attributes:
        value (float): value for unbounded position element
        min (Optional[float]): value for position element with ``bound="min"``
        max (Optional[float]): value for position element with ``bound="max"``
    """

    value = attrib(validator=instance_of(float))
    min = attrib(validator=optional(instance_of(float)), default=None)
    max = attrib(validator=optional(instance_of(float)), default=None)


class DirectSpeakerPosition(object):
    """Base for classes representing data contained in `audioBlockFormat`
    `position` elements for DirectSpeakers.

    See Also:
        :class:`DirectSpeakerPolarPosition` and
        :class:`DirectSpeakerCartesianPosition`
    """
    __slots__ = ()


@attrs(slots=True)
class DirectSpeakerPolarPosition(DirectSpeakerPosition, PolarPositionMixin):
    """Represents data contained in `audioBlockFormat` `position` elements for
    DirectSpeakers where polar coordinates are used.

    Attributes are formatted according to the ADM coordinate convention.

    Attributes:
        bounded_azimuth (BoundCoordinate): data for position elements with
            ``coordinate="azimuth"``
        bounded_elevation (BoundCoordinate): data for position elements with
            ``coordinate="elevation"``
        bounded_distance (BoundCoordinate): data for position elements with
            ``coordinate="distance"``
        screenEdgeLock (ScreenEdgeLock)
    """

    bounded_azimuth = attrib(validator=instance_of(BoundCoordinate))
    bounded_elevation = attrib(validator=instance_of(BoundCoordinate))
    bounded_distance = attrib(validator=instance_of(BoundCoordinate),
                              default=Factory(lambda: BoundCoordinate(1.)))
    screenEdgeLock = attrib(default=Factory(ScreenEdgeLock), validator=instance_of(ScreenEdgeLock))

    @property
    def azimuth(self):
        """float: anti-clockwise azimuth in degrees, measured from the front"""
        return self.bounded_azimuth.value

    @property
    def elevation(self):
        """float: elevation in degrees, measured upwards from the equator"""
        return self.bounded_elevation.value

    @property
    def distance(self):
        """float: distance relative to the audioPackFormat absoluteDistance
        parameter"""
        return self.bounded_distance.value

    def as_cartesian_array(self):
        return cart(self.azimuth, self.elevation, self.distance)


@attrs(slots=True)
class DirectSpeakerCartesianPosition(DirectSpeakerPosition, CartesianPositionMixin):
    """Represents data contained in `audioBlockFormat` `position` elements for
    DirectSpeakers where Cartesian coordinates are used.

    Attributes:
        bounded_X (BoundCoordinate): data for position elements with
            ``coordinate="X"``
        bounded_Y (BoundCoordinate): data for position elements with
            ``coordinate="Y"``
        bounded_Z (BoundCoordinate): data for position elements with
            ``coordinate="Z"``
        screenEdgeLock (ScreenEdgeLock)
    """

    bounded_X = attrib(validator=instance_of(BoundCoordinate))
    bounded_Y = attrib(validator=instance_of(BoundCoordinate))
    bounded_Z = attrib(validator=instance_of(BoundCoordinate))
    screenEdgeLock = attrib(default=Factory(ScreenEdgeLock), validator=instance_of(ScreenEdgeLock))

    @property
    def X(self):
        """float: left-to-right position, from -1 to 1"""
        return self.bounded_X.value

    @property
    def Y(self):
        """float: back-to-front position, from -1 to 1"""
        return self.bounded_Y.value

    @property
    def Z(self):
        """float: bottom-to-top position, from -1 to 1"""
        return self.bounded_Z.value
