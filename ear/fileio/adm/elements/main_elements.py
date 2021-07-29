from attr import attrs, attrib, Factory, validate
from attr.validators import instance_of, optional
from enum import Enum
from fractions import Fraction
from six import string_types

from ..exceptions import AdmError
from ....common import CartesianScreen, PolarScreen, default_screen, list_of


def _lookup_elements(adm, idRefs):
    """Lookup multiple ID references"""
    return [adm.lookup_element(key) for key in idRefs]


def _link_track_stream_format(audioTrackFormat, audioStreamFormat):
    """Establish a link between an audioTrackFormat and an audioStreamFormat"""
    if (audioTrackFormat.audioStreamFormat is not None and
            audioTrackFormat.audioStreamFormat is not audioStreamFormat):
        raise AdmError("audioTrackFormat {audioTrackFormat.id} is linked "
                       "to more than one audioStreamFormat".format(audioTrackFormat=audioTrackFormat))

    audioTrackFormat.audioStreamFormat = audioStreamFormat


class TypeDefinition(Enum):
    """ADM type definitions, representing ``typeDefintion`` and ``typeLabel``
    attributes.
    """

    DirectSpeakers = 1
    Matrix = 2
    Objects = 3
    HOA = 4
    Binaural = 5


class FormatDefinition(Enum):
    """ADM format definitions, representing ``formatDefintion`` and
    ``formatLabel`` attributes.
    """

    PCM = 1


@attrs(slots=True)
class LoudnessMetadata(object):
    """ADM loudnessMetadata

    Attributes:
        loudnessMethod (Optional[str])
        loudnessRecType (Optional[str])
        loudnessCorrectionType (Optional[str])
        integratedLoudness (Optional[float])
        loudnessRange (Optional[float])
        maxTruePeak (Optional[float])
        maxMomentary (Optional[float])
        maxShortTerm (Optional[float])
        dialogueLoudness (Optional[float])
    """

    loudnessMethod = attrib(default=None, validator=optional(instance_of(string_types)))
    loudnessRecType = attrib(default=None, validator=optional(instance_of(string_types)))
    loudnessCorrectionType = attrib(default=None, validator=optional(instance_of(string_types)))
    integratedLoudness = attrib(default=None, validator=optional(instance_of(float)))
    loudnessRange = attrib(default=None, validator=optional(instance_of(float)))
    maxTruePeak = attrib(default=None, validator=optional(instance_of(float)))
    maxMomentary = attrib(default=None, validator=optional(instance_of(float)))
    maxShortTerm = attrib(default=None, validator=optional(instance_of(float)))
    dialogueLoudness = attrib(default=None, validator=optional(instance_of(float)))


@attrs(slots=True)
class ADMElement(object):
    """base class for top-level ADM elements

    Attributes:
        id (str): ADM ID attribute (e.g. audioProgrammeID)
        is_common_definition (bool): was this read from the common definitions file?
    """

    id = attrib(default=None)
    is_common_definition = attrib(default=False, validator=instance_of(bool))

    @property
    def element_type(self):
        return type(self).__name__

    def validate(self):
        validate(self)


@attrs(slots=True)
class AudioProgramme(ADMElement):
    """ADM audioProgramme

    Attributes:
        audioProgrammeName (str)
        audioProgrammeLanguage (Optional[str])
        start (Optional[fractions.Fraction])
        end (Optional[fractions.Fraction])
        maxDuckingDepth (Optional[float])
        audioContents (list[AudioContent]): audioContent elements referenced
            via audioContentIDRef
        referenceScreen (Optional[Union[CartesianScreen, PolarScreen]])
        loudnessMetadata (list[LoudnessMetadata])
    """

    audioProgrammeName = attrib(default=None, validator=instance_of(string_types))
    audioProgrammeLanguage = attrib(default=None)
    start = attrib(default=None)
    end = attrib(default=None)
    maxDuckingDepth = attrib(default=None)
    audioContents = attrib(default=Factory(list), repr=False)

    audioContentIDRef = attrib(default=Factory(list))

    referenceScreen = attrib(validator=optional(instance_of((CartesianScreen, PolarScreen))),
                             default=default_screen)
    loudnessMetadata = attrib(default=Factory(list), validator=list_of(LoudnessMetadata))

    def lazy_lookup_references(self, adm):
        if self.audioContentIDRef is not None:
            self.audioContents = _lookup_elements(adm, self.audioContentIDRef)
            self.audioContentIDRef = None


