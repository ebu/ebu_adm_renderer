from attr import attrs, attrib, evolve
from .utils import in_by_id


@attrs
class AllocationChannel(object):
    """Represents a channel to allocate within an AllocationPack

    Attributes:
        channel_format (AudioChannelFormat): channel format to match with
            channel_format in AllocationTrack.
        pack_formats (list of AudioPackFormat): nested audioPackFormats which
            lead from the root audioPackFormat to this channel. pack_format in
            the AllocationTrack allocated to this channel must reference one of
            these.
    """
    channel_format = attrib()
    pack_formats = attrib()


@attrs
class AllocationPack(object):
    """Represents a complete audioPackFormat to be allocated.

    Attributes:
        root_pack (AudioPackFormat): the top level audioPackFormat which
            references all channels to be allocated.
        channels (list of AllocationChannel): channels to allocate within this
            pack, with the nested audioPackFormat structure which must be
            satisfied.
    """
    root_pack = attrib()
    channels = attrib()


@attrs
class AllocationTrack(object):
    """Represents a track to be allocated.

    Attributes:
        channel_format (AudioChannelFormat): channelFormat referenced indirectly by this track.
        pack_format (AudioPackFormat): packFormat referenced by this track.
    """
    channel_format = attrib()
    pack_format = attrib()


@attrs
class AllocatedPack(object):
    """Represents an allocated pack format with the resulting association
    between channels and tracks.

    Attributes:
        pack (AllocationPack): referenced to the allocated pack for these
            channels; note that it's the AllocationPack not the AudioPackFormat
            which is referenced to allow for packs to be duplicated with
            different sets of channels to allocate (for matrix).
        allocation (list of (AllocationChannel, AllocationTrack or None)):
            association between the channels in this pack, and the tracks that
            have been allocated to them. None in place of the AllocationTrack
            indicates that a silent track has been associated with a channel.
    """
    pack = attrib()
    allocation = attrib()


def allocate_packs(packs,
                   tracks,
                   pack_refs,
                   num_silent_tracks):
    """Allocate tracks to channels and packs. This is intended to be used on a
    subset of tracks referenced by an audioObject, or on all tracks if there is
    no programme/content/object hierarchy.

    It takes information about the existing pack/channel structures
    (in `packs`), the tracks to allocate (`tracks`), the
    pack references if they exist (`pack_refs`), and the number of silent tracks
    available (`num_silent_tracks`), and yields all possible allocations, which
    are lists of AllocatedPack objects containing a reference to the root
    audioPackFormat and an association between channels and tracks.

    Each possible allocation meets the following requirements:

    - For each `AllocatedPack`, each channel in the `AllocationPack` occurs
      exactly once in `allocation`.

    - Each track in `tracks` occurs exactly once in the allocation.

    - The number of silent tracks referenced in the output is equal to
      `num_silent_tracks`.

    - For each associated `AllocationChannel channel` and `AllocationTrack track`,
      `track.channel_format` is `channel.channel_format`, and `track.pack_format`
      is in `channel.pack_formats`.

    - If `pack_refs` is not `None`, then there is a one-to-one correspondence
      between `pack_refs` and the values of `pack.pack.root_pack` for each
      `AllocatedPack pack`.

    Note that this operates on abstract ADM structures rather than the actual
    objects for simplicity; references to audioPackFormats and
    audioChannelFormats in the inputs are compared by identity.

    Parameters:
        packs (list of AllocationPack): audioPackFormats to allocate from, with
            their associated channels and nested audioPackFormat structures.
        tracks (list of AllocationTrack): tracks to allocate to packs, with
            references to the channel and pack formats referenced (indirectly)
            from the audioTrackUIDs. This should be a subset of the tracks --
            either just the tracks in an audioObject, or all tracks for a
            CHNA-only file.
        pack_refs (list of audioPackFormat or None): list of pack references to
            resolve. If None than they will be determined automatically; for
            allocation in audioObjects this should be populated with the
            audioPackFormat references in the audioObject; for CHNA-only files
            this should contain all tracks.
        num_silent_tracks (int): number of references to zero trackUIDs in the
            audioObject; should be 0 for CHNA-only use.

    Yields:
        lists of AllocatedPack; one list per possible solution. If there are no
        possible solutions then something was contradictory. If there is more
        than one solution then something was ambiguous.
    """
    tracks_inc_silent = tracks + [None] * num_silent_tracks
    return _allocate_packs_impl(packs,
                                tracks_inc_silent,
                                pack_refs,
                                [])


