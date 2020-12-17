from attr import attrs, attrib, evolve
from attr.validators import instance_of, optional
import numpy as np
import warnings
from ...common import list_of
from ...fileio.adm.adm import ADM
from ...fileio.adm.xml import default_screen
from ...fileio.adm.exceptions import AdmError, AdmFormatRefError
from ...fileio.adm.elements import (AudioProgramme, AudioContent, AudioObject,
                                    AudioPackFormat, AudioChannelFormat,
                                    Frequency, TypeDefinition,
                                    )
from .pack_allocation import allocate_packs, AllocationPack, AllocationChannel, AllocationTrack
from .utils import in_by_id, object_paths_from, pack_format_paths_from
from .validate import (validate_structure, validate_selected_audioTrackUID,
                       possible_reference_errors,
                       )
from ..metadata_input import (ExtraData, ADMPath, MetadataSourceIter,
                              RenderingItem, ObjectTypeMetadata,
                              ObjectRenderingItem, DirectSpeakersTypeMetadata,
                              DirectSpeakersRenderingItem, HOATypeMetadata,
                              HOARenderingItem, ImportanceData, TrackSpec,
                              DirectTrackSpec, SilentTrackSpec,
                              MatrixCoefficientTrackSpec, MixTrackSpec
                              )


@attrs(slots=True)
class _ItemSelectionState(object):
    """Represents the currently selected parts of the ADM.

    The general approach here is that each step in the algorithm takes a state
    and either returns or yields new copies of that state, with some extra
    information set. Making copies ensures that the algorithm is stateless --
    there's no way for data to "flow back" between steps.

    This is done rather than passing the state around explicitly as the early
    results (e.g. the programme/content/objects) are required at the end when
    we're generating the rendering items. This approach reduces coupling
    between the steps, as the interface for each step can stay the same even if
    the data it requires/produces changes.
    """
    adm = attrib(validator=instance_of(ADM))

    # programme/content/object hierarchy, set by _select_programme_content_objects
    #
    # After selecting these, audioObjects is None if there are no audioObjects
    # (meaning we will operate in CHNA-only mode). audioProgramme and
    # audioContent are None if there are no audioProgrammes (meaning we will
    # operate on all audioObjects or in CHNA-only mode).
    audioProgramme = attrib(default=None,
                            validator=optional(instance_of(AudioProgramme)))
    audioContent = attrib(default=None,
                          validator=optional(instance_of(AudioContent)))
    # path through audioObjects from audioContent to the audioObject which
    # contains the content to render
    audioObjects = attrib(default=None,
                          validator=optional(list_of(AudioObject)))

    # complete selected pack format with a track allocated to each channel, set
    # by _PackAllocator.select_pack_mapping
    #
    # the 'root' pack format -- the pack format which contains exactly the
    # selected channels to render.
    audioPackFormat = attrib(default=None,
                             validator=optional(instance_of(AudioPackFormat)))
    # a list of (AudioChannelFormat, TrackSpec) connecting each channel in
    # audioPackFormat to a source of samples
    channel_allocation = attrib(default=None,
                                validator=optional(instance_of(list)))

    # selection of a single channel within a pack format, set by
    # _select_single_channel from _get_rendering_items, depending on the type.
    #
    # audioPackFormat_path is the path from audioPackFormat (the root pack
    # format) to audioChannelFormat
    audioPackFormat_path = attrib(default=None,
                                  validator=optional(list_of(AudioPackFormat)))
    # the selected channel format
    audioChannelFormat = attrib(default=None,
                                validator=optional(instance_of(AudioChannelFormat)))
    # the source of samples for this channel
    track_spec = attrib(default=None,
                        validator=optional(instance_of(TrackSpec)))

    @property
    def audioObject(self):
        """The primary audioObject of this track (the last one in the chain), or None"""
        return self.audioObjects[-1] if self.audioObjects is not None else None