@attrs(slots=True)
class AudioContent(ADMElement):
    """ADM audioContent

    Attributes:
        audioContentName (str)
        audioContentLanguage (Optional[str])
        loudnessMetadata (list[LoudnessMetadata])
        dialogue (Optional[int])
        audioObject (list[AudioObject])
    """

    audioContentName = attrib(default=None, validator=instance_of(string_types))
    audioContentLanguage = attrib(default=None)
    loudnessMetadata = attrib(default=Factory(list), validator=list_of(LoudnessMetadata))
    dialogue = attrib(default=None)
    audioObjects = attrib(default=Factory(list), repr=False)

    audioObjectIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        if self.audioObjectIDRef is not None:
            self.audioObjects = _lookup_elements(adm, self.audioObjectIDRef)
            self.audioObjectIDRef = None


@attrs(slots=True)
class AudioObject(ADMElement):
    """ADM audioObject

    Attributes:
        audioObjectName (str)
        start (Optional[fractions.Fraction])
        duration (Optional[fractions.Fraction])
        importance (Optional[int])
        interact (Optional[bool])
        disableDucking (Optional[bool])
        dialogue (Optional[int])
        audioPackFormats (list[AudioPackFormat])
        audioTrackUIDs (list[AudioTrackUID])
        audioObjects (list[AudioObject])
        audioComplementaryObjects (list[AudioObject])
    """

    audioObjectName = attrib(default=None, validator=instance_of(string_types))
    start = attrib(validator=optional(instance_of(Fraction)), default=None)
    duration = attrib(validator=optional(instance_of(Fraction)), default=None)
    importance = attrib(default=None, validator=optional(instance_of(int)))
    interact = attrib(default=None, validator=optional(instance_of(bool)))
    disableDucking = attrib(default=None, validator=optional(instance_of(bool)))
    dialogue = attrib(default=None, validator=optional(instance_of(int)))
    audioPackFormats = attrib(default=Factory(list), repr=False)
    audioTrackUIDs = attrib(default=Factory(list), repr=False)
    audioObjects = attrib(default=Factory(list), repr=False)
    audioComplementaryObjects = attrib(default=Factory(list), repr=False)

    audioPackFormatIDRef = attrib(default=None)
    audioTrackUIDRef = attrib(default=None)
    audioObjectIDRef = attrib(default=None)
    audioComplementaryObjectIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        if self.audioPackFormatIDRef is not None:
            self.audioPackFormats = _lookup_elements(adm, self.audioPackFormatIDRef)
            self.audioPackFormatIDRef = None
        if self.audioTrackUIDRef is not None:
            self.audioTrackUIDs = [adm[ref] if ref is not None else None
                                   for ref in self.audioTrackUIDRef]
            self.audioTrackUIDRef = None
        if self.audioObjectIDRef is not None:
            self.audioObjects = _lookup_elements(adm, self.audioObjectIDRef)
            self.audioObjectIDRef = None
        if self.audioComplementaryObjectIDRef is not None:
            self.audioComplementaryObjects = _lookup_elements(adm, self.audioComplementaryObjectIDRef)
            self.audioComplementaryObjectIDRef = None


