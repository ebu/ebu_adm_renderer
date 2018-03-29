import logging
from collections import defaultdict, Counter
import warnings
from .bw64 import Bw64Reader, Bw64Writer
from .adm.adm import ADM
from .adm.xml import load_axml_string, default_screen
from .adm.common_definitions import load_common_definitions
from .adm.exceptions import AdmError
from .adm.elements import TypeDefinition
from .adm.chna import load_chna_chunk
from ..core.metadata_input import (ExtraData, MetadataSourceIter,
                                   ObjectTypeMetadata, ObjectRenderingItem,
                                   DirectSpeakersTypeMetadata, DirectSpeakersRenderingItem,
                                   HOATypeMetadata, HOARenderingItem, ImportanceData
                                   )


def openBw64(filename, mode='r', **kwargs):
    if mode == 'r':
        fileHandle = open(filename, 'rb')
        try:
            return Bw64Reader(fileHandle, **kwargs)
        except:  # noqa: E722
            fileHandle.close()
            raise
    elif mode == 'w':
        fileHandle = open(filename, 'wb')
        try:
            return Bw64Writer(fileHandle, **kwargs)
        except:  # noqa: E722
            fileHandle.close()
            raise
    else:
        raise RuntimeError('unknown mode: ' + str(mode))


def openBw64Adm(filename, fix_block_format_durations=False):
    fileHandle = open(filename, 'rb')
    try:
        bw64FileHandle = Bw64Reader(fileHandle)
        return Bw64AdmReader(bw64FileHandle, fix_block_format_durations)
    except:  # noqa: E722
        fileHandle.close()
        raise


def _in_by_id(element, collection):
    """Check if element is in collection, by comparing identity rather than equality."""
    return any(element is item for item in collection)


class Bw64AdmReader(object):

    def __init__(self, bw64FileHandle, fix_block_format_durations=False):
        self.logger = logging.getLogger(__name__)
        self._bw64 = bw64FileHandle
        self._fix_block_format_durations = fix_block_format_durations
        self._renderingItemHandler = RenderingItemHandler(self._parse_adm())

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._bw64._buffer.close()

    @property
    def chna(self):
        return self._bw64.chna

    @property
    def sampleRate(self):
        return self._bw64.sampleRate

    @property
    def channels(self):
        return self._bw64.channels

    @property
    def bitdepth(self):
        return self._bw64.bitdepth

    @property
    def selected_items(self):
        return self._renderingItemHandler.selected_items

    def iter_sample_blocks(self, blockSize):
        """Read samples blockwise until next ChangeSet and yield it."""
        while(self._bw64.tell() != len(self._bw64)):
            yield self._bw64.read(blockSize)

    def _parse_adm(self):
        adm = ADM()
        load_common_definitions(adm)
        if self._bw64.axml is not None:
            self.logger.info("Parsing")
            load_axml_string(adm, self._bw64.axml, fix_block_format_durations=self._fix_block_format_durations)
            self.logger.info("Parsing done!")
        load_chna_chunk(adm, self._bw64.chna)
        return adm


def _update_importance_value(current_importance=None, other_importance=None):
    """Returns the updated other important value of its less than the current value

    Instead of a simple comparison, this also takes into that one or both of
    the input values might be None.
    """
    if current_importance is None:
        return other_importance
    elif other_importance is None:
        return current_importance
    else:
        return min(other_importance, current_importance)


def _recurse_audio_packs(pack_formats):
    for pack in pack_formats:
        for sub_pack, sub_importance in _recurse_audio_pack(pack):
            yield sub_pack, sub_importance


def _recurse_audio_pack(pack_format, path=(), current_pack_importance=None):
    """Yield all audioPackFormsts referenced by a given audioPackFormat, including itself."""
    if _in_by_id(pack_format, path):
        raise AdmError("loop detected in AudioPackFormats: {path}".format(path=' -> '.join(o.id for o in path)))
    path = path + (pack_format,)

    current_pack_importance = _update_importance_value(current_pack_importance, pack_format.importance)

    yield pack_format, current_pack_importance

    for direct_sub_pack in pack_format.audioPackFormats:
        for sub_pack, sub_importance in _recurse_audio_pack(direct_sub_pack, path, current_pack_importance):
            yield sub_pack, sub_importance


