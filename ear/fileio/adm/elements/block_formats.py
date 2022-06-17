from attr import attrs, attrib, Factory, validate
from attr.validators import instance_of, optional
from fractions import Fraction
from ....common import list_of
from .geom import convert_object_position, DirectSpeakerPosition, ObjectPosition
from .main_elements import AudioChannelFormat, TypeDefinition


@attrs(slots=True)
class AudioBlockFormat(object):
    """ADM audioBlockFormat base class

    Attributes:
        id (Optional[str])
        rtime (Optional[fractions.Fraction])
        duration (Optional[fractions.Fraction])
    """

    id = attrib(default=None)
    rtime = attrib(validator=optional(instance_of(Fraction)), default=None)
    duration = attrib(validator=optional(instance_of(Fraction)), default=None)

    def lazy_lookup_references(self, adm):
        pass

    def validate(self):
        validate(self)

        if not (
            (self.rtime is None and self.duration is None)
            or (self.rtime is not None and self.duration is not None)
        ):
            raise ValueError("rtime and duration must be used together")


BlockFormat = AudioBlockFormat
"""Compatibility alias for AudioBlockFormat"""


@attrs(slots=True)
class MatrixCoefficient(object):
    """ADM audioBlockFormat Matrix coefficient element

    Attributes:
        inputChannelFormat (Optional[AudioChannelFormat])
        gain (Optional[float])
        gainVar (Optional[str])
        phase (Optional[float])
        phaseVar (Optional[str])
        delay (Optional[float])
        delayVar (Optional[str])
    """

    inputChannelFormat = attrib(default=None, validator=optional(instance_of(AudioChannelFormat)))

    gain = attrib(default=None, validator=optional(instance_of(float)))
    gainVar = attrib(default=None, validator=optional(instance_of(str)))
    phase = attrib(default=None, validator=optional(instance_of(float)))
    phaseVar = attrib(default=None, validator=optional(instance_of(str)))
    delay = attrib(default=None, validator=optional(instance_of(float)))
    delayVar = attrib(default=None, validator=optional(instance_of(str)))

    inputChannelFormatIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        if self.inputChannelFormatIDRef is not None:
            self.inputChannelFormat = adm.lookup_element(self.inputChannelFormatIDRef)
            self.inputChannelFormatIDRef = None

    def validate(self):
        validate(self)
        if self.inputChannelFormat is None:
            raise ValueError("MatrixCoefficient must have an inputChannelFormat attribute")


@attrs(slots=True)
class AudioBlockFormatMatrix(AudioBlockFormat):
    """ADM audioBlockFormat with typeDefinition == "Matrix"

    Attributes:
        outputChannelFormat (Optional[AudioChannelFormat])
        matrix (list[MatrixCoefficient])
    """

    outputChannelFormat = attrib(default=None, validator=optional(instance_of(AudioChannelFormat)))
    matrix = attrib(default=Factory(list), validator=list_of(MatrixCoefficient))

    outputChannelFormatIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        if self.outputChannelFormatIDRef is not None:
            self.outputChannelFormat = adm.lookup_element(self.outputChannelFormatIDRef)
            self.outputChannelFormatIDRef = None

        for coefficient in self.matrix:
            coefficient.lazy_lookup_references(adm)

    def validate(self):
        super(AudioBlockFormatMatrix, self).validate()
        for coefficient in self.matrix:
            coefficient.validate()


@attrs(slots=True)
class ChannelLock(object):
    """ADM channelLock element

    Attributes:
        maxDistance (Optional[float])
    """

    maxDistance = attrib(default=None, validator=optional(instance_of(float)))


@attrs(slots=True)
class ObjectDivergence(object):
    """ADM objectDivergence element

    Attributes:
        value (float)
        azimuthRange (Optional[float])
        positionRange (Optional[float])
    """

    value = attrib(validator=instance_of(float))
    azimuthRange = attrib(default=None, validator=optional(instance_of(float)))
    positionRange = attrib(default=None, validator=optional(instance_of(float)))


@attrs(slots=True)
class JumpPosition(object):
    """ADM jumpPosition element

    Attributes:
        flag (bool): contents of the jumpPosition element
        interpolationLength (Optional[fractions.Fraction])
    """

    flag = attrib(default=False, validator=instance_of(bool))
    interpolationLength = attrib(default=None, validator=optional(instance_of(Fraction)))


