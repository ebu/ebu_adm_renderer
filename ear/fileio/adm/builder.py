from attr import attrs, attrib, Factory
from .adm import ADM
from .elements import AudioProgramme, AudioContent, AudioObject
from .elements import TypeDefinition, FormatDefinition
from .elements import AudioChannelFormat, AudioPackFormat, AudioTrackFormat, AudioTrackUID, AudioStreamFormat


class _Default(object):
    def __repr__(self):
        return "DEFAULT"


DEFAULT = _Default()


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
            kwargs: see :class:`AudioProgramme`

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
            kwargs: see :class:`AudioContent`

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
            kwargs: see :class:`AudioObject`

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
            kwargs: see :class:`AudioPackFormat`

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
            kwargs: see :class:`AudioChannelFormat`

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
    class MonoItem(object):
        """Structure referencing the ADM components created as part of a mono item.

        Attributes:
            channel_format (AudioChannelFormat)
            track_format (AudioTrackFormat)
            pack_format (AudioPackFormat)
            stream_format (AudioStreamFormat)
            track_uid (AudioTrackUID)
            audio_object (AudioObject)
            parent (Union[AudioContent, AudioObject])
        """

        channel_format = attrib()
        track_format = attrib()
        pack_format = attrib()
        stream_format = attrib()
        track_uid = attrib()
        audio_object = attrib()
        parent = attrib()

    def create_item_mono(self, type, track_index, name, parent=DEFAULT, block_formats=[]):
        """Create ADM components needed to represent a mono channel, either
        DirectSpeakers or Objects.

        Args:
            type (TypeDefinition): type of channelFormat and packFormat
            track_index (int): zero-based index of the track in the BWF file.
            name (str): name used for all components
            parent (Union[AudioContent, AudioObject]): parent of the created audioObject
                defaults to the last content or explicitly created object
            block_formats (list[AudioBlockFormat]): block formats to add to
                the channel format

        Returns:
            MonoItem: the created components
        """
        channel_format = AudioChannelFormat(
            audioChannelFormatName=name,
            type=type,
            audioBlockFormats=block_formats)
        self.adm.addAudioChannelFormat(channel_format)

        pack_format = AudioPackFormat(
            audioPackFormatName=name,
            type=type,
            audioChannelFormats=[channel_format],
        )
        self.adm.addAudioPackFormat(pack_format)

        stream_format = AudioStreamFormat(
            audioStreamFormatName=name,
            format=FormatDefinition.PCM,
            audioChannelFormat=channel_format,
        )
        self.adm.addAudioStreamFormat(stream_format)

        track_format = AudioTrackFormat(
            audioTrackFormatName=name,
            audioStreamFormat=stream_format,
            format=FormatDefinition.PCM,
        )
        self.adm.addAudioTrackFormat(track_format)

        track_uid = AudioTrackUID(
            trackIndex=track_index + 1,
            audioTrackFormat=track_format,
            audioPackFormat=pack_format,
        )
        self.adm.addAudioTrackUID(track_uid)

        audio_object = AudioObject(
            audioObjectName=name,
            audioPackFormats=[pack_format],
            audioTrackUIDs=[track_uid],
        )
        self.adm.addAudioObject(audio_object)

        if parent is DEFAULT:
            parent = self.item_parent
        if parent is not None:
            parent.audioObjects.append(audio_object)

        self.last_object = audio_object
        self.last_pack_format = pack_format
        self.last_stream_format = stream_format

        return self.MonoItem(
            channel_format=channel_format,
            track_format=track_format,
            pack_format=pack_format,
            stream_format=stream_format,
            track_uid=track_uid,
            audio_object=audio_object,
            parent=parent,
        )

    def create_item_objects(self, *args, **kwargs):
        """Create ADM components needed to represent an object channel.

        Wraps :func:`create_item_mono` with ``type=TypeDefinition.Objects``.
        """
        return self.create_item_mono(TypeDefinition.Objects, *args, **kwargs)

    def create_item_direct_speakers(self, *args, **kwargs):
        """Create ADM components needed to represent a DirectSpeakers channel.

        Wraps :func:`create_item_mono` with ``type=TypeDefinition.DirectSpeakers``.
        """
        return self.create_item_mono(TypeDefinition.DirectSpeakers, *args, **kwargs)