_EMPTY = object()


def _is_compatible(track, alloc_channel):
    """Is AllocationTrack (or None for silent) track compatible with AllocationChannel alloc_channel?"""
    return (track is None or
            (track.channel_format is alloc_channel.channel_format and
             in_by_id(track.pack_format, alloc_channel.pack_formats)))


def _allocate_packs_impl(packs,
                         tracks,
                         pack_refs,
                         partial_solution):
    """allocate_packs implementation -- see allocate_packs for interface

    partial_solution is the in-progress solution to add to -- a list of
    AllocatedPack in which allocation may contain _EMPTY in place of
    AllocationTrack | None

    Approximately, for each track we try to find either a channel in the
    partial solution to assign it to, or a channel in a new pack format, which
    is either a pack format in pack_refs if that exists, or any available pack
    otherwise. This function considers the possible allocations of the first
    track -- all possible solutions for all tracks are enumerated by recursion.

    The real tracks are considered before the silent tracks -- this way, by the
    time we get to a silent tracks there are only silent tracks left to
    allocate, so the silent tracks can just be allocated to the first empty
    channel found in an existing solution if there are any, or otherwise a new
    pack.
    """
    # Base case. If there are no tracks left to allocate, then we have either
    # finished successfully (if there are no remaining pack refs to allocate
    # and partial_solution is complete, then partial solution is a real
    # solution) or have finished unsuccessfully (partial_solution is not a real
    # solution)
    if not tracks:
        if ((pack_refs is None or not pack_refs) and
                all(track is not _EMPTY
                    for allocation in partial_solution
                    for (channel, track) in allocation.allocation)):
            yield partial_solution
        return

    remaining_in_partial = sum(1 for allocation in partial_solution
                               for (channel, track) in allocation.allocation
                               if track is _EMPTY)

    # Fail early if there are not enough remaining tracks to complete this
    # solution.
    if len(tracks) < remaining_in_partial:
        return

    def could_possibly_allocate(pack):
        """Might it be possible to allocate pack to the tracks?

        Allocation might not always succeed if this returns True, but will
        always fail if it returns False. If this returns False it is safe to
        discard this pack for all sub-calls.
        """
        # after all channels in the partial solution have been allocated, would
        # there be any left for this pack? `len(tracks) - remaining_in_partial`
        # always decreases in sub-calls, so this is safe
        if len(pack.channels) > len(tracks) - remaining_in_partial:
            return False

        # only packs in pack_refs can be allocated if specified. We only remove
        # from pack_refs, so this is safe.
        if pack_refs is not None and not in_by_id(pack.root_pack, pack_refs):
            return False

        # does each channel have a possible track? We only remove tracks in
        # sub-calls, so this is safe.
        n_found = 0
        for channel in pack.channels:
            if any(_is_compatible(possible_track, channel)
                   for possible_track in tracks):
                n_found += 1
        return n_found >= len(pack.channels)

    # filter out packs which couldn't possibly be allocated now or in any sub-calls.
    packs = [pack for pack in packs if could_possibly_allocate(pack)]

    def candidate_new_packs():
        """Possible new packs (to be added to the partial solution) which could
        be allocated.

        Yields:
            tuples of (pack_ref, remaining_pack_refs)

            pack_ref is the pack to try to allocate; remaining_pack_refs is the
            value of pack_refs for the next round
        """
        if pack_refs is not None:
            # try any pack which references a pack in pack_refs
            for pack in packs:
                for i, pack_ref in enumerate(pack_refs):
                    if pack_ref is pack.root_pack:
                        yield pack, pack_refs[:i] + pack_refs[i + 1:]
                        break
        else:
            # try any known pack
            for pack in packs:
                yield pack, None

    # try to allocate a pack/channel for the first track
    track, remaining_tracks = tracks[0], tracks[1:]

    def try_allocate(allocation):
        """Assign the current track to an appropriate channel in an allocation

        Channels are appropriate if there is no track assigned, and either the
        track is silent (therefore could belong to any channel) or if the track
        channel format and pack format refs match that of the channel.

        Returns:
            AllocatedPack or None: an updated copy of allocation if an
                appropriate track was found
        """
        for i, (alloc_channel, alloc_track) in enumerate(allocation.allocation):
            if alloc_track is _EMPTY and _is_compatible(track, alloc_channel):
                return evolve(allocation, allocation=(allocation.allocation[:i] +
                                                      [(alloc_channel, track)] +
                                                      allocation.allocation[i + 1:]))

    def candidate_partial_solutions():
        """Try assigning the track to an existing or new allocation. Yields an
        updated partial solution and the remaining track refs."""
        # try an existing allocation
        for i, existing_allocation in enumerate(partial_solution):
            new_allocation = try_allocate(existing_allocation)
            if new_allocation is not None:
                yield partial_solution[:i] + [new_allocation] + partial_solution[i + 1:], pack_refs
                # if track is silent, allocating it to any channel is
                # equivalent, and if it can be allocated to an existing channel
                # then it must be -- this prevents multiple equivalent
                # solutions being returned as we could start a new pack on any
                # silent track
                if track is None:
                    return

        # try allocating a new pack
        for pack, remaining_pack_refs in candidate_new_packs():
            empty_allocation = AllocatedPack(pack=pack,
                                             allocation=[(channel, _EMPTY) for channel in pack.channels])
            new_allocation = try_allocate(empty_allocation)
            if new_allocation is not None:
                yield partial_solution + [new_allocation], remaining_pack_refs

    for new_partial, remaining_pack_refs in candidate_partial_solutions():
        for soln in _allocate_packs_impl_obvious(packs, remaining_tracks, remaining_pack_refs, new_partial):
            yield soln


