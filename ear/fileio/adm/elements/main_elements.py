from attr import attrs, attrib, Factory, validate
from attr.validators import instance_of, optional
from enum import Enum
from fractions import Fraction
from six import string_types

from ....common import CartesianScreen, PolarScreen, default_screen, list_of


def _lookup_elements(adm, idRefs):
    """Lookup multiple ID references"""
    return [adm.lookup_element(key) for key in idRefs]


class TypeDefinition(Enum):
    DirectSpeakers = 1
    Matrix = 2
    Objects = 3
    HOA = 4
    Binaural = 5


class FormatDefinition(Enum):
    PCM = 1


@attrs(slots=True)
class ADMElement(object):
    id = attrib(default=None)
    is_common_definition = attrib(default=False, validator=instance_of(bool))

    @property
    def element_type(self):
        return type(self).__name__

    def validate(self):
        validate(self)


@attrs(slots=True)
class AudioProgramme(ADMElement):
    audioProgrammeName = attrib(default=None, validator=instance_of(string_types))
    audioProgrammeLanguage = attrib(default=None)
    start = attrib(default=None)
    end = attrib(default=None)
    maxDuckingDepth = attrib(default=None)
    audioContents = attrib(default=Factory(list), repr=False)

    audioContentIDRef = attrib(default=Factory(list))

    referenceScreen = attrib(validator=optional(instance_of((CartesianScreen, PolarScreen))),
                             default=default_screen)

    def lazy_lookup_references(self, adm):
        if self.audioContentIDRef is not None:
            self.audioContents = _lookup_elements(adm, self.audioContentIDRef)
            self.audioContentIDRef = None


@attrs(slots=True)
class AudioContent(ADMElement):
    audioContentName = attrib(default=None, validator=instance_of(string_types))
    audioContentLanguage = attrib(default=None)
    loudnessMetadata = attrib(default=None)
    dialogue = attrib(default=None)
    audioObjects = attrib(default=Factory(list), repr=False)

    audioObjectIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        if self.audioObjectIDRef is not None:
            self.audioObjects = _lookup_elements(adm, self.audioObjectIDRef)
            self.audioObjectIDRef = None


@attrs(slots=True)
class AudioObject(ADMElement):
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
            self.audioTrackUIDs = _lookup_elements(adm, self.audioTrackUIDRef)
            self.audioTrackUIDRef = None
        if self.audioObjectIDRef is not None:
            self.audioObjects = _lookup_elements(adm, self.audioObjectIDRef)
            self.audioObjectIDRef = None
        if self.audioComplementaryObjectIDRef is not None:
            self.audioComplementaryObjects = _lookup_elements(adm, self.audioComplementaryObjectIDRef)
            self.audioComplementaryObjectIDRef = None


@attrs(slots=True)
class AudioPackFormat(ADMElement):
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
    lowPass = attrib(default=None, validator=optional(instance_of(float)))
    highPass = attrib(default=None, validator=optional(instance_of(float)))


@attrs(slots=True)
class AudioChannelFormat(ADMElement):
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
    audioStreamFormatName = attrib(default=None, validator=instance_of(string_types))

    format = attrib(default=None, validator=instance_of(FormatDefinition))

    audioTrackFormats = attrib(default=Factory(list), repr=False)
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
            self.audioTrackFormats = _lookup_elements(adm, self.audioTrackFormatIDRef)
            self.audioTrackFormatIDRef = None

    def validate(self):
        super(AudioStreamFormat, self).validate()
        if not self.audioTrackFormats:
            raise ValueError("AudioStreamFormat must reference at least one AudioTrackFormat")


@attrs(slots=True)
class AudioTrackFormat(ADMElement):
    audioTrackFormatName = attrib(default=None, validator=instance_of(string_types))
    format = attrib(default=None, validator=instance_of(FormatDefinition))

    audioStreamFormatIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        # check that there is a reference from the referenced stream format
        # back to ourselves
        if self.audioStreamFormatIDRef is not None:
            stream = adm.lookup_element(self.audioStreamFormatIDRef)

            # cannot use 'in', as we want to check identity, not equality
            if not any(track_format is self for track_format in stream.audioTrackFormats):
                raise Exception("track format {id} references stream format {ref} that does not reference it back.".format(
                    id=self.id, ref=self.audioStreamFormatIDRef))
            self.audioStreamFormatIDRef = None


@attrs(slots=True)
class AudioTrackUID(ADMElement):
    trackIndex = attrib(default=None)
    sampleRate = attrib(default=None)
    bitDepth = attrib(default=None)
    audioTrackFormat = attrib(default=None, repr=False)
    audioPackFormat = attrib(default=None, repr=False)

    audioTrackFormatIDRef = attrib(default=None)
    audioPackFormatIDRef = attrib(default=None)

    def lazy_lookup_references(self, adm):
        if self.audioTrackFormatIDRef is not None:
            self.audioTrackFormat = adm.lookup_element(self.audioTrackFormatIDRef)
            self.audioTrackFormatIDRef = None
        if self.audioPackFormatIDRef is not None:
            self.audioPackFormat = adm.lookup_element(self.audioPackFormatIDRef)
            self.audioPackFormatIDRef = None

    def validate(self):
        super(AudioTrackUID, self).validate()
        if self.audioTrackFormat is None:
            raise ValueError("AudioTrackUID must have an audioTrackFormat attribute")
