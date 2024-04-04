from .pack_allocation import AllocatedPack, _is_compatible
from .utils import index_by_id


def allocate_packs(packs, tracks, pack_refs, num_silent_tracks):
    """alternative implementation of pack_allocation.allocate_packs

    this has the same interface and should produce the same results, but is
    implemented in a different way, to hopefully have different bugs for
    automated testing
    """

    # The overall strategy used is to iterate over all combinations of possible
    # packs to allocate, and all possible track orders, and yield allocations
    # for the ones which are valid. The correctness relies on both these loops
    # (combinations of packs and track orders) producing only unique elements,
    # so as not to produce duplicate solutions.

    def get_track(i):
        return None if i is None else tracks[i]

    for alloc_packs in pack_subsets(packs, pack_refs, len(tracks) + num_silent_tracks):
        # When finding an order for the tracks, and there are repeated packs,
        # we must not find orders which just have the tracks assigned to
        # repeated packs switched. For example, if there are two identical
        # stereo packs and 4 tracks:
        #
        # alloc_packs = [p1(c1, c2), p1(c1, c2)]
        # tracks = [t1(c1), t2(c2), t3(c1), t4(c2)]
        #
        # Then the following channel orders are equivalent, because the tracks
        # in the identical packs are just swapped around:
        #
        # a: [t1(c1), t2(c2), t3(c1), t4(c2)]
        # b: [t3(c1), t4(c2), t1(c1), t2(c2)]
        #
        # The following two are also equivalent to each other, but not
        # equivalent to the above two:
        #
        # c: [t1(c1), t4(c2), t3(c1), t2(c2)]
        # d: [t3(c1), t2(c2), t1(c1), t4(c2)]
        #
        # So, we only want to test one from each of these pairs (say, a and c),
        # and a way to do that is to test only allocations where the tracks for
        # repeated packs incense lexicographically. a is chosen because
        # [1, 2] < [3, 4], and c is chosen because [1, 4] < [3, 2].
        #
        # This also works when there are silent tracks, assuming that silent
        # tracks are equal, and sorted after any real tracks.
        #
        # Note that because tracks are unique, when we are sequentially
        # allocating tracks, we only have to consider this lexicographic order
        # requirement when all tracks before the current channel in the
        # previous identical pack are silent. For example, if we have:
        #
        # alloc_packs = [p1(c1, c2), p1(c1, c2)]
        # tracks = [t1(c1), t2(c2), None, None]
        #
        # the following orders are possible
        #
        # a: [t1(c1), t2(c2), None, None]
        # b: [None, None, t1(c1), t2(c2)]
        # c: [t1(c1), None, None, t2(c2)]
        # d: [None, t2(c2), None, t1(c1)]
        #
        # only a and c meet the lexicographic requirement
        #
        # b is rejected when allocating t1, because the first 0 tracks of the
        # first pack (i.e. the empty list) are all None, and t1 is ordered
        # before None (the first track in the second pack)
        #
        # d is rejected when allocating t1, because the first 1 tracks of the
        # first pack (i.e. [None]) are all None, and t1 is ordered before t2
        # (the second track in the first pack)

        # This works in general because if the first n channels of the first
        # pack are None, the first n channels of the second one will be too, as
        # long as the order constraint is not violated in the previous step.
        #
        # So, ultimately we find a mapping here from the channel number in the
        # allocation to the channel numbers in the previous pack to check, and
        # use that to do the above checks.

        prev_same_pack_slice = {}
        pack_to_channel_index = {}

        pack_channel_i = 0
        for pack in alloc_packs:
            if id(pack) in pack_to_channel_index:
                for channel_i, channel in enumerate(pack.channels):
                    prev_pack_channel_i = pack_to_channel_index[id(pack)]

                    prev_slice = slice(
                        prev_pack_channel_i, prev_pack_channel_i + channel_i
                    )
                    prev_same_pack_slice[pack_channel_i + channel_i] = prev_slice

            pack_to_channel_index[id(pack)] = pack_channel_i
            pack_channel_i += len(pack.channels)

        channels = list(channels_in_packs(alloc_packs))

        def track_possible_at_position(partial_alloc, track_i):
            position = len(partial_alloc)

            if not _is_compatible(get_track(track_i), channels[position]):
                return False

            if position in prev_same_pack_slice:
                prev_slice = prev_same_pack_slice[position]

                # as above, if all channels before the current one in the
                # previous identical pack are None, then the allocation of this
                # track will determine if the tracks are in order or not
                if all(
                    prev_pack_track_i is None
                    for prev_pack_track_i in partial_alloc[prev_slice]
                ):
                    # yes, so this track must come after the corresponding one
                    # in the previous packs
                    alloc_after = partial_alloc[prev_slice.stop]

                    # only silent comes after silent
                    if alloc_after is None and track_i is not None:
                        return False

                    if track_i <= alloc_after:
                        return False

            return True

        for track_allocation_i in track_index_orders(
            len(tracks), num_silent_tracks, track_possible_at_position
        ):
            track_i_iter = iter(track_allocation_i)

            yield [
                AllocatedPack(
                    pack=pack,
                    allocation=[
                        (channel, get_track(next(track_i_iter)))
                        for channel in pack.channels
                    ],
                )
                for pack in alloc_packs
            ]