def _select_programme(state, audio_programme=None):
    """Select an audioProgramme to render.

    If audio_programme_id is provided, use that to make the selection,
    otherwise select the only audioProgramme, or the one with the lowest id.

    Parameters:
        state (_ItemSelectionState): 'adm' must be set.
        audio_programme (AudioProgramme): audioProgramme to select if there are
            multiple programmes.

    Returns:
        _ItemSelectionState: state with audioProgramme set if one is found, None otherwise.
    """
    if audio_programme is None:
        if len(state.adm.audioProgrammes) > 1:
            warnings.warn("more than one audioProgramme; selecting the one with the lowest id")
            return evolve(state,
                          audioProgramme=min(state.adm.audioProgrammes, key=lambda programme: programme.id))
        elif len(state.adm.audioProgrammes) == 1:
            return evolve(state, audioProgramme=state.adm.audioProgrammes[0])
        else:
            return evolve(state, audioProgramme=None)
    else:
        assert in_by_id(audio_programme, state.adm.audioProgrammes), "selected audioProgramme not in ADM."

        return evolve(state, audioProgramme=audio_programme)


def _select_content(state):
    """Select an audioContent to render.

    Parameters:
        state (_ItemSelectionState): 'audioProgramme' must be set if the
            programme/content/object structure is to be used.

    Yields:
        _ItemSelectionStates with audioContent set to the audioContents in the
        audioProgramme, or None if no programme/content/object structure is
        being used.
    """
    if state.audioProgramme is not None:
        for audioContent in state.audioProgramme.audioContents:
            yield evolve(state, audioContent=audioContent)
    else:
        yield state


def _root_objects(adm):
    """Get all audioObjects which are not sub-objects of another audioObject.

    All audioObjects will be sub-objects of the yielded audioObjects, as long
    as there are no loops in the audioObject nesting -- see
    _validate_object_loops.
    """
    non_root_objects = set(id(subObject)
                           for audioObject in adm.audioObjects
                           for subObject in audioObject.audioObjects)

    for audioObject in adm.audioObjects:
        if id(audioObject) not in non_root_objects:
            yield audioObject


def _select_root_objects(state):
    """Get the root objects to search from.

    If an audioContent is selected, then select all objects referenced from
    that, otherwise select all root audioObject; see _root_objects.

    Parameters:
        state (_ItemSelectionState): 'audioContent' must be set if the
            programme/content/object structure is to be used.

    Yields:
        AudioObject
    """
    if state.audioContent is not None:
        for audioObject in state.audioContent.audioObjects:
            yield audioObject
    else:
        for audioObject in _root_objects(state.adm):
            yield audioObject


def _select_object_paths(state):
    """Select audioObject paths.

    Parameters:
        state (_ItemSelectionState): 'audioContent' must be set if the
            programme/content/object structure is to be used.

    Yields:
        _ItemSelectionState: states with audioObjects set
    """
    for root_object in _select_root_objects(state):
        for object_path in object_paths_from(root_object):
            yield evolve(state, audioObjects=object_path)


def _select_programme_content_objects(state, audio_programme=None):
    """Select the audioProgramme/audioContent/audioObjects structure.

    If the ADM has any audioProgrammes or audioObjects, then
    `_select_programme`, `_select_content` and `_select_object_paths` are used,
    otherwise state is used unchanged, causing all tracks to be used.

    Parameters:
        state (_ItemSelectionState): state with `adm` set.

    Yields:
        _ItemSelectionState: state with audioProgramme, audioContent and audioObjects set.
    """
    if state.adm.audioProgrammes or state.adm.audioObjects:
        state = _select_programme(state, audio_programme)
        for state in _select_content(state):
            for state in _select_object_paths(state):
                yield state
    else:
        yield state


