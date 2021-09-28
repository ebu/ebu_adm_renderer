from attr import attrs, attrib, Factory
from .adm import ADM
from .elements import AudioProgramme, AudioContent, AudioObject
from .elements import TypeDefinition, FormatDefinition
from .elements import (
    AudioChannelFormat,
    AudioPackFormat,
    AudioTrackFormat,
    AudioTrackUID,
    AudioStreamFormat,
    AudioBlockFormatHoa,
)


class _Default(object):
    def __repr__(self):
        return "DEFAULT"


DEFAULT = _Default()


def _make_format_property(attribute):
    """Make a property which forwards gets/sets to format.attribute."""

    def getter(self):
        return getattr(self.format, attribute)

    def setter(self, new_val):
        return setattr(self.format, attribute, new_val)

    return property(getter, setter, doc=f"accessor for format.{attribute}")


def _make_singlar_property(attribute, attribute_singular):
    """Make a property which forwards gets/sets to attribute, assuming it is a
    list with a single entry.
    """

    def getter(self):
        items = getattr(self, attribute)
        assert len(items) == 1, f"expected 1 {attribute_singular}, got {len(items)}"
        return items[0]

    def setter(self, new_val):
        return setattr(self, attribute, [new_val])

    return property(getter, setter, doc=f"singular accessor for {attribute}")


