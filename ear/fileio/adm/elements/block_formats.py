from attr import attrs, attrib, Factory, validate
from attr.validators import instance_of, optional
from fractions import Fraction
from ....common import finite_float, list_of
from .geom import convert_object_position, DirectSpeakerPosition, ObjectPosition
from .main_elements import AudioChannelFormat, TypeDefinition


@attrs(slots=True)
class AudioBlockFormat(object):
    """ADM audioBlockFormat base class

    Attributes:
        id (Optional[str])
        rtime (Optional[fractions.Fraction])
        duration (Optional[fractions.Fraction])
        gain (float)
        importance (int)
    """

    id = attrib(default=None)
    rtime = attrib(validator=optional(instance_of(Fraction)), default=None)
    duration = attrib(validator=optional(instance_of(Fraction)), default=None)
    gain = attrib(validator=finite_float(), default=1.0)
    importance = attrib(default=10, validator=instance_of(int))

    def lazy_lookup_references(self, adm):
        pass

    def validate(self, adm=None, audioChannelFormat=None):
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

    gain = attrib(default=None, validator=optional(finite_float()))
    gainVar = attrib(default=None, validator=optional(instance_of(str)))
    phase = attrib(default=None, validator=optional(finite_float()))
    phaseVar = attrib(default=None, validator=optional(instance_of(str)))
    delay = attrib(default=None, validator=optional(finite_float()))
    delayVar = attrib(default=None, validator=optional(instance_of(str)))

    inputChannelFormatIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        if self.inputChannelFormatIDRef is not None:
            self.inputChannelFormat = adm.lookup_element(self.inputChannelFormatIDRef)
            self.inputChannelFormatIDRef = None

    def validate(self, adm=None, audioChannelFormat=None, audioBlockFormat=None):
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

    def validate(self, adm=None, audioChannelFormat=None):
        super(AudioBlockFormatMatrix, self).validate(adm=adm, audioChannelFormat=audioChannelFormat)
        for coefficient in self.matrix:
            coefficient.validate(adm=adm, audioChannelFormat=audioChannelFormat, audioBlockFormat=self)


@attrs(slots=True)
class ChannelLock(object):
    """ADM channelLock element

    Attributes:
        maxDistance (Optional[float])
    """

    maxDistance = attrib(default=None, validator=optional(finite_float()))


@attrs(slots=True)
class ObjectDivergence(object):
    """ADM objectDivergence element

    Attributes:
        value (float)
        azimuthRange (Optional[float])
        positionRange (Optional[float])
    """

    value = attrib(validator=finite_float())
    azimuthRange = attrib(default=None, validator=optional(finite_float()))
    positionRange = attrib(default=None, validator=optional(finite_float()))


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

    minX = attrib(validator=finite_float())
    minY = attrib(validator=finite_float())
    minZ = attrib(validator=finite_float())
    maxX = attrib(validator=finite_float())
    maxY = attrib(validator=finite_float())
    maxZ = attrib(validator=finite_float())


@attrs(slots=True)
class PolarZone(object):
    """ADM zoneExclusion zone element with polar coordinates

    Attributes:
        minElevation (float)
        maxElevation (float)
        minAzimuth (float)
        maxAzimuth (float)
    """

    minElevation = attrib(validator=finite_float())
    maxElevation = attrib(validator=finite_float())
    minAzimuth = attrib(validator=finite_float())
    maxAzimuth = attrib(validator=finite_float())


@attrs(slots=True)
class AudioBlockFormatObjects(AudioBlockFormat):
    """ADM audioBlockFormat with typeDefinition == "Objects"

    Attributes:
        position (Optional[ObjectPosition])
        cartesian (bool)
        width (float)
        height (float)
        depth (float)
        diffuse (float)
        channelLock (Optional[ChannelLock])
        objectDivergence (Optional[ObjectDivergence])
        jumpPosition (JumpPosition)
        screenRef (bool)
        zoneExclusion (list[Union[CartesianZone, PolarZone]])
    """

    position = attrib(default=None, validator=instance_of(ObjectPosition), converter=convert_object_position)
    cartesian = attrib(converter=bool, default=False)
    width = attrib(converter=float, default=0.)
    height = attrib(converter=float, default=0.)
    depth = attrib(converter=float, default=0.)
    diffuse = attrib(converter=float, default=0.)
    channelLock = attrib(default=None, validator=optional(instance_of(ChannelLock)))
    objectDivergence = attrib(default=None, validator=optional(instance_of(ObjectDivergence)))
    jumpPosition = attrib(default=Factory(JumpPosition))
    screenRef = attrib(converter=bool, default=False)
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
    nfcRefDist = attrib(default=None, validator=optional(finite_float()))
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