def _select_complementary_objects(adm, selected_complementary_objects):
    """Select objects to ignore in order to implement complementary objects.

    Parameters:
        adm (ADM)
        selected_complementary_objects (list of AudioObject): Objects to select
            from each complementary group. If there is no entry for an object
            in a complementary object group, then the root is selected by default.

    Returns:
        list of AudioObject: objects to be ignored
    """
    root_objects = [root_object for root_object in adm.audioObjects
                    if root_object.audioComplementaryObjects]

    def objects_in_group(root_object):
        """All objects within a given complementary object group."""
        yield root_object
        for comp_audio_object in root_object.audioComplementaryObjects:
            yield comp_audio_object

    # check that selected objects are actually complementary. This is important
    # to prevent confusion between "selecting one object from a programme to
    # render" and "selecting a complementary object from a group".
    all_complementary = [comp_audio_object
                         for root_object in root_objects
                         for comp_audio_object in objects_in_group(root_object)]
    for selected_obj in selected_complementary_objects:
        if not in_by_id(selected_obj, all_complementary):
            raise AdmError("selected audioObject {selected_obj.id} is not part "
                           "of any complementary audioObject group".format(
                               selected_obj=selected_obj,
                           ))

    # list of selected objects with defaults applied. If no object in a group
    # is explicitly selected then the root object in the group is
    all_selected = selected_complementary_objects[:]
    for root_object in root_objects:
        if not any(in_by_id(complementary_object, selected_complementary_objects)
                   for complementary_object in objects_in_group(root_object)):
            all_selected.append(root_object)

    # produce a list of unselected objects to ignore, and check for multiple
    # selected in each group
    not_selected = []
    for root_object in root_objects:
        selected = []
        for complementary_object in objects_in_group(root_object):
            if in_by_id(complementary_object, all_selected):
                selected.append(complementary_object)
            else:
                not_selected.append(complementary_object)

        assert selected
        if len(selected) > 1:
            raise AdmError("multiple audioObjects selected from complementary "
                           "object group '{root_object.id}': {ids}".format(
                               root_object=root_object,
                               ids=', '.join("'{ao.id}'".format(ao=ao) for ao in selected),
                           ))

    return not_selected


def _select_only_selected_complementary(state, objects_to_ignore):
    """Select only states which do not contain any ignored audioObjects"""
    if (state.audioObjects is None or
            not any(in_by_id(audio_object, objects_to_ignore)
                    for audio_object in state.audioObjects)):
        yield state


