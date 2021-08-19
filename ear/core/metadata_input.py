from attr import attrib, attrs, Factory
from attr.validators import instance_of, optional
from fractions import Fraction
from typing import Optional
from ..common import list_of, default_screen
from ..fileio.adm.elements import (AudioProgramme, AudioContent, AudioObject, AudioPackFormat,
                                   AudioChannelFormat, AudioBlockFormatObjects, AudioBlockFormatDirectSpeakers,
                                   MatrixCoefficient, Frequency)


class MetadataSource(object):
    """A source of metadata for some input channels."""

    def get_next_block(self) -> Optional["TypeMetadata"]:
        """Get the next metadata block, if one is available."""
        raise NotImplementedError()


class MetadataSourceIter(MetadataSource):
    """Metadata source that iterates through a list of TypeMetadata objects.

    Args:
        type_metadatas (list of TypeMetadata): List of metadata to iterate through.
    """

    def __init__(self, type_metadatas):
        self.type_metadatas_iter = iter(type_metadatas)

    def get_next_block(self):
        return next(self.type_metadatas_iter, None)


@attrs(slots=True)
class TypeMetadata(object):
    """Base class for \\*TypeMetadata classes; these should represent all the
    parameters needed to render some set of audio channels within some time
    bounds.
    """


@attrs(slots=True)
class RenderingItem(object):
    """Base class for \\*RenderingItem classes; these should represent an item
    to be rendered, combining a MetadataSource that produces a sequence of
    TypeMetadata objects, and some indices into the tracks that this metadata
    applies to.
    """


@attrs(slots=True)
class ExtraData(object):
    """Common metadata from outside the ADM block format.

    Attributes:
        object_start (fractions.Fraction or None): Start time of audioObject.
        object_duration (fractions.Fraction or None): Duration of audioObject.
        reference_screen (CartesianScreen or PolarScreen): Reference screen from audioProgramme.
        channel_frequency (Frequency): Frequency information from audioChannel.
    """
    object_start = attrib(validator=optional(instance_of(Fraction)), default=None)
    object_duration = attrib(validator=optional(instance_of(Fraction)), default=None)
    reference_screen = attrib(default=default_screen)
    channel_frequency = attrib(validator=instance_of(Frequency), default=Factory(Frequency))


@attrs(slots=True)
class ADMPath(object):
    """Pointers to the ADM objects which a rendering item is derived from.

    Attributes:
        audioProgramme (Optional[AudioProgramme])
        audioContent (Optional[AudioContent])
        audioObjects (Optional[list[AudioObject]])
        audioPackFormats (Optional[list[AudioPackFormat]])
        audioChannelFormat (Optional[list[AudioChannelFormat]])
    """
    audioProgramme = attrib(validator=optional(instance_of(AudioProgramme)), default=None)
    audioContent = attrib(validator=optional(instance_of(AudioContent)), default=None)
    audioObjects = attrib(validator=optional(list_of(AudioObject)), default=None)
    audioPackFormats = attrib(validator=optional(list_of(AudioPackFormat)), default=None)
    audioChannelFormat = attrib(validator=optional(instance_of(AudioChannelFormat)), default=None)

    @property
    def first_audioObject(self):
        """Optional[AudioObject]: The first audioObject of this track in the
        chain, or None"""
        return self.audioObjects[0] if self.audioObjects is not None else None

    @property
    def last_audioObject(self):
        """Optional[AudioObject]: The last audioObject of this track in the
        chain, or None"""
        return self.audioObjects[-1] if self.audioObjects is not None else None

    @property
    def first_audioPackFormat(self):
        """Optional[AudioPackFormat]: The first audioPackFormat of this track
        in the chain, or None"""
        return self.audioPackFormats[0] if self.audioPackFormats is not None else None

    @property
    def last_audioPackFormat(self):
        """Optional[AudioPackFormat]: The last audioPackFormat of this track in
        the chain, or None"""
        return self.audioPackFormats[-1] if self.audioPackFormats is not None else None


@attrs(slots=True)
class ImportanceData(object):
    """Importance metadata for a single channel in a RenderingItem

    Attributes:
        audio_object (int or None): Importance that has been derived from the audioObject level
        audio_pack_format (int or None): Importance that has been derived from the audioPackFormat level
    """
    audio_object = attrib(validator=optional(instance_of(int)), default=None)
    audio_pack_format = attrib(validator=optional(instance_of(int)), default=None)


@attrs(slots=True)
class TrackSpec(object):
    """Represents a method for obtaining audio samples to be processed given
    multi-track input samples (from a WAV file for example).

    This is used to abstract over regular track references, silent channels and
    matrix channels, but could also be used for coded audio, fancy containers etc.
    """


@attrs(slots=True)
class DirectTrackSpec(TrackSpec):
    """Track obtained directly from the input audio stream.

    Attributes:
        track_index (int): Zero based input track index.
    """
    track_index = attrib(validator=instance_of(int))


@attrs(slots=True)
class SilentTrackSpec(TrackSpec):
    """A track whose samples are always 0."""


@attrs(slots=True)
class MatrixCoefficientTrackSpec(TrackSpec):
    """Track derived from a single channel and a matrix coefficient.

    Attributes:
        input_track (TrackSpec): track spec to obtain samples from before they
            are processed by parameters in coefficient.
        coefficient (MatrixCoefficient): matrix parameters to apply;
            inputChannelFormat should be ignored.
    """
    input_track = attrib(validator=instance_of(TrackSpec))
    coefficient = attrib(validator=instance_of(MatrixCoefficient))