def channels_in_packs(alloc_packs):
    """given a list of AllocationPack, yield the AllocationChannels it contains
    in order
    """
    for alloc_pack in alloc_packs:
        for channel in alloc_pack.channels:
            yield channel


def track_index_orders(num_real_tracks, num_silent_tracks, track_possible_at_position):
    """all orders of the tracks (specified by number of real and silent) which
    are valid according to track_possible_at_position

    This will yield lists of track indices, which are either an integer
    refering to a track number, or None for a silent track

    track_possible_at_position will be called with a partial allocation and a
    track index to check if it's OK to append that track to the allocation
    """
    return track_index_orders_impl(
        [], list(range(num_real_tracks)), num_silent_tracks, track_possible_at_position
    )


def track_index_orders_impl(
    partial_alloc, tracks, num_silent_tracks, track_possible_at_position
):
    if not tracks and num_silent_tracks == 0:
        yield partial_alloc

    else:

        def pick_track_indices():
            for i, track in enumerate(tracks):
                if track_possible_at_position(partial_alloc, track):
                    yield track, tracks[:i] + tracks[i + 1 :], num_silent_tracks

            if num_silent_tracks:
                yield None, tracks, num_silent_tracks - 1

        for track, tracks_left, num_silent_tracks_left in pick_track_indices():
            yield from track_index_orders_impl(
                partial_alloc + [track],
                tracks_left,
                num_silent_tracks_left,
                track_possible_at_position,
            )


def all_pack_subsets(packs, tracks_left):
    """implementation of pack_subsets_with_refs for when there are no pack refs"""
    if tracks_left == 0:
        yield []
    elif packs:
        pack, *tail = packs

        n = tracks_left // len(pack.channels)

        yield from all_pack_subsets(tail, tracks_left)

        for i in range(1, n + 1):
            for tail_subset in all_pack_subsets(
                tail, tracks_left - i * len(pack.channels)
            ):
                yield [pack] * i + tail_subset


def pack_subsets_with_refs(packs, pack_refs, num_tracks):
    """implementation of pack_subsets_with_refs for when there are pack refs"""
    if not pack_refs and num_tracks == 0:
        # empty valid solution
        yield []
        return

    if not packs:
        # no packs to allocate
        return
    if not pack_refs:
        # no pack refs to allocate to
        return
    if not num_tracks:
        # no tracks left to allocate to
        return

    try_pack = packs[0]
    new_num_tracks = num_tracks - len(try_pack.channels)

    # try allocating this pack
    if new_num_tracks >= 0:
        pack_refs_idx = index_by_id(try_pack.root_pack, pack_refs)
        if pack_refs_idx is not None:
            new_pack_refs = pack_refs[:pack_refs_idx] + pack_refs[pack_refs_idx + 1 :]
            for tail_subset in pack_subsets_with_refs(
                packs, new_pack_refs, new_num_tracks
            ):
                yield [try_pack] + tail_subset

    # or skip it
    yield from pack_subsets_with_refs(packs[1:], pack_refs, num_tracks)


def pack_subsets(packs, pack_refs, num_tracks):
    """given the list of AllocationPacks, the pack references and total number
    of tracks, yield possible lists of packs to allocate

    this only yields lists of packs that are unique, i.e. not just re-orderings
    of each other
    """
    if pack_refs is None:
        return all_pack_subsets(packs, num_tracks)
    else:
        return pack_subsets_with_refs(packs, pack_refs, num_tracks)