class _PackAllocator(object):
    """Object which can allocate audioTrackUIDs to channels in pack formats
    within either an audioObject or a CHNA-only ADM.

    This works by building a set of reference patterns to match against, where
    each pattern is a 'root' audioPackFormat and a list of audioChannelFormats,
    each with a list of possible audioPackFormats which could be referenced in
    the audioTrackUID which references it.

    These patterns are matched against the audioPackFormat references (in an
    audioObject) and audioTrackUIDs (in either an audioObject or CHNA-only ADM)
    by pack_allocation.allocate_packs.

    Once an allocation has been found it determines the real audioPackFormat
    and track/channel allocation to be used for rendering. For most types this
    is the same as the matched pattern, but for matrix types the mapping is
    more complex.

    To achieve this, the pack_allocation.Allocation* classes which are used to
    specify the patterns are subclassed to allow them to store information
    about this mapping. The 'input' allocation being the result of the pattern
    match, and the 'output' pack/allocation being the pack and track/channel
    allocation for the renderer.

    In RegularAllocationPack (used for normal types) this is a direct mapping,
    but in MatrixAllocationPack the output pack follows the outputPackFormat
    reference, and the output channel allocation performs a search from the
    channels of the output format back to the channels referenced by the
    selected audioTrackUIDs.
    """

    @attrs
    class AllocationTrackUID(AllocationTrack):
        """Extended AllocationTrack to hold the real track UID"""
        track_uid = attrib()

    class OutputAllocationPack(AllocationPack):
        """Subclasses of AllocationPack which allow overriding of the pack and
        channel allocation used to form the rendering items when the pack has
        been allocated to some channels.

        Attributes:
            output_pack (AudioPackFormat): specifies the pack to use in the rendering item
        """
        def output_channel_allocation(self, input_allocation):
            """Get the channel allocation within output_pack to be used to for
            rendering items.

            Parameters:
                input_allocation (list of (AllocationChannel, AllocationTrackUID or None)):
                    allocation of the input channels as returned by allocate_packs

            Returns:
                list of (AudioChannelFormat, TrackSpec): allocation of channels
                    in output_pack to tracks suitable for
                    _ItemSelectionState.channel_allocation
            """
            raise NotImplementedError("called abstract method")  # pragma: no cover

    @attrs
    class RegularAllocationPack(OutputAllocationPack):
        """OutputAllocationPack used for non-matrix packs; output_pack is
        root_pack and output_channel_allocation corresponds to
        input_allocation.
        """
        @property
        def output_pack(self):
            return self.root_pack

        def output_channel_allocation(self, input_allocation):
            return [(channel.channel_format, _PackAllocator.get_track_spec(track))
                    for channel, track in input_allocation]

    @attrs
    class MatrixAllocationPack(OutputAllocationPack):
        """OutputAllocationPack used for both matrix types (encode/decode), and
        all usage types (pre-applied, direct/decode, encode then decode).

        root_pack is the direct or decode matrix, so output_pack is the
        outputPackFormat which it refers to.

        The output channel allocation works by starting at the channels of the
        direct/decode matrix and recursively following inputChannelFormats in
        the matrix element until it gets to a channels in the input channel
        allocation, and building the track specs on the way back up.
        """
        @property
        def output_pack(self):
            return self.root_pack.outputPackFormat

        def output_channel_allocation(self, input_allocation):
            def get_track_spec(channel_format):
                # base case: if this is a channel in the input, return its track spec
                for alloc_channel, alloc_track in input_allocation:
                    if alloc_channel.channel_format is channel_format:
                        return _PackAllocator.get_track_spec(alloc_track)

                # recursive case: this must be a matrix type; apply the matrix
                # coefficients to the track specs of their input channels and
                # mix them together
                [block_format] = channel_format.audioBlockFormats
                return MixTrackSpec([
                    MatrixCoefficientTrackSpec(get_track_spec(coeff.inputChannelFormat), coeff)
                    for coeff in block_format.matrix])

            def get_channel_allocation(matrix_channel):
                [block_format] = matrix_channel.audioBlockFormats
                return (block_format.outputChannelFormat, get_track_spec(matrix_channel))

            return [get_channel_allocation(channel) for channel in self.root_pack.audioChannelFormats]

    def __init__(self, adm):
        self.packs = list(self.get_wrapped_packs(adm))

    def get_wrapped_packs(self, adm):
        """Wrap the audioPackFormats in adm in OutputAllocationPack instances
        which will be allocated to the audioObjects and audioTrackUIDs by the
        pack allocator. This is what controls the effect of the possible
        format referencing structures, particularly for Matrix.
        """

        for audioPackFormat in adm.audioPackFormats:
            if audioPackFormat.type != TypeDefinition.Matrix:
                yield self.wrap_non_matrix_pack(audioPackFormat)
            else:
                for wrapped_pack in self.wrap_matrix_pack(audioPackFormat):
                    yield wrapped_pack

    def wrap_non_matrix_pack(self, audioPackFormat):
        return self.RegularAllocationPack(
            root_pack=audioPackFormat,
            channels=[AllocationChannel(channel_format=channel_format, pack_formats=pack_formats)
                      for pack_formats in pack_format_paths_from(audioPackFormat)
                      for channel_format in pack_formats[-1].audioChannelFormats]
        )

    def wrap_matrix_pack(self, audioPackFormat):
        from . import matrix

        if matrix.type_of(audioPackFormat) in (matrix.Type.DIRECT, matrix.Type.DECODE):
            # direct or decoding matrix use. audioPackFormat refs point at the
            # direct or decode matrix pack (audioPackFormat), and the tracks
            # reference the channels of the inputPackFormat (for direct) or
            # encodePackFormat (for decode)

            input_pack = matrix.input_pack_format(audioPackFormat)
            input_channels = [AllocationChannel(channel_format=channel_format,
                                                pack_formats=[audioPackFormat])
                              for pack_formats in pack_format_paths_from(input_pack)
                              for channel_format in pack_formats[-1].audioChannelFormats]

            yield self.MatrixAllocationPack(
                root_pack=audioPackFormat,
                channels=input_channels,
            )

            # pre-applied matrix use. audioPackFormat refs and tracks point at
            # the direct or decode matrix pack (audioPackFormat) and the
            # channels thereof.

            yield self.MatrixAllocationPack(
                root_pack=audioPackFormat,
                channels=[AllocationChannel(channel_format=channel_format, pack_formats=pack_formats)
                          for pack_formats in pack_format_paths_from(audioPackFormat)
                          for channel_format in pack_formats[-1].audioChannelFormats]
            )

        if matrix.type_of(audioPackFormat) == matrix.Type.DECODE:
            # encode-then-decode matrix use. Tracks point at encode
            # audioPackFormat and the channels of its inputPackFormat, while
            # audioObjects refer to the decode pack.

            [encode_pack] = audioPackFormat.encodePackFormats

            input_pack = encode_pack.inputPackFormat
            input_channels = [AllocationChannel(channel_format=channel_format,
                                                pack_formats=[encode_pack])
                              for pack_formats in pack_format_paths_from(input_pack)
                              for channel_format in pack_formats[-1].audioChannelFormats]

            yield self.MatrixAllocationPack(
                root_pack=audioPackFormat,
                channels=input_channels)

    @classmethod
    def channel_format_for_track_uid(cls, audioTrackUID):
        return (audioTrackUID
                .audioTrackFormat
                .audioStreamFormat
                .audioChannelFormat)

    def get_selected_packs_tracks_silent(self, state):
        """Get the audioPackFormats, audioTrackUIDs and silent tracks
        referenced by the current state.

        If an object is selected, the packs and tracks and silent tracks are
        those referenced by it. Otherwise all audioTrackUIDs are returned, with
        no packs or silent tracks.
        """
        if state.audioObject is not None:
            obj = state.audioObject
            real_track_uids = [atu for atu in obj.audioTrackUIDs if atu is not None]
            silent_tracks = len(obj.audioTrackUIDs) - len(real_track_uids)

            return obj.audioPackFormats, real_track_uids, silent_tracks
        else:
            return None, state.adm.audioTrackUIDs, 0

    @classmethod
    def get_track_spec(cls, allocation_track_uid):
        if allocation_track_uid is not None:
            return DirectTrackSpec(allocation_track_uid.track_uid.trackIndex - 1)
        else:
            return SilentTrackSpec()

    @classmethod
    def raise_error(cls, state, selected_packs, selected_tracks, num_silent_tracks, error_type):
        """Error helper for select_pack_mapping"""
        context = ("audioObject {audioObject.id}".format(audioObject=state.audioObject)
                   if state.audioObject is not None
                   else "CHNA")

        message = "{error_type} format references found in {context}".format(
            error_type=error_type,
            context=context,
        )

        possible_errors = list(possible_reference_errors(selected_packs,
                                                         selected_tracks,
                                                         num_silent_tracks))

        raise AdmFormatRefError(message, possible_errors)

    def select_pack_mapping(self, state):
        """Select pack formats and the allocation of tracks to channels within them.

        Parameters:
            state (_ItemSelectionState): state with programme/content/object
                selected if not in CHNA-oly ADM.

        Yields:
            state with audioPackFormat and channel_allocation set
        """
        selected_packs, selected_tracks, num_silent_tracks = self.get_selected_packs_tracks_silent(state)

        for track in selected_tracks:
            validate_selected_audioTrackUID(track)

        tracks = [self.AllocationTrackUID(channel_format=self.channel_format_for_track_uid(track),
                                          pack_format=track.audioPackFormat,
                                          track_uid=track)
                  for track in selected_tracks]

        # try to get up to 2 possible solutions
        solutions = allocate_packs(self.packs, tracks, selected_packs, num_silent_tracks)
        solution = next(solutions, None)
        alt_solution = next(solutions, None)

        if solution is not None and alt_solution is None:
            for pack in solution:
                yield evolve(state,
                             audioPackFormat=pack.pack.output_pack,
                             channel_allocation=pack.pack.output_channel_allocation(pack.allocation),
                             )
        else:
            self.raise_error(state, selected_packs, selected_tracks, num_silent_tracks,
                             "Conflicting" if solution is None else "Ambiguous")


