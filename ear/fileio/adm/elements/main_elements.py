from attr import attrs, attrib, Factory
from attr.validators import instance_of, optional
from enum import Enum
from fractions import Fraction
from six import string_types

from ....common import CartesianScreen, PolarScreen, default_screen


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
    adm_parent = attrib(default=None)
    is_common_definition = attrib(default=False, validator=instance_of(bool))

    @property
    def element_type(self):
        return type(self).__name__

    def _lookup_elements(self, idRefs):
        return [self.adm_parent.lookup_element(key) for key in idRefs]

    def _lookup_element(self, idRef):
        if idRef is None: return None
        return self.adm_parent.lookup_element(idRef)


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

    def lazy_lookup_references(self):
        if self.audioContentIDRef is not None:
            self.audioContents = self._lookup_elements(self.audioContentIDRef)
            self.audioContentIDRef = None


@attrs(slots=True)
class AudioContent(ADMElement):
    audioContentName = attrib(default=None, validator=instance_of(string_types))
    audioContentLanguage = attrib(default=None)
    loudnessMetadata = attrib(default=None)
    dialogue = attrib(default=None)
    audioObjects = attrib(default=Factory(list), repr=False)

    audioObjectIDRef = attrib(default=None)

    def lazy_lookup_references(self):
        if self.audioObjectIDRef is not None:
            self.audioObjects = self._lookup_elements(self.audioObjectIDRef)
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

    def lazy_lookup_references(self):
        if self.audioPackFormatIDRef is not None:
            self.audioPackFormats = self._lookup_elements(self.audioPackFormatIDRef)
            self.audioPackFormatIDRef = None
        if self.audioTrackUIDRef is not None:
            self.audioTrackUIDs = self._lookup_elements(self.audioTrackUIDRef)
            self.audioTrackUIDRef = None
        if self.audioObjectIDRef is not None:
            self.audioObjects = self._lookup_elements(self.audioObjectIDRef)
            self.audioObjectIDRef = None
        if self.audioComplementaryObjectIDRef is not None:
            self.audioComplementaryObjects = self._lookup_elements(self.audioComplementaryObjectIDRef)
            self.audioComplementaryObjectIDRef = None


@attrs(slots=True)
class AudioPackFormat(ADMElement):
    audioPackFormatName = attrib(default=None, validator=instance_of(string_types))
    type = attrib(default=None, validator=instance_of(TypeDefinition))
    absoluteDistance = attrib(default=None)
    audioChannelFormats = attrib(default=Factory(list), repr=False)
    audioPackFormats = attrib(default=Factory(list), repr=False)
    importance = attrib(default=None, validator=optional(instance_of(int)))

    audioChannelFormatIDRef = attrib(default=None)
    audioPackFormatIDRef = attrib(default=None)

    def lazy_lookup_references(self):
        if self.audioChannelFormatIDRef is not None:
            self.audioChannelFormats = self._lookup_elements(self.audioChannelFormatIDRef)
            self.audioChannelFormatIDRef = None
        if self.audioPackFormatIDRef is not None:
            self.audioPackFormats = self._lookup_elements(self.audioPackFormatIDRef)
            self.audioPackFormatIDRef = None


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

    def lazy_lookup_references(self):
        pass


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

    def lazy_lookup_references(self):
        if self.audioChannelFormatIDRef is not None:
            self.audioChannelFormat = self._lookup_element(self.audioChannelFormatIDRef)
            self.audioChannelFormatIDRef = None
        if self.audioPackFormatIDRef is not None:
            self.audioPackFormat = self._lookup_element(self.audioPackFormatIDRef)
            self.audioPackFormatIDRef = None
        if self.audioTrackFormatIDRef is not None:
            self.audioTrackFormats = self._lookup_elements(self.audioTrackFormatIDRef)
            self.audioTrackFormatIDRef = None


@attrs(slots=True)
class AudioTrackFormat(ADMElement):
    audioTrackFormatName = attrib(default=None, validator=instance_of(string_types))
    format = attrib(default=None, validator=instance_of(FormatDefinition))

    audioStreamFormatIDRef = attrib(default=None)

    def lazy_lookup_references(self):
        # check that there is a reference from the referenced stream format
        # back to ourselves
        if self.audioStreamFormatIDRef is not None:
            stream = self._lookup_element(self.audioStreamFormatIDRef)

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

    def lazy_lookup_references(self):
        if self.audioTrackFormatIDRef is not None:
            self.audioTrackFormat = self._lookup_element(self.audioTrackFormatIDRef)
            self.audioTrackFormatIDRef = None
        if self.audioPackFormatIDRef is not None:
            self.audioPackFormat = self._lookup_element(self.audioPackFormatIDRef)
            self.audioPackFormatIDRef = None