@attrs(slots=True)
class MixTrackSpec(TrackSpec):
    """Track that is a mix of some other tracks.

    Attributes:
        input_tracks (list of TrackSpec): list of input tracks to mix
    """
    input_tracks = attrib(validator=list_of(TrackSpec))


#################################################
# type metadata and rendering items for each type
#################################################

# objects

@attrs(slots=True)
class ObjectTypeMetadata(TypeMetadata):
    """TypeMetadata for typeDefinition="Objects"

    Attributes:
        block_format (AudioBlockFormatObjects): Block format.
        extra_data (ExtraData): Extra parameters from outside block format.
    """
    block_format = attrib(validator=instance_of(AudioBlockFormatObjects))

    extra_data = attrib(validator=instance_of(ExtraData), default=Factory(ExtraData))


@attrs(slots=True)
class ObjectRenderingItem(RenderingItem):
    """RenderingItem for typeDefinition="Objects"

    Attributes:
        track_spec (TrackSpec): Zero based input track index for this item.
        metadata_source (MetadataSource): Source of ObjectTypeMetadata objects.
        importance (ImportanceData): Importance data for this item.
        adm_path (ADMPath): Pointers to the ADM objects which this is derived from.
    """
    track_spec = attrib(validator=instance_of(TrackSpec))
    metadata_source = attrib(validator=instance_of(MetadataSource))

    importance = attrib(validator=instance_of(ImportanceData), default=Factory(ImportanceData))
    adm_path = attrib(validator=optional(instance_of(ADMPath)), default=None, repr=False)


# direct speakers

@attrs(slots=True)
class DirectSpeakersTypeMetadata(TypeMetadata):
    """TypeMetadata for typeDefinition="DirectSpeakers"

    Attributes:
        block_format (AudioBlockFormatDirectSpeakers): Block format.
        extra_data (ExtraData): Extra parameters from outside block format.
    """
    block_format = attrib(validator=instance_of(AudioBlockFormatDirectSpeakers))
    audioPackFormats = attrib(validator=optional(list_of(AudioPackFormat)), default=None)

    extra_data = attrib(validator=instance_of(ExtraData), default=Factory(ExtraData))


@attrs(slots=True)
class DirectSpeakersRenderingItem(RenderingItem):
    """RenderingItem for typeDefinition="DirectSpeakers"

    Attributes:
        track_spec (TrackSpec): Specification of input samples.
        metadata_source (MetadataSource): Source of DirectSpeakersTypeMetadata objects.
        importance (ImportanceData): Importance data for this item.
        adm_path (ADMPath): Pointers to the ADM objects which this is derived from.
    """
    track_spec = attrib(validator=instance_of(TrackSpec))
    metadata_source = attrib(validator=instance_of(MetadataSource))

    importance = attrib(validator=instance_of(ImportanceData), default=Factory(ImportanceData))
    adm_path = attrib(validator=optional(instance_of(ADMPath)), default=None, repr=False)


# HOA

@attrs(slots=True)
class HOATypeMetadata(TypeMetadata):
    """TypeMetadata for typeDefinition="HOA"

    Attributes:
        orders (list of int): Order for each input channel.
        degrees (list of int): Degree for each channel.
        normalization (str): Normalization for all channels.
        nfcRefDist (float or None): NFC Reference distance for all channels.
        screenRef (bool): Are these channels screen related?
        rtime (fractions.Fraction or None): Start time of block.
        duration (fractions.Fraction or None): Duration of block.
        extra_data (ExtraData): Info from object and channels for all channels.
    """
    orders = attrib(validator=list_of(int))
    degrees = attrib(validator=list_of(int))
    normalization = attrib()
    nfcRefDist = attrib(validator=optional(instance_of(float)), default=None)
    screenRef = attrib(validator=instance_of(bool), default=False)
    rtime = attrib(default=None, validator=optional(instance_of(Fraction)))
    duration = attrib(default=None, validator=optional(instance_of(Fraction)))

    extra_data = attrib(validator=instance_of(ExtraData), default=Factory(ExtraData))


@attrs(slots=True)
class HOARenderingItem(RenderingItem):
    """RenderingItem for typeDefinition="HOA"

    Attributes:
        track_specs (list[TrackSpec]): Specification of n tracks of input samples.
        metadata_source (MetadataSource): Source of HOATypeMetadata objects;
            will usually contain only one object.
        importances (Optional[list[ImportanceData]]): Importance data for each
            track.
        adm_paths (Optional[list[ADMPath]]): Pointers to the ADM objects which
            each track is derived from.
    """
    track_specs = attrib(validator=list_of(TrackSpec))
    metadata_source = attrib(validator=instance_of(MetadataSource))

    importances = attrib(validator=optional(list_of(ImportanceData)), default=None)
    adm_paths = attrib(validator=optional(list_of(ADMPath)), repr=False, default=None)

    @importances.validator
    def importances_valid(self, attribute, value):
        if value is not None and len(value) != len(self.track_specs):
            raise ValueError("wrong number of ImportanceDatas provided")

    @adm_paths.validator
    def adm_paths_valid(self, attribute, value):
        if value is not None and len(value) != len(self.track_specs):
            raise ValueError("wrong number of ADMPaths provided")
