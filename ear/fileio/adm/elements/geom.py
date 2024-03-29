from attr import attrs, attrib, evolve, Factory
from attr.validators import instance_of, optional
from ....common import (
    PolarPositionMixin,
    CartesianPositionMixin,
    PolarPosition,
    CartesianPosition,
    cart,
    finite_float,
    validate_range,
)

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

    value = attrib(validator=finite_float())
    min = attrib(validator=optional(finite_float()), default=None)
    max = attrib(validator=optional(finite_float()), default=None)


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


class PositionOffset:
    """representation of positionOffset elements in audioObject or alternativeValueSet"""

    __slots__ = ()


@attrs(slots=True)
class PolarPositionOffset(PositionOffset):
    """representation of a polar positionOffset"""

    azimuth = attrib(default=0.0, validator=finite_float())
    elevation = attrib(default=0.0, validator=finite_float())
    distance = attrib(default=0.0, validator=finite_float())

    def apply(self, pos):
        if not isinstance(pos, ObjectPolarPosition):
            raise ValueError(
                "can only apply a polar position offset to a polar position"
            )
        return evolve(
            pos,
            azimuth=pos.azimuth + self.azimuth,
            elevation=pos.elevation + self.elevation,
            distance=pos.distance + self.distance,
        )


@attrs(slots=True)
class CartesianPositionOffset(PositionOffset):
    """representation of a cartesian positionOffset"""

    X = attrib(default=0.0, validator=finite_float())
    Y = attrib(default=0.0, validator=finite_float())
    Z = attrib(default=0.0, validator=finite_float())

    def apply(self, pos):
        if not isinstance(pos, ObjectCartesianPosition):
            raise ValueError(
                "can only apply a cartesian position offset to a cartesian position"
            )
        return evolve(
            pos,
            X=pos.X + self.X,
            Y=pos.Y + self.Y,
            Z=pos.Z + self.Z,
        )


@attrs(slots=True)
class InteractionRange(object):
    """a minimum and maximum bound for a single number

    Attributes:
        min (Optional[float]): lower bound
        max (Optional[float]): upper bound
    """

    min = attrib(validator=optional(finite_float()), default=None)
    max = attrib(validator=optional(finite_float()), default=None)


class PositionInteractionRange:
    """representation of a set of positionInteractionRange elements, for either
    Cartesian or polar coordinates
    """

    __slots__ = ()


@attrs(slots=True)
class PolarPositionInteractionRange(PositionInteractionRange):
    """polar positionInteractionRange elements

    Attributes:
        azimuth (InteractionRange): upper and lower bound for azimuth
        elevation (InteractionRange): upper and lower bound for elevation
        distance (InteractionRange): upper and lower bound for distance
    """

    azimuth = attrib(
        validator=instance_of(InteractionRange), default=Factory(InteractionRange)
    )
    elevation = attrib(
        validator=instance_of(InteractionRange), default=Factory(InteractionRange)
    )
    distance = attrib(
        validator=instance_of(InteractionRange), default=Factory(InteractionRange)
    )


@attrs(slots=True)
class CartesianPositionInteractionRange(PositionInteractionRange):
    """Cartesian positionInteractionRange elements

    Attributes:
        X (InteractionRange): upper and lower bound for X
        Y (InteractionRange): upper and lower bound for Y
        Z (InteractionRange): upper and lower bound for Z
    """

    X = attrib(
        validator=instance_of(InteractionRange), default=Factory(InteractionRange)
    )
    Y = attrib(
        validator=instance_of(InteractionRange), default=Factory(InteractionRange)
    )
    Z = attrib(
        validator=instance_of(InteractionRange), default=Factory(InteractionRange)
    )
