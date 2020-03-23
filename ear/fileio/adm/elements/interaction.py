from attr import attrs, attrib, Factory
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
    onOffInteract = attrib(validator=instance_of(bool))
    gainInteract = attrib(default=False, validator=optional(instance_of(bool)))
    positionInteract = attrib(default=False, validator=optional(instance_of(bool)))
    gainInteractionRange = attrib(
        default=Factory(GainInteractionRange),
        validator=instance_of(GainInteractionRange),
    )
    positionInteractionRange = attrib(
        default=Factory(PositionInteractionRange),
        validator=instance_of(PositionInteractionRange),
    )