def _get_importance(state):
    """Get importance data for a state.

    Parameters:
        state (_ItemSelectionState): `audioObjects` and `audioPackFormats` are used.

    Returns:
        ImportanceData: the minimum importance along the audio object path and
        the audio pack format path.
    """
    def importance_sort_key(importance):
        """No importance value implies maximum importance."""
        return np.inf if importance is None else importance

    return ImportanceData(
        audio_object=(min((obj.importance for obj in state.audioObjects),
                          key=importance_sort_key)
                      if state.audioObjects is not None
                      else None),
        audio_pack_format=min((pack.importance for pack in state.audioPackFormat_path),
                              key=importance_sort_key)
    )


def _get_adm_path(state):
    """Get the path through the ADM used to get to a single track/channel."""
    return ADMPath(
        audioProgramme=state.audioProgramme,
        audioContent=state.audioContent,
        audioObjects=state.audioObjects,
        audioPackFormats=state.audioPackFormat_path,
        audioChannelFormat=state.audioChannelFormat,
    )


def _get_extra_data(state):
    """Get an ExtraData object for this track/channel with extra information
    from the programme/object/channel needed for rendering."""
    return ExtraData(
        object_start=(state.audioObject.start
                      if state.audioObject is not None
                      else None),
        object_duration=(state.audioObject.duration
                         if state.audioObject is not None
                         else None),
        reference_screen=(state.audioProgramme.referenceScreen
                          if state.audioProgramme is not None
                          else default_screen),
        channel_frequency=(state.audioChannelFormat.frequency
                           if state.audioChannelFormat is not None
                           else Frequency()),
    )


