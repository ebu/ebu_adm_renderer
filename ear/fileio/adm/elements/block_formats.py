from attr import attrs, attrib, Factory
from attr.validators import instance_of, optional
from fractions import Fraction
from ....common import list_of
from .geom import convert_object_position, DirectSpeakerPosition, ObjectPosition


@attrs(slots=True)
class BlockFormat(object):
    id = attrib(default=None)
    rtime = attrib(validator=optional(instance_of(Fraction)), default=None)
    duration = attrib(validator=optional(instance_of(Fraction)), default=None)


@attrs(slots=True)
class AudioBlockFormatMatrix(BlockFormat):
    pass


@attrs(slots=True)
class ChannelLock(object):
    maxDistance = attrib(default=None, validator=optional(instance_of(float)))


@attrs(slots=True)
class ObjectDivergence(object):
    value = attrib(validator=instance_of(float))
    azimuthRange = attrib(default=None, validator=optional(instance_of(float)))
    positionRange = attrib(default=None, validator=optional(instance_of(float)))


@attrs(slots=True)
class JumpPosition(object):
    flag = attrib(default=False, validator=instance_of(bool))
    interpolationLength = attrib(default=None, validator=optional(instance_of(Fraction)))


@attrs(slots=True)
class CartesianZone(object):
    minX = attrib(validator=instance_of(float))
    minY = attrib(validator=instance_of(float))
    minZ = attrib(validator=instance_of(float))
    maxX = attrib(validator=instance_of(float))
    maxY = attrib(validator=instance_of(float))
    maxZ = attrib(validator=instance_of(float))


@attrs(slots=True)
class PolarZone(object):
    minElevation = attrib(validator=instance_of(float))
    maxElevation = attrib(validator=instance_of(float))
    minAzimuth = attrib(validator=instance_of(float))
    maxAzimuth = attrib(validator=instance_of(float))


@attrs(slots=True)
class AudioBlockFormatObjects(BlockFormat):
    position = attrib(default=None, validator=instance_of(ObjectPosition), convert=convert_object_position)
    cartesian = attrib(convert=bool, default=False)
    width = attrib(convert=float, default=0.)
    height = attrib(convert=float, default=0.)
    depth = attrib(convert=float, default=0.)
    gain = attrib(convert=float, default=1.)
    diffuse = attrib(convert=float, default=0.)
    channelLock = attrib(default=None, validator=optional(instance_of(ChannelLock)))
    objectDivergence = attrib(default=None, validator=optional(instance_of(ObjectDivergence)))
    jumpPosition = attrib(default=Factory(JumpPosition))
    screenRef = attrib(convert=bool, default=False)
    importance = attrib(default=10, validator=instance_of(int))
    zoneExclusion = attrib(default=Factory(list), validator=list_of((CartesianZone, PolarZone)))


@attrs(slots=True)
class AudioBlockFormatDirectSpeakers(BlockFormat):
    position = attrib(default=None, validator=instance_of(DirectSpeakerPosition))
    speakerLabel = attrib(default=Factory(list))


@attrs(slots=True)
class AudioBlockFormatHoa(BlockFormat):
    equation = attrib(default=None, validator=optional(instance_of(str)))
    order = attrib(default=None, validator=optional(instance_of(int)))
    degree = attrib(default=None, validator=optional(instance_of(int)))
    normalization = attrib(default="SN3D", validator=instance_of(str))
    nfcRefDist = attrib(default=None, validator=optional(instance_of(float)))
    screenRef = attrib(default=False, validator=instance_of(bool))


@attrs(slots=True)
class AudioBlockFormatBinaural(BlockFormat):
    pass
