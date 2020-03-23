from attr import attrs, attrib
from attr.validators import instance_of, optional


@attrs(slots=True)
class PositionInteractionRange(object):
    azimuthMin = attrib(default=None, validator=optional(instance_of(float)))
    azimuthMax = attrib(default=None, validator=optional(instance_of(float)))
    elevationMin = attrib(default=None, validator=optional(instance_of(float)))
    elevationMax = attrib(default=None, validator=optional(instance_of(float)))
    distanceMin = attrib(default=None, validator=optional(instance_of(float)))
    distanceMax = attrib(default=None, validator=optional(instance_of(float)))
    XMin = attrib(default=None, validator=optional(instance_of(float)))
    XMax = attrib(default=None, validator=optional(instance_of(float)))
    YMin = attrib(default=None, validator=optional(instance_of(float)))
    YMax = attrib(default=None, validator=optional(instance_of(float)))
    ZMin = attrib(default=None, validator=optional(instance_of(float)))
    ZMax = attrib(default=None, validator=optional(instance_of(float)))


@attrs(slots=True)
class GainInteractionRange(object):
    min = attrib(default=None, validator=optional(instance_of(float)))
    max = attrib(default=None, validator=optional(instance_of(float)))


@attrs(slots=True)
class AudioObjectInteraction(object):
    onOffInteract = attrib(default=None, validator=optional(instance_of(int)))
    gainInteract = attrib(default=None, validator=optional(instance_of(int)))
    positionInteract = attrib(default=None, validator=optional(instance_of(int)))
    gainInteractionRange = attrib(default=None)
    positionInteractionRange = attrib(default=None)