@attrs(slots=True)
class AudioPackFormat(ADMElement):
    """ADM audioPackformat

    Attributes:
        audioPackFormatName (str)
        type (TypeDefinition): ``typeDefintion`` and/or ``typeLabel``
        absoluteDistance (Optional[float])
        audioChannelFormats (list[AudioChannelFormat])
        audioPackFormats (list[AudioPackFormat])
        importance (Optional[int])

        encodePackFormats (list[AudioPackFormat]): Only for type==Matrix.
            Encode and decode pack references are a single binary many-many
            relationship; we only store one side.
        inputPackFormat (Optional[AudioPackFormat]): Only for type==Matrix.
        outputPackFormat (Optional[AudioPackFormat]): Only for type==Matrix.

        normalization (Optional[str]): Only for type==HOA.
        nfcRefDist (Optional[float]): Only for type==HOA.
        screenRef (Optional[bool]): Only for type==HOA.
    """

    audioPackFormatName = attrib(default=None, validator=instance_of(string_types))
    type = attrib(default=None, validator=instance_of(TypeDefinition))
    absoluteDistance = attrib(default=None)
    audioChannelFormats = attrib(default=Factory(list), repr=False)
    audioPackFormats = attrib(default=Factory(list), repr=False)
    importance = attrib(default=None, validator=optional(instance_of(int)))

    # attributes for type==Matrix
    # encode and decode pack references are a single binary many-many
    # relationship; only store one side
    encodePackFormats = attrib(default=Factory(list))
    inputPackFormat = attrib(default=None)
    outputPackFormat = attrib(default=None)

    # attributes for type==HOA
    normalization = attrib(default=None, validator=optional(instance_of(str)))
    nfcRefDist = attrib(default=None, validator=optional(instance_of(float)))
    screenRef = attrib(default=None, validator=optional(instance_of(bool)))

    audioChannelFormatIDRef = attrib(default=None)
    audioPackFormatIDRef = attrib(default=None)
    encodePackFormatIDRef = attrib(default=None)
    decodePackFormatIDRef = attrib(default=None)
    inputPackFormatIDRef = attrib(default=None)
    outputPackFormatIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        if self.audioChannelFormatIDRef is not None:
            self.audioChannelFormats = _lookup_elements(adm, self.audioChannelFormatIDRef)
            self.audioChannelFormatIDRef = None
        if self.audioPackFormatIDRef is not None:
            self.audioPackFormats = _lookup_elements(adm, self.audioPackFormatIDRef)
            self.audioPackFormatIDRef = None

        def add_encodePackFormat(decode_pack, new_encode_pack):
            if not any(encode_pack is new_encode_pack
                       for encode_pack in decode_pack.encodePackFormats):
                decode_pack.encodePackFormats.append(new_encode_pack)

        if self.decodePackFormatIDRef is not None:
            for decode_pack in _lookup_elements(adm, self.decodePackFormatIDRef):
                add_encodePackFormat(decode_pack, self)
            self.decodePackFormatIDRef = None

        if self.encodePackFormatIDRef is not None:
            for encode_pack in _lookup_elements(adm, self.encodePackFormatIDRef):
                add_encodePackFormat(self, encode_pack)
            self.encodePackFormatIDRef = None

        if self.inputPackFormatIDRef is not None:
            self.inputPackFormat = adm.lookup_element(self.inputPackFormatIDRef)
            self.inputPackFormatIDRef = None

        if self.outputPackFormatIDRef is not None:
            self.outputPackFormat = adm.lookup_element(self.outputPackFormatIDRef)
            self.outputPackFormatIDRef = None


@attrs(slots=True)
class Frequency(object):
    """ADM frequency element

    Attributes:
        lowPass (Optional[float])
        highPass (Optional[float])
    """

    lowPass = attrib(default=None, validator=optional(instance_of(float)))
    highPass = attrib(default=None, validator=optional(instance_of(float)))


@attrs(slots=True)
class AudioChannelFormat(ADMElement):
    """ADM audioChannelFormat

    Attributes:
        audioChannelFormatName (str)
        type (TypeDefinition): ``typeDefintion`` and/or ``typeLabel``
        audioBlockFormats (list[AudioBlockFormat])
        frequency (Frequency)
    """

    audioChannelFormatName = attrib(default=None, validator=instance_of(string_types))
    type = attrib(default=None, validator=instance_of(TypeDefinition))
    audioBlockFormats = attrib(default=Factory(list))
    frequency = attrib(default=Factory(Frequency), validator=instance_of(Frequency))

    def lazy_lookup_references(self, adm):
        for block in self.audioBlockFormats:
            block.lazy_lookup_references(adm)

    @audioBlockFormats.validator
    def _validate_audioBlockFormats(self, attr, value):
        from . import block_formats  # can't import at top level without making a loop
        block_type = block_formats.by_type_definition[self.type]
        list_of(block_type)(self, attr, value)

    def validate(self):
        super(AudioChannelFormat, self).validate()
        for block in self.audioBlockFormats:
            block.validate()


