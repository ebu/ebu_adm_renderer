from attr import attrs, attrib, Factory
from attr.validators import instance_of, optional


@attrs(slots=True)
class PositionInteractionRange(object):
    minAzimuth = attrib(default=None, validator=optional(instance_of(float)))
    maxAzimuth = attrib(default=None, validator=optional(instance_of(float)))
    minElevation = attrib(default=None, validator=optional(instance_of(float)))
    maxElevation = attrib(default=None, validator=optional(instance_of(float)))
    minDistance = attrib(default=None, validator=optional(instance_of(float)))
    maxDistance = attrib(default=None, validator=optional(instance_of(float)))
    minX = attrib(default=None, validator=optional(instance_of(float)))
    maxX = attrib(default=None, validator=optional(instance_of(float)))
    minY = attrib(default=None, validator=optional(instance_of(float)))
    maxY = attrib(default=None, validator=optional(instance_of(float)))
    minZ = attrib(default=None, validator=optional(instance_of(float)))
    maxZ = attrib(default=None, validator=optional(instance_of(float)))


@attrs(slots=True)
class GainInteractionRange(object):
    min = attrib(default=None, validator=optional(instance_of(float)))
    max = attrib(default=None, validator=optional(instance_of(float)))


@attrs(slots=True)
class AudioObjectInteraction(object):
    onOffInteract = attrib(validator=instance_of(bool))
    gainInteract = attrib(default=None, validator=optional(instance_of(bool)))
    positionInteract = attrib(default=None, validator=optional(instance_of(bool)))
    gainInteractionRange = attrib(
        default=Factory(GainInteractionRange),
        validator=instance_of(GainInteractionRange),
    )
    positionInteractionRange = attrib(
        default=Factory(PositionInteractionRange),
        validator=instance_of(PositionInteractionRange),
    )