@attrs(slots=True)
class CartesianZone(object):
    """ADM zoneExclusion zone element with Cartesian coordinates

    Attributes:
        minX (float)
        minY (float)
        minZ (float)
        maxX (float)
        maxY (float)
        maxZ (float)
    """

    minX = attrib(validator=instance_of(float))
    minY = attrib(validator=instance_of(float))
    minZ = attrib(validator=instance_of(float))
    maxX = attrib(validator=instance_of(float))
    maxY = attrib(validator=instance_of(float))
    maxZ = attrib(validator=instance_of(float))


@attrs(slots=True)
class PolarZone(object):
    """ADM zoneExclusion zone element with polar coordinates

    Attributes:
        minElevation (float)
        maxElevation (float)
        minAzimuth (float)
        maxAzimuth (float)
    """

    minElevation = attrib(validator=instance_of(float))
    maxElevation = attrib(validator=instance_of(float))
    minAzimuth = attrib(validator=instance_of(float))
    maxAzimuth = attrib(validator=instance_of(float))


@attrs(slots=True)
class AudioBlockFormatObjects(AudioBlockFormat):
    """ADM audioBlockFormat with typeDefinition == "Objects"

    Attributes:
        position (Optional[ObjectPosition])
        cartesian (bool)
        width (float)
        height (float)
        depth (float)
        gain (float)
        diffuse (float)
        channelLock (Optional[ChannelLock])
        objectDivergence (Optional[ObjectDivergence])
        jumpPosition (JumpPosition)
        screenRef (bool)
        importance (int)
        zoneExclusion (list[Union[CartesianZone, PolarZone]])
    """

    position = attrib(default=None, validator=instance_of(ObjectPosition), converter=convert_object_position)
    cartesian = attrib(converter=bool, default=False)
    width = attrib(converter=float, default=0.)
    height = attrib(converter=float, default=0.)
    depth = attrib(converter=float, default=0.)
    gain = attrib(converter=float, default=1.)
    diffuse = attrib(converter=float, default=0.)
    channelLock = attrib(default=None, validator=optional(instance_of(ChannelLock)))
    objectDivergence = attrib(default=None, validator=optional(instance_of(ObjectDivergence)))
    jumpPosition = attrib(default=Factory(JumpPosition))
    screenRef = attrib(converter=bool, default=False)
    importance = attrib(default=10, validator=instance_of(int))
    zoneExclusion = attrib(default=Factory(list), validator=list_of((CartesianZone, PolarZone)))


@attrs(slots=True)
class AudioBlockFormatDirectSpeakers(AudioBlockFormat):
    """ADM audioBlockFormat with typeDefinition == "DirectSpeakers"

    Attributes:
        position (DirectSpeakerPosition)
        speakerLabel (list[str])
    """

    position = attrib(default=None, validator=instance_of(DirectSpeakerPosition))
    speakerLabel = attrib(default=Factory(list))


@attrs(slots=True)
class AudioBlockFormatHoa(AudioBlockFormat):
    """ADM audioBlockFormat with typeDefinition == "HOA"

    Attributes:
        equation (Optional[str])
        order (Optional[int])
        degree (Optional[int])
        normalization (Optional[str])
        nfcRefDist (Optional[float])
        screenRef (Optional[bool])
    """

    equation = attrib(default=None, validator=optional(instance_of(str)))
    order = attrib(default=None, validator=optional(instance_of(int)))
    degree = attrib(default=None, validator=optional(instance_of(int)))
    normalization = attrib(default=None, validator=optional(instance_of(str)))
    nfcRefDist = attrib(default=None, validator=optional(instance_of(float)))
    screenRef = attrib(default=None, validator=optional(instance_of(bool)))


@attrs(slots=True)
class AudioBlockFormatBinaural(AudioBlockFormat):
    pass


by_type_definition = {
    TypeDefinition.DirectSpeakers: AudioBlockFormatDirectSpeakers,
    TypeDefinition.Matrix: AudioBlockFormatMatrix,
    TypeDefinition.Objects: AudioBlockFormatObjects,
    TypeDefinition.HOA: AudioBlockFormatHoa,
    TypeDefinition.Binaural: AudioBlockFormatBinaural,
}