def _get_pack_format_path(audioPackFormat, audioChannelFormat):
    """Get the pack formats along the path from a pack format to a channel format."""
    [found_path] = [path for path in pack_format_paths_from(audioPackFormat)
                    if in_by_id(audioChannelFormat, path[-1].audioChannelFormats)]

    return found_path


def _select_single_channel(state):
    """Select the audioPackFormat path, audioChannelFormat and audioTrackUID
    for single channels within the pack.
    """
    for audioChannelFormat, track_spec in state.channel_allocation:
        yield evolve(state,
                     audioPackFormat_path=_get_pack_format_path(state.audioPackFormat, audioChannelFormat),
                     audioChannelFormat=audioChannelFormat,
                     track_spec=track_spec,
                     )


def _get_RenderingItems_Objects(state):
    """Get a RenderingItem for each selected Objects channel."""
    for state in _select_single_channel(state):
        extra_data = _get_extra_data(state)
        importance = _get_importance(state)
        adm_path = _get_adm_path(state)

        metadata_source = MetadataSourceIter([ObjectTypeMetadata(block_format=block_format,
                                                                 extra_data=extra_data)
                                              for block_format in state.audioChannelFormat.audioBlockFormats])

        yield ObjectRenderingItem(track_spec=state.track_spec,
                                  metadata_source=metadata_source,
                                  importance=importance,
                                  adm_path=adm_path,
                                  )


def _get_RenderingItems_DirectSpeakers(state):
    """Get a RenderingItem for each selected DirectSpeakers channel."""
    for state in _select_single_channel(state):
        extra_data = _get_extra_data(state)
        importance = _get_importance(state)
        adm_path = _get_adm_path(state)

        metadata_source = MetadataSourceIter([DirectSpeakersTypeMetadata(block_format=block_format,
                                                                         audioPackFormats=state.audioPackFormat_path,
                                                                         extra_data=extra_data)
                                              for block_format in state.audioChannelFormat.audioBlockFormats])

        yield DirectSpeakersRenderingItem(track_spec=state.track_spec,
                                          metadata_source=metadata_source,
                                          importance=importance,
                                          adm_path=adm_path,
                                          )