@attrs(slots=True)
class AudioStreamFormat(ADMElement):
    """ADM audioStreamFormat

    Attributes:
        audioStreamFormatName (str)
        format (FormatDefinition): ``formatDefintion`` and/or ``formatLabel``
        audioChannelFormat (Optional[AudioStreamFormat])
        audioPackFormat (Optional[AudioPackFormat])
    """

    audioStreamFormatName = attrib(default=None, validator=instance_of(string_types))

    format = attrib(default=None, validator=instance_of(FormatDefinition))

    audioChannelFormat = attrib(default=None, repr=False)
    audioPackFormat = attrib(default=None, repr=False)

    audioTrackFormatIDRef = attrib(default=None)
    audioChannelFormatIDRef = attrib(default=None)
    audioPackFormatIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        if self.audioChannelFormatIDRef is not None:
            self.audioChannelFormat = adm.lookup_element(self.audioChannelFormatIDRef)
            self.audioChannelFormatIDRef = None
        if self.audioPackFormatIDRef is not None:
            self.audioPackFormat = adm.lookup_element(self.audioPackFormatIDRef)
            self.audioPackFormatIDRef = None
        if self.audioTrackFormatIDRef is not None:
            for ref in self.audioTrackFormatIDRef:
                track_format = adm.lookup_element(ref)
                _link_track_stream_format(track_format, self)
            self.audioTrackFormatIDRef = None

    def validate(self):
        super(AudioStreamFormat, self).validate()
        if self.audioPackFormat is not None and self.audioChannelFormat is not None:
            raise AdmError("audioStreamFormat {self.id} has a reference to both an "
                           "audioPackFormat and an audioChannelFormat".format(self=self))

        if self.audioPackFormat is None and self.audioChannelFormat is None:
            raise AdmError("audioStreamFormat {self.id} has no reference to an "
                           "audioPackFormat or audioChannelFormat".format(self=self))


@attrs(slots=True)
class AudioTrackFormat(ADMElement):
    """ADM audioTrackFormat

    Attributes:
        audioTrackFormatName (str)
        format (FormatDefinition): ``formatDefintion`` and/or ``formatLabel``
        audioStreamFormat (Optional[AudioStreamFormat])
    """

    audioTrackFormatName = attrib(default=None, validator=instance_of(string_types))
    format = attrib(default=None, validator=instance_of(FormatDefinition))
    audioStreamFormat = attrib(default=None, validator=optional(instance_of(AudioStreamFormat)))

    audioStreamFormatIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        if self.audioStreamFormatIDRef is not None:
            stream_format = adm.lookup_element(self.audioStreamFormatIDRef)
            _link_track_stream_format(self, stream_format)
            self.audioStreamFormatIDRef = None

    def validate(self):
        super(AudioTrackFormat, self).validate()
        if self.audioStreamFormat is None:
            raise AdmError("audioTrackFormat {self.id} is not linked "
                           "to an audioStreamFormat".format(self=self))


@attrs(slots=True)
class AudioTrackUID(ADMElement):
    """ADM audioTrackUID

    Attributes:
        trackIndex (Optional[int]): 1-based track index from CHNA chunk
        sampleRate (Optional[int])
        bitDepth (Optional[int])
        audioTrackFormat (Optional[AudioTrackFormat])
        audioPackFormat (Optional[AudioPackFormat])
    """

    trackIndex = attrib(default=None)
    sampleRate = attrib(default=None)
    bitDepth = attrib(default=None)
    audioTrackFormat = attrib(default=None, repr=False,
                              validator=optional(instance_of(AudioTrackFormat)))
    audioPackFormat = attrib(default=None, repr=False,
                             validator=optional(instance_of(AudioPackFormat)))

    audioTrackFormatIDRef = attrib(default=None)
    audioPackFormatIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        if self.audioTrackFormatIDRef is not None:
            self.audioTrackFormat = adm.lookup_element(self.audioTrackFormatIDRef)
            self.audioTrackFormatIDRef = None
        if self.audioPackFormatIDRef is not None:
            self.audioPackFormat = adm.lookup_element(self.audioPackFormatIDRef)
            self.audioPackFormatIDRef = None
