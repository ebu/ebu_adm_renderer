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
    horizontal = attrib(default=None)
    vertical = attrib(default=None)


class ObjectPosition(object):
    """Base for classes representing data contained in `audioBlockFormat`
    `position` elements for Objects."""
    __slots__ = ()


@attrs(slots=True)
class ObjectPolarPosition(ObjectPosition, PolarPositionMixin):
    """Represents data contained in `audioBlockFormat` `position` elements for
    Objects where polar coordinates are used."""
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
    Objects where Cartesian coordinates are used."""
    X = attrib(converter=float)
    Y = attrib(converter=float)
    Z = attrib(converter=float)
    screenEdgeLock = attrib(default=Factory(ScreenEdgeLock), validator=instance_of(ScreenEdgeLock))

    @classmethod
    def from_CartesianPosition(cls, position):
        return cls(X=position.X, Y=position.Y, Z=position.Z)


@attrs(slots=True)
class BoundCoordinate(object):
    value = attrib(validator=instance_of(float))
    min = attrib(validator=optional(instance_of(float)), default=None)
    max = attrib(validator=optional(instance_of(float)), default=None)


class DirectSpeakerPosition(object):
    """Base for classes representing data contained in `audioBlockFormat`
    `position` elements for DirestSpeakers."""
    __slots__ = ()


@attrs(slots=True)
class DirectSpeakerPolarPosition(DirectSpeakerPosition, PolarPositionMixin):
    """Represents data contained in `audioBlockFormat` `position` elements for
    DirectSpeakers where polar coordinates are used."""
    bounded_azimuth = attrib(validator=instance_of(BoundCoordinate))
    bounded_elevation = attrib(validator=instance_of(BoundCoordinate))
    bounded_distance = attrib(validator=instance_of(BoundCoordinate),
                              default=Factory(lambda: BoundCoordinate(1.)))
    screenEdgeLock = attrib(default=Factory(ScreenEdgeLock), validator=instance_of(ScreenEdgeLock))

    @property
    def azimuth(self):
        return self.bounded_azimuth.value

    @property
    def elevation(self):
        return self.bounded_elevation.value

    @property
    def distance(self):
        return self.bounded_distance.value

    def as_cartesian_array(self):
        return cart(self.azimuth, self.elevation, self.distance)


@attrs(slots=True)
class DirectSpeakerCartesianPosition(DirectSpeakerPosition, CartesianPositionMixin):
    """Represents data contained in `audioBlockFormat` `position` elements for
    DirectSpeakers where Cartesian coordinates are used."""
    bounded_X = attrib(validator=instance_of(BoundCoordinate))
    bounded_Y = attrib(validator=instance_of(BoundCoordinate))
    bounded_Z = attrib(validator=instance_of(BoundCoordinate))
    screenEdgeLock = attrib(default=Factory(ScreenEdgeLock), validator=instance_of(ScreenEdgeLock))

    @property
    def X(self):
        return self.bounded_X.value

    @property
    def Y(self):
        return self.bounded_Y.value

    @property
    def Z(self):
        return self.bounded_Z.value
