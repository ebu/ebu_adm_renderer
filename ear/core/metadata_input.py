from attr import attrib, attrs, Factory
from attr.validators import instance_of, optional
from fractions import Fraction
from ..common import list_of, default_screen
from ..fileio.adm.elements import AudioBlockFormatObjects, AudioBlockFormatDirectSpeakers, Frequency


class MetadataSource(object):
    """A source of metadata for some input channels."""

    def get_next_block(self):
        """Get the next metadata block, if one is available.

        Returns:
            TypeMetadata
        """
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
    """Base class for *TypeMetadata classes; these should represent all the
    parameters needed to render some set of audio channels within some time
    bounds.
    """


@attrs(slots=True)
class RenderingItem(object):
    """Base class for *RenderingItem classes; these should represent an item to
    be rendered, combining a MetadataSource that produces a sequence of
    TypeMetadata objects, and some indices into the tracks that this metadata
    applies to.
    """


@attrs(slots=True)
class ExtraData(object):
    """Common metadata from outside the ADM block format.

    Attributes:
        object_start (Fraction or None): Start time of audioObject.
        object_duration (Fraction or None): Duration of audioObject.
        reference_screen (CartesianScreen or PolarScreen): Reference screen from audioProgramme.
        channel_frequency (Frequency): Frequency information from audioChannel.
    """
    object_start = attrib(validator=optional(instance_of(Fraction)), default=None)
    object_duration = attrib(validator=optional(instance_of(Fraction)), default=None)
    reference_screen = attrib(default=default_screen)
    channel_frequency = attrib(validator=instance_of(Frequency), default=Factory(Frequency))


@attrs(slots=True)
class ImportanceData(object):
    """Importance metadata for a RenderingItem

    Attributes:
        audio_object (int or None): Importance that has been derived from the audioObject level
        audio_pack_format (int or None): Importance that has been derived from the audioPackFormat level
    """
    audio_object = attrib(validator=optional(instance_of(int)), default=None)
    audio_pack_format = attrib(validator=optional(instance_of(int)), default=None)


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
        track_index (int): Zero based input track index for this item.
        metadata_source (MetadataSource): Source of ObjectTypeMetadata objects.
        importance (ImportanceData): Importance values applicable for this item.
    """
    track_index = attrib(validator=instance_of(int))
    metadata_source = attrib(validator=instance_of(MetadataSource))
    importance = attrib(validator=instance_of(ImportanceData), default=Factory(ImportanceData))


# direct speakers

@attrs(slots=True)
class DirectSpeakersTypeMetadata(TypeMetadata):
    """TypeMetadata for typeDefinition="DirectSpeakers"

    Attributes:
        block_format (AudioBlockFormatDirectSpeakerss): Block format.
        extra_data (ExtraData): Extra parameters from outside block format.
    """
    block_format = attrib(validator=instance_of(AudioBlockFormatDirectSpeakers))
    extra_data = attrib(validator=instance_of(ExtraData), default=Factory(ExtraData))


@attrs(slots=True)
class DirectSpeakersRenderingItem(RenderingItem):
    """RenderingItem for typeDefinition="DirectSpeakers"

    Attributes:
        track_index (int): Zero based input track index for this item.
        metadata_source (MetadataSource): Source of DirectSpeakersTypeMetadata objects.
        importance (ImportanceData): Importance values applicable for this item.
    """
    track_index = attrib(validator=instance_of(int))
    metadata_source = attrib(validator=instance_of(MetadataSource))
    importance = attrib(validator=instance_of(ImportanceData), default=Factory(ImportanceData))


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
        extra_data (ExtraData): Info from object and channels for all channels.
        rtime (Fraction or None): Start time of block.
        duration (Fraction or None): Duration of block.
    """
    orders = attrib(validator=list_of(int))
    degrees = attrib(validator=list_of(int))
    normalization = attrib()
    nfcRefDist = attrib(validator=optional(instance_of(float)), default=None)
    screenRef = attrib(validator=instance_of(bool), default=False)
    extra_data = attrib(validator=instance_of(ExtraData), default=Factory(ExtraData))
    rtime = attrib(default=None, validator=optional(instance_of(Fraction)))
    duration = attrib(default=None, validator=optional(instance_of(Fraction)))


@attrs(slots=True)
class HOARenderingItem(RenderingItem):
    """RenderingItem for typeDefinition="HOA"

    Attributes:
        track_indices (collection of int): Zero based index of each track in this item.
        metadata_source (MetadataSource): Source of HOATypeMetadata objects;
            will usually contain only one object.
        importance (ImportanceData): Importance values applicable for this item.
    """
    track_indices = attrib()
    metadata_source = attrib(validator=instance_of(MetadataSource))
    importance = attrib(validator=instance_of(ImportanceData), default=Factory(ImportanceData))