def _get_RenderingItems_HOA(state):
    """Get a HOARenderingItem given an _ItemSelectionState."""
    from .hoa import (get_single_param, get_per_channel_param,
                      get_nfcRefDist, get_screenRef, get_normalization,
                      get_order, get_degree, get_rtime, get_duration)

    states = list(_select_single_channel(state))

    pack_paths_channels = [(state_single.audioPackFormat_path, state_single.audioChannelFormat)
                           for state_single in states]

    type_metadata = HOATypeMetadata(
        rtime=get_single_param(pack_paths_channels, "rtime", get_rtime),
        duration=get_single_param(pack_paths_channels, "duration", get_duration),
        orders=get_per_channel_param(pack_paths_channels, get_order),
        degrees=get_per_channel_param(pack_paths_channels, get_degree),
        normalization=get_single_param(pack_paths_channels, "normalization", get_normalization),
        nfcRefDist=get_single_param(pack_paths_channels, "nfcRefDist", get_nfcRefDist),
        screenRef=get_single_param(pack_paths_channels, "screenRef", get_screenRef),
        extra_data=_get_extra_data(state),
    )

    metadata_source = MetadataSourceIter([type_metadata])
    yield HOARenderingItem(track_specs=[state_single.track_spec for state_single in states],
                           metadata_source=metadata_source,
                           importances=[_get_importance(state_single) for state_single in states],
                           adm_paths=[_get_adm_path(state_single) for state_single in states],
                           )


def _get_rendering_items(state):
    if state.audioPackFormat.type == TypeDefinition.Objects:
        return _get_RenderingItems_Objects(state)
    elif state.audioPackFormat.type == TypeDefinition.DirectSpeakers:
        return _get_RenderingItems_DirectSpeakers(state)
    elif state.audioPackFormat.type == TypeDefinition.HOA:
        return _get_RenderingItems_HOA(state)
    else:
        raise NotImplementedError("Don't know how to produce rendering items for type {apf.type.name}".format(
            apf=state.audioPackFormat,
        ))


def select_rendering_items(adm,
                           audio_programme=None,
                           selected_complementary_objects=[]):
    """Select RenderingItems from an ADM structure.

    Parameters:
        adm (ADM): ADM to process
        audio_programme (Optional[AudioProgramme]): audioProgramme to select if
            there is more than one in adm.
        selected_complementary_objects (list[AudioObject]): Objects to select
            from each complementary group. If there is no entry for an object
            in a complementary object group, then the root is selected by
            default.

    Returns:
        list[RenderingItem]: selected rendering items
    """
    validate_structure(adm)

    pack_allocator = _PackAllocator(adm)

    objects_to_ignore = _select_complementary_objects(adm, selected_complementary_objects)

    state = _ItemSelectionState(adm=adm)

    rendering_items = []
    for state in _select_programme_content_objects(state, audio_programme):
        for state in _select_only_selected_complementary(state, objects_to_ignore):
            for state in pack_allocator.select_pack_mapping(state):
                for rendering_item in _get_rendering_items(state):
                    rendering_items.append(rendering_item)

    return rendering_items


class ObjectChannelMatcher(object):
    """Interface for using the _PackAllocator to find the audioChannelFormats
    referenced by audioObjects.

    This doesn't do anything special or interesting, but keeps the details of
    item selection inside this module.
    """

    def __init__(self, adm):
        self._adm = adm
        self._pack_allocator = _PackAllocator(adm)

    def get_channel_formats_for_object(self, audioObject):
        state = _ItemSelectionState(adm=self._adm, audioObjects=[audioObject])
        for state in self._pack_allocator.select_pack_mapping(state):
            for channelFormat, _track_spec in state.channel_allocation:
                yield channelFormat