@attrs
class ADMBuilder(object):
    """Builder object for creating ADM object graphs.

    Attributes:
        adm (ADM): ADM object to modify.
        last_programme (Optional[AudioProgramme]): The last programme created,
            to which created audioContents will be linked.
        last_content (Optional[AudioContent]): The last content created, to
            which created audioObjects will be linked by default.
        last_object (Optional[AudioObject]): The last object created, to which
            created audioObjects or audioPackFormats will be linked by default.
        last_pack_format (Optional[AudioPackFormat]): The last pack_format
            created, to which created audioChannelFormats will be linked by
            default.
        last_stream_format (Optional[AudioStreamFormat]): The last
            stream_format created, to which created audioTrackFormats will be
            linked by default.
        item_parent (Optional[Union[AudioContent, AudioObject]]): The last
            explicitly created audioContent or audioObject, used as the parent
            for audioObjects created by create_item* functions.
    """

    adm = attrib(default=Factory(ADM))
    last_programme = attrib(default=None)
    last_content = attrib(default=None)
    last_object = attrib(default=None)
    last_pack_format = attrib(default=None)
    last_stream_format = attrib(default=None)
    item_parent = attrib(default=None)

    def load_common_definitions(self):
        """Load common definitions into adm."""
        from .common_definitions import load_common_definitions

        load_common_definitions(self.adm)

    def create_programme(self, **kwargs):
        """Create a new audioProgramme.

        Args:
            kwargs: see :class:`.AudioProgramme`

        Returns:
            AudioProgramme: created audioProgramme
        """
        programme = AudioProgramme(**kwargs)
        self.adm.addAudioProgramme(programme)

        self.last_programme = programme

        return programme

    def create_content(self, parent=DEFAULT, **kwargs):
        """Create a new audioContent.

        Args:
            parent (AudioProgramme): parent programme; defaults to the last one created
            kwargs: see :class:`.AudioContent`

        Returns:
            AudioContent: created audioContent
        """
        content = AudioContent(**kwargs)
        self.adm.addAudioContent(content)

        if parent is DEFAULT:
            parent = self.last_programme
        if parent is not None:
            parent.audioContents.append(content)

        self.last_content = content
        self.item_parent = content

        return content

    def create_object(self, parent=DEFAULT, **kwargs):
        """Create a new audioObject.

        Args:
            parent (Union[AudioContent, AudioObject]): parent content or
                object; defaults to the last content created
            kwargs: see :class:`.AudioObject`

        Returns:
            AudioObject: created audioObject
        """
        object = AudioObject(**kwargs)
        self.adm.addAudioObject(object)

        if parent is DEFAULT:
            parent = self.last_content
        if parent is not None:
            parent.audioObjects.append(object)

        self.item_parent = object
        self.last_object = object

        return object

    def create_pack(self, parent=DEFAULT, **kwargs):
        """Create a new audioPackFormat.

        Args:
            parent (AudioObject or AudioPackFormat): parent object or packFormat;
                defaults to the last object created
            kwargs: see :class:`.AudioPackFormat`

        Returns:
            AudioPackFormat: created audioPackFormat
        """
        pack_format = AudioPackFormat(**kwargs)
        self.adm.addAudioPackFormat(pack_format)

        if parent is DEFAULT:
            parent = self.last_object
        if parent is not None:
            parent.audioPackFormats.append(pack_format)

        self.last_pack_format = pack_format

        return pack_format

    def create_channel(self, parent=DEFAULT, **kwargs):
        """Create a new audioChannelFormat.

        Args:
            parent (AudioPackFormat): parent packFormat;
                defaults to the last packFormat created
            kwargs: see :class:`.AudioChannelFormat`

        Returns:
            AudioChannelFormat: created audioChannelFormat
        """
        channel_format = AudioChannelFormat(**kwargs)
        self.adm.addAudioChannelFormat(channel_format)

        if parent is DEFAULT:
            parent = self.last_pack_format
        if parent is not None:
            parent.audioChannelFormats.append(channel_format)

        return channel_format

    def create_stream(self, **kwargs):
        """Create a new audioStreamFormat.

        Args:
            kwargs: see AudioChannelFormat

        Returns:
            AudioStreamFormat: created audioStreamFormat
        """
        stream_format = AudioStreamFormat(**kwargs)
        self.adm.addAudioStreamFormat(stream_format)

        self.last_stream_format = stream_format

        return stream_format

    def create_track(self, parent=DEFAULT, **kwargs):
        """Create a new audioTrackFormat.

        Args:
            parent (AudioStreamFormat): parent streamFormat;
                defaults to the last audioStreamFormat created
            kwargs: see AudioTrackFormat

        Returns:
            AudioTrackFormat: created audioTrackFormat
        """
        track_format = AudioTrackFormat(**kwargs)
        self.adm.addAudioTrackFormat(track_format)

        if parent is DEFAULT:
            parent = self.last_stream_format
        if parent is not None:
            track_format.audioStreamFormat = parent

        return track_format

    def create_track_uid(self, parent=DEFAULT, **kwargs):
        """Create a new audioTrackUID.

        Args:
            parent (AudioObject): parent audioObject;
                defaults to the last audioObject created
            kwargs: see AudioTrackUID

        Returns:
            AudioTrackUID: created audioTrackUID
        """
        track_uid = AudioTrackUID(**kwargs)
        self.adm.addAudioTrackUID(track_uid)

        if parent is DEFAULT:
            parent = self.last_object
        if parent is not None:
            parent.audioTrackUIDs.append(track_uid)

        return track_uid

    @attrs
    class Format(object):
        """Structure referencing the ADM components of a format with a
        particular channel layout.

        This holds an audioPackFormat, and one audioTrackFormat,
        audioStreamFormat and audioChannelFormat per channel in the format.

        Attributes:
            channel_formats (list[AudioChannelFormat])
            track_formats (list[AudioTrackFormat])
            pack_format (AudioPackFormat)
            stream_formats (list[AudioStreamFormat])
        """

        channel_formats = attrib()
        track_formats = attrib()
        pack_format = attrib()
        stream_formats = attrib()

        channel_format = _make_singlar_property("channel_formats", "channel_format")
        track_format = _make_singlar_property("track_formats", "track_format")
        stream_format = _make_singlar_property("stream_formats", "stream_format")

    @attrs
    class Item(object):
        """Structure referencing the ADM components of a created item.

        This holds an audioObject, one audioTrackUID per channel, and a
        reference to :class:`Format` for the format parts of the item.

        Attributes:
            format (Format)
            track_uids (list[AudioTrackUID])
            audio_object (AudioObject)
            parent (Union[AudioContent, AudioObject])
        """

        format = attrib()
        track_uids = attrib()
        audio_object = attrib()
        parent = attrib()

        track_uid = _make_singlar_property("track_uids", "track_uid")

        channel_formats = _make_format_property("channel_formats")
        track_formats = _make_format_property("track_formats")
        pack_format = _make_format_property("pack_format")
        stream_formats = _make_format_property("stream_formats")

        channel_format = _make_format_property("channel_format")
        track_format = _make_format_property("track_format")
        stream_format = _make_format_property("stream_format")

    MonoItem = Item
    """compatibility alias for users expecting \\*_mono to return MonoItem"""

    def create_format_mono(
        self,
        type,
        name,
        block_formats=[],
    ):
        """Create ADM components needed to represent a mono format.

        This makes:

        - an audioChannelFormat with the given block_formats
        - an audioPackFormat linked to the audioChannelFormat
        - an audioStreamFormat linked to the audioChannelFormat
        - an audioTrackFormat linked to the audioStreamFormat

        Args:
            type (TypeDefinition): type of channelFormat and packFormat
            name (str): name used for all components
            block_formats (list[AudioBlockFormat]): block formats to add to
                the channel format

        Returns:
            Format: the created components
        """
        format = self.create_format_multichannel(
            type=type,
            name=name,
            block_formats=[block_formats],
        )

        self.last_pack_format = format.pack_format
        self.last_stream_format = format.stream_format

        return format

    def create_item_mono_from_format(
        self,
        format,
        track_index,
        name,
        parent=DEFAULT,
    ):
        """Create ADM components needed to represent a mono channel given an
        existing format.

        This makes:

        - an audioTrackUID linked to the audioTrackFormat and audioPackFormat
          of format
        - an audioObject linked to the audioTrackUID and audioPackFormat

        Args:
            format (Format)
            track_index (int): zero-based index of the track in the BWF file.
            name (str): name used for all components
            parent (Union[AudioContent, AudioObject]): parent of the created audioObject
                defaults to the last content or explicitly created object

        Returns:
            Item: the created components
        """
        item = self.create_item_multichannel_from_format(
            format=format,
            track_indices=[track_index],
            name=name,
            parent=parent,
        )

        self.last_pack_format = item.pack_format
        self.last_stream_format = item.stream_format

        return item

    def create_item_mono(
        self, type, track_index, name, parent=DEFAULT, block_formats=[]
    ):
        """Create ADM components needed to represent a mono channel, either
        DirectSpeakers or Objects.

        This makes:

        - an audioChannelFormat with the given block_formats
        - an audioPackFormat linked to the audioChannelFormat
        - an audioStreamFormat linked to the audioChannelFormat
        - an audioTrackFormat linked to the audioStreamFormat
        - an audioTrackUID linked to the audioTrackFormat and audioPackFormat
        - an audioObject linked to the audioTrackUID and audioPackFormat

        Args:
            type (TypeDefinition): type of channelFormat and packFormat
            track_index (int): zero-based index of the track in the BWF file.
            name (str): name used for all components
            parent (Union[AudioContent, AudioObject]): parent of the created audioObject
                defaults to the last content or explicitly created object
            block_formats (list[AudioBlockFormat]): block formats to add to
                the channel format

        Returns:
            Item: the created components
        """
        item = self.create_item_multichannel(
            type=type,
            track_indices=[track_index],
            name=name,
            block_formats=[block_formats],
            parent=parent,
        )

        self.last_pack_format = item.pack_format
        self.last_stream_format = item.stream_format

        return item

    def create_item_objects(self, *args, **kwargs):
        """Create ADM components needed to represent an object channel.

        Wraps :func:`create_item_mono` with ``type=TypeDefinition.Objects``.

        Returns:
            Item: the created components
        """
        return self.create_item_mono(TypeDefinition.Objects, *args, **kwargs)

    def create_item_direct_speakers(self, *args, **kwargs):
        """Create ADM components needed to represent a DirectSpeakers channel.

        Wraps :func:`create_item_mono` with ``type=TypeDefinition.DirectSpeakers``.

        Returns:
            Item: the created components
        """
        return self.create_item_mono(TypeDefinition.DirectSpeakers, *args, **kwargs)

    def create_format_multichannel(self, type, name, block_formats):
        """Create ADM components representing a multi-channel format.

        This makes:

        - an audioChannelFormat for each channel
        - an audioStreamFormat linked to each audioChannelFormat
        - an audioTrackFormat linked to each audioStreamFormat
        - an audioPackFormat linked to the audioChannelFormats

        Args:
            type (TypeDefinition): type of channelFormat and packFormat
            name (str): name used for all components
            block_formats (list[list[AudioBlockFormat]]): list of audioBlockFormats
                for each audioChannelFormat

        Returns:
            Format: the created components
        """
        channel_formats = []
        stream_formats = []
        track_formats = []

        for i, channel_block_formats in enumerate(block_formats):
            channel_name = f"{name}_{i + 1}" if len(block_formats) > 1 else name

            channel_format = AudioChannelFormat(
                audioChannelFormatName=channel_name,
                type=type,
                audioBlockFormats=channel_block_formats,
            )
            self.adm.addAudioChannelFormat(channel_format)
            channel_formats.append(channel_format)

            stream_format = AudioStreamFormat(
                audioStreamFormatName=channel_name,
                format=FormatDefinition.PCM,
                audioChannelFormat=channel_format,
            )
            self.adm.addAudioStreamFormat(stream_format)
            stream_formats.append(stream_format)

            track_format = AudioTrackFormat(
                audioTrackFormatName=channel_name,
                audioStreamFormat=stream_format,
                format=FormatDefinition.PCM,
            )
            self.adm.addAudioTrackFormat(track_format)
            track_formats.append(track_format)

        pack_format = AudioPackFormat(
            audioPackFormatName=name,
            type=type,
            audioChannelFormats=channel_formats[:],
        )
        self.adm.addAudioPackFormat(pack_format)

        return self.Format(
            channel_formats=channel_formats,
            track_formats=track_formats,
            pack_format=pack_format,
            stream_formats=stream_formats,
        )

    def create_item_multichannel_from_format(
        self,
        format,
        track_indices,
        name,
        parent=DEFAULT,
    ):
        """Create ADM components representing a multi-channel object,
        referencing an existing format structure.

        This makes:

        - an audioTrackUID linked to each audioTrackFormat and the audioPackFormat in format
        - an audioObject linked to the audioTrackUIDs and the audioPackFormat in format

        Args:
            format (Format): format components to reference
            track_indices (list[int]): zero-based indices of the tracks in the BWF file.
            name (str): name used for all components
            parent (Union[AudioContent, AudioObject]): parent of the created audioObject
                defaults to the last content or explicitly created object

        Returns:
            Item: the created components
        """
        if len(track_indices) != len(format.track_formats):
            raise ValueError(
                "track_indices and format must have the same number of channels"
            )

        track_uids = []

        for i, (track_index, track_format) in enumerate(
            zip(track_indices, format.track_formats)
        ):
            track_uid = AudioTrackUID(
                trackIndex=track_index + 1,
                audioTrackFormat=track_format,
                audioPackFormat=format.pack_format,
            )
            self.adm.addAudioTrackUID(track_uid)
            track_uids.append(track_uid)

        audio_object = AudioObject(
            audioObjectName=name,
            audioPackFormats=[format.pack_format],
            audioTrackUIDs=track_uids[:],
        )
        self.adm.addAudioObject(audio_object)

        if parent is DEFAULT:
            parent = self.item_parent
        if parent is not None:
            parent.audioObjects.append(audio_object)

        self.last_object = audio_object
        self.last_pack_format = format.pack_format

        return self.Item(
            format=format,
            track_uids=track_uids,
            audio_object=audio_object,
            parent=parent,
        )

    def create_item_multichannel(
        self,
        type,
        track_indices,
        name,
        block_formats,
        parent=DEFAULT,
    ):
        """Create ADM components representing a multi-channel object.

        This makes:

        - an audioChannelFormat for each channel
        - an audioStreamFormat linked to each audioChannelFormat
        - an audioTrackFormat linked to each audioStreamFormat
        - an audioPackFormat linked to the audioChannelFormats
        - an audioTrackUID linked to each audioTrackFormat and the audioPackFormat
        - an audioObject linked to the audioTrackUIDs and the audioPackFormat

        Args:
            type (TypeDefinition): type of channelFormat and packFormat
            track_indices (list[int]): zero-based indices of the tracks in the BWF file.
            name (str): name used for all components
            block_formats (list[list[AudioBlockFormat]]): list of audioBlockFormats
                for each audioChannelFormat
            parent (Union[AudioContent, AudioObject]): parent of the created audioObject
                defaults to the last content or explicitly created object

        Returns:
            Item: the created components
        """
        if len(track_indices) != len(block_formats):
            raise ValueError("track_indices and block_formats must be the same length")

        format = self.create_format_multichannel(
            type=type,
            name=name,
            block_formats=block_formats,
        )

        return self.create_item_multichannel_from_format(
            format=format,
            track_indices=track_indices,
            name=name,
            parent=parent,
        )

    def create_format_hoa(
        self,
        orders,
        degrees,
        name,
        **kwargs,
    ):
        """Create ADM components representing the format of a HOA stream.

        This is a wrapper around :func:`create_format_multichannel`.

        Args:
            orders (list[int]): order for each track
            degrees (list[int]): degree for each track
            name (str): name used for all components
            kwargs: arguments for :class:`.AudioBlockFormatHoa`

        Returns:
            Format: the created components
        """
        block_formats = [
            [
                AudioBlockFormatHoa(
                    order=order,
                    degree=degree,
                    **kwargs,
                )
            ]
            for order, degree in zip(orders, degrees)
        ]

        return self.create_format_multichannel(
            type=TypeDefinition.HOA,
            name=name,
            block_formats=block_formats,
        )

    def create_item_hoa(
        self,
        track_indices,
        orders,
        degrees,
        name,
        parent=DEFAULT,
        **kwargs,
    ):
        """Create ADM components representing a HOA stream.

        This is a wrapper around :func:`create_format_hoa` and
        :func:`create_item_multichannel_from_format`.

        Args:
            track_indices (list[int]): zero-based indices of the tracks in the BWF file.
            orders (list[int]): order for each track
            degrees (list[int]): degree for each track
            name (str): name used for all components
            parent (Union[AudioContent, AudioObject]): parent of the created audioObject
                defaults to the last content or explicitly created object
            kwargs: arguments for :class:`.AudioBlockFormatHoa`

        Returns:
            Item: the created components
        """
        format = self.create_format_hoa(
            orders=orders,
            degrees=degrees,
            name=name,
            **kwargs,
        )

        return self.create_item_multichannel_from_format(
            format=format,
            track_indices=track_indices,
            name=name,
            parent=parent,
        )