class _NotPossible(Exception):
    """Exception raised within _allocate_packs_obvious to break out if a track
    is found which cannot be allocated."""
    pass


def _allocate_packs_impl_obvious(packs,
                                 tracks,
                                 pack_refs,
                                 partial_solution):
    """Recursive step which allocates tracks to unallocated channels in
    the partial solution if there is only one possible track which could fill
    the gap. If there are unallocated channels which could not possibly be
    allocated then this solution is discarded.

    Use of this function means that the tricks used to reduce the search space
    in _allocate_packs_impl only need to be applied in cases which are actually
    ambiguous.
    """
    tracks = tracks[:]

    def allocate_channel(channel, allocated_track):
        if allocated_track is not _EMPTY:
            return allocated_track
        else:
            possible = [(i, track)
                        for i, track in enumerate(tracks)
                        if _is_compatible(track, channel)]

            if not possible:
                raise _NotPossible()
            # if there's only one possible track, or the only possible tracks
            # are silent (silent tracks come last and are equivalent), allocate
            # it now
            elif len(possible) == 1 or possible[0][1] is None:
                i, track = possible[0]
                del tracks[i]
                return track
            else:
                return _EMPTY

    def allocate_channels_in_pack(pack):
        return evolve(pack,
                      allocation=[(channel, allocate_channel(channel, allocated_track))
                                  for channel, allocated_track in pack.allocation])

    try:
        new_solution = [allocate_channels_in_pack(allocation)
                        for allocation in partial_solution]
    except _NotPossible:
        return

    for solution in _allocate_packs_impl(packs, tracks, pack_refs, new_solution):
        yield solution