def _calulate_pack_importance(target_pack_format, parent_audio_object):
    """
    Calculates the effective importance for the `target_pack_format`, taking
    into account all potential parent audio_packs starting from `parent_audio_object`.
    """
    if parent_audio_object is None:
        return target_pack_format.importance
    for pack, importance in _recurse_audio_packs(parent_audio_object.audioPackFormats):
        if pack.id == target_pack_format.id:
            return importance
    return None


class RenderingItemHandler():

    def __init__(self, adm, audio_programme_id=None, selected_complementary_objects=None):
        self._adm = adm
        self._audio_programme_id = audio_programme_id
        if selected_complementary_objects is not None:
            self._selected_complementary_objects = selected_complementary_objects
        else:
            self._selected_complementary_objects = {}
        self._ignore_object_list = []
        self._map_track_format_to_stream_format()
        self._select_complementary_objects()
        self.selected_items = self._select_rendering_items()

    def _select_programme(self):
        """Select the audioProgramme"""
        if self._audio_programme_id is None:
            if len(self._adm.audioProgrammes) > 1:
                warnings.warn("more than one audioProgramme; selecting the one with the lowest id")
            return sorted(self._adm.audioProgrammes, key=lambda programme: programme.id)[0]

        for programme in self._adm.audioProgrammes:
            if programme.id == self._audio_programme_id:
                return programme

    def _root_objects(self):
        """Get all objects which are not sub-objects of another object."""
        non_root_objects = set(id(subObject)
                               for audioObject in self._adm.audioObjects
                               for subObject in audioObject.audioObjects)

        for audioObject in self._adm.audioObjects:
            if id(audioObject) not in non_root_objects:
                yield audioObject

    def _select_objects(self):
        """Get objects (and their associated reference screens) to render,
        either via the programmes or by selecting all objects.

        yields:
            AudioObject
            AudioProgramme.CartesianReferenceScreen or AudioProgramme.PolarReferenceScreen
        """
        if self._adm.audioProgrammes:
            audioProgramme = self._select_programme()
            for audioContent in audioProgramme.audioContents:
                for audioObject in audioContent.audioObjects:
                    for subObject, object_importance in self._sub_objects(audioObject):
                        if subObject not in self._ignore_object_list:
                            yield subObject, audioProgramme.referenceScreen, object_importance
        else:
            for audioObject in self._root_objects():
                for subObject, object_importance in self._sub_objects(audioObject):
                    if subObject not in self._ignore_object_list:
                        yield subObject, default_screen, object_importance

    def _sub_objects(self, audio_object, path=(), current_object_importance=None):
        """Yield all audioObjects referenced by a given audioObject, including itself."""
        if _in_by_id(audio_object, path):
            raise AdmError("loop detected in audioObjects: {path}".format(path=' -> '.join(o.id for o in path)))
        path = path + (audio_object,)

        current_object_importance = _update_importance_value(current_object_importance, audio_object.importance)

        yield audio_object, current_object_importance

        for direct_sub_object in audio_object.audioObjects:
            for sub_object, sub_importance in self._sub_objects(direct_sub_object, path, current_object_importance):
                yield sub_object, sub_importance

    def _ignore_object(self, audio_object):
        for sub_object, object_importance in self._sub_objects(audio_object):
            self._ignore_object_list.append(sub_object)

    def _complementary_audio_object_group(self, audio_object):
        yield audio_object
        for comp_audio_object in audio_object.audioComplementaryObjects:
            yield comp_audio_object

    def _select_complementary_objects(self):
        for audio_object in self._adm.audioObjects:
            selected_comp_audio_object = self._selected_complementary_objects.get(audio_object.id,
                                                                                  audio_object.id)
            for comp_audio_object in self._complementary_audio_object_group(audio_object):
                if comp_audio_object.id != selected_comp_audio_object:
                    self._ignore_object(comp_audio_object)

    def _select_tracks(self):
        """Get selected tracks with information from elsewhere in the ADM.

        Either selects tracks from audioObjects if there is a
        programme/content/object structure (see _select_objects), or just
        selects all tracks; this is intended to handle files without an AXML
        chunk.

        Yields:
            AudioTrackUID -- track to render
            ExtraData -- populated with object times, and reference screen
            AudioObject -- if this track was found inside an audio object
        """
        if self._adm.audioObjects or self._adm.audioProgrammes:
            for audioObject, referenceScreen, object_importance in self._select_objects():
                for audio_track_uid in audioObject.audioTrackUIDs:
                    extra_data = ExtraData(object_start=audioObject.start,
                                           object_duration=audioObject.duration,
                                           reference_screen=referenceScreen)
                    yield audio_track_uid, extra_data, audioObject, object_importance
        else:
            for audio_track_uid in self._adm.audioTrackUIDs:
                yield audio_track_uid, ExtraData(), None, None

    def _channels_in_pack_format(self, pack_format):
        channels = []

        for nested_pack_format in pack_format.audioPackFormats:
            channels.extend(self._channels_in_pack_format(nested_pack_format))

        channels.extend(pack_format.audioChannelFormats)

        return channels

    def _map_track_format_to_stream_format(self):
        """Map audioStreamFormat to audioTrackFormat references."""
        self._atf_to_asf_mapping = {}
        for stream in self._adm.audioStreamFormats:
            for track in stream.audioTrackFormats:
                if id(track) in self._atf_to_asf_mapping:
                    raise AdmError("don't know how to handle audioTrackFormat linked to by multiple audioStreamFormats")
                self._atf_to_asf_mapping[id(track)] = stream

    def _check_consistency(self, audio_object, audio_track_uid):
        """Check consistency"""

        track_format = audio_track_uid.audioTrackFormat
        if id(track_format) not in self._atf_to_asf_mapping:
            raise AdmError("audioTrackUID '{atu.id}' references audioTrackFormat '{atf.id}', which is not referenced by any audioStreamFormat".format(
                           atu=audio_track_uid,
                           atf=track_format)
                           )

        stream_format = self._atf_to_asf_mapping[id(track_format)]
        channel_format = stream_format.audioChannelFormat
        if channel_format is None:
            raise AdmError("no audioChannelFormat linked from audioStreamFormat {asf.id}".format(asf=stream_format))
        if audio_track_uid.trackIndex is None:
            raise AdmError("audioTrackUID {atu.id} does not have a track index, "
                           "which should be specified in the CHNA chunk".format(atu=audio_track_uid))

        if audio_track_uid.audioPackFormat is not None:
            if audio_object is not None and audio_object.audioPackFormats:
                unravelled_audio_packs = [pack for pack, importance in _recurse_audio_packs(audio_object.audioPackFormats)]
                if not _in_by_id(audio_track_uid.audioPackFormat, unravelled_audio_packs):
                    raise AdmError("audioObject {ao.id} does not reference audioPackFormat {apf.id} "
                                   "which is referenced by audioTrackUID {atu.id}".format(
                                       ao=audio_object,
                                       apf=audio_track_uid.audioPackFormat,
                                       atu=audio_track_uid))
            if not _in_by_id(channel_format, self._channels_in_pack_format(audio_track_uid.audioPackFormat)):
                raise AdmError("audioPackFormat {apf.id} does not reference audioChannelFormat {acf.id} "
                               "which is referenced by audioTrackUID {atu.id}".format(
                                   apf=audio_track_uid.audioPackFormat,
                                   acf=channel_format,
                                   atu=audio_track_uid))

    def _select_rendering_items(self):
        """Select items to render.

        The items are selected by following the references from an
        audioProgramme to every individual audioChannelFormat

             audioProgramme
          -> audioContent
          -> audioObject
          -> audioTrackUID
          -> audioTrackFormat
          -> audioStreamFormat
          -> audioChannelFormat

        If there is no audioProgramme within the ADM file, the collection of all
        audioObjects will be used as the starting point.

        Returns:
            list of RenderingItem
        """
        hoa_channels_by_object_pack = defaultdict(list)
        items = []

        for audio_track_uid, extra_data, audio_object, object_importance in self._select_tracks():
            self._check_consistency(audio_object, audio_track_uid)

            stream_format = self._atf_to_asf_mapping[id(audio_track_uid.audioTrackFormat)]
            channel_format = stream_format.audioChannelFormat
            extra_data.channel_frequency = channel_format.frequency
            pack_importance = _calulate_pack_importance(audio_track_uid.audioPackFormat, audio_object)
            importance = ImportanceData(audio_object=object_importance, audio_pack_format=pack_importance)

            if channel_format.type == TypeDefinition.Objects:
                metadata_source = MetadataSourceIter([ObjectTypeMetadata(block_format=block_format,
                                                                         extra_data=extra_data)
                                                      for block_format in channel_format.audioBlockFormats])

                items.append(ObjectRenderingItem(track_index=audio_track_uid.trackIndex - 1,
                                                 metadata_source=metadata_source,
                                                 importance=importance))
            elif channel_format.type == TypeDefinition.DirectSpeakers:
                metadata_source = MetadataSourceIter([DirectSpeakersTypeMetadata(block_format=block_format,
                                                                                 extra_data=extra_data)
                                                      for block_format in channel_format.audioBlockFormats])

                items.append(DirectSpeakersRenderingItem(track_index=audio_track_uid.trackIndex - 1,
                                                         metadata_source=metadata_source,
                                                         importance=importance))
            elif channel_format.type == TypeDefinition.HOA:
                if audio_track_uid.audioPackFormat is None:
                    raise AdmError("HOA track UIDs must have a pack format")

                hoa_channels_by_object_pack[(id(audio_object), id(audio_track_uid.audioPackFormat))].append((audio_track_uid,
                                                                                                             channel_format,
                                                                                                             extra_data,
                                                                                                             importance))
            else:
                raise Exception("Don't know how to produce rendering items for type {type}".format(type=channel_format.type))

        for channels in hoa_channels_by_object_pack.values():
            items.append(self._hoa_channels_to_rendering_item(channels))

        return items

    def _hoa_channels_to_rendering_item(self, channels):
        """Turn a list of associated HOA channels into a rendering item.

        Args:
            channels (list): list of tuples:
                - audioTrackUID
                - audioChannelFormat
                - ExtraData

        Returns:
            TypeMetadata
        """
        audio_track_uid, channel_format, reference_extra_data, reference_importance = channels[0]
        [reference_block_format] = channel_format.audioBlockFormats

        orders = []
        degrees = []
        track_indices = []

        for audio_track_uid, channel_format, extra_data, importance in channels:
            [block_format] = channel_format.audioBlockFormats

            if (block_format.order, block_format.degree) in zip(orders, degrees):
                raise AdmError("Duplicate HOA orders and degrees found; see {audio_track_uid.id}.".format(audio_track_uid=audio_track_uid))

            if audio_track_uid.trackIndex - 1 in track_indices:
                raise AdmError("Duplicate tracks used in HOA; see {track.id}.".format(track=audio_track_uid))

            orders.append(block_format.order)
            degrees.append(block_format.degree)
            track_indices.append(audio_track_uid.trackIndex - 1)

            # other block and channel attributes must match
            if block_format.normalization != reference_block_format.normalization:
                raise AdmError("All HOA channel formats in a single pack format must have the same normalization.")
            if block_format.nfcRefDist != reference_block_format.nfcRefDist:
                raise AdmError("All HOA channel formats in a single pack format must have the same nfcRefDist.")
            if block_format.screenRef != reference_block_format.screenRef:
                raise AdmError("All HOA channel formats in a single pack format must have the same screenRef.")
            if extra_data.channel_frequency != reference_extra_data.channel_frequency:
                raise AdmError("All HOA channel formats in a single pack format must have the same frequency.")

            if block_format.rtime != reference_block_format.rtime:
                raise AdmError("All HOA block formats must not have same rtime.")
            if block_format.duration != reference_block_format.duration:
                raise AdmError("All HOA block formats must not have same duration.")

            assert extra_data == reference_extra_data
            assert importance == reference_importance

        # check that orders/degrees/indices? are unique
        if any(count != 1 for count in Counter(zip(orders, degrees)).values()):
            raise AdmError("Duplicated orders and degrees in HOA.")
        if any(count != 1 for count in Counter(track_indices).values()):
            raise AdmError("Duplicated track indices in HOA.")

        type_metadata = HOATypeMetadata(
            rtime=reference_block_format.rtime,
            duration=reference_block_format.duration,
            orders=orders,
            degrees=degrees,
            normalization=reference_block_format.normalization,
            nfcRefDist=reference_block_format.nfcRefDist,
            screenRef=reference_block_format.screenRef,
            extra_data=reference_extra_data,
        )
        metadata_source = MetadataSourceIter([type_metadata])
        return HOARenderingItem(track_indices=track_indices,
                                metadata_source=metadata_source,
                                importance=reference_importance)
