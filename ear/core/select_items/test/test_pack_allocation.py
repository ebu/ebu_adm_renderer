from ..pack_allocation import allocate_packs, AllocationPack, AllocationChannel, AllocationTrack, AllocatedPack
import pytest

p1, p2 = "p1", "p2"
c1, c2, c3, c4, c5 = "c1", "c2", "c3", "c4", "c5"


def allocation_eq(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(allocation_eq(ai, bi) for ai, bi in zip(a, b))
    if isinstance(a, AllocatedPack):
        return (a.pack is b.pack and
                len(a.allocation) == len(b.allocation) and
                all(channel_a is channel_b and track_a is track_b
                    for (channel_a, track_a), (channel_b, track_b) in zip(a.allocation, b.allocation)))
    assert False


@pytest.mark.parametrize("packs",
                         [
                             [AllocationPack(p1, [AllocationChannel(c1, [p1])])],
                             [AllocationPack(p1, [AllocationChannel(c1, [p1])]),
                              AllocationPack(p2, [AllocationChannel(c2, [p2])])],
                         ],
                         ids=["just used packs",
                              "bonus unused packs",
                              ])
@pytest.mark.parametrize("tracks,num_silent_tracks,expected_track",
                         [([AllocationTrack(c1, p1)], 0, lambda tracks: tracks[0]),
                          ([], 1, lambda tracks: None),
                          ],
                         ids=["one real track, no silent tracks",
                              "no real tracks, one silent track",
                              ])
def test_simple_one_track(packs, tracks, num_silent_tracks, expected_track):
    # one pack reference specified; one solution
    assert allocation_eq(
        list(allocate_packs(packs, tracks, [p1], num_silent_tracks)),
        [[AllocatedPack(packs[0], [(packs[0].channels[0], expected_track(tracks))])]])

    # two pack references specified, no solutions
    assert allocation_eq(
        list(allocate_packs(packs, tracks, [p1, p1], num_silent_tracks)),
        [])

    # zero pack references; no solution
    assert allocation_eq(
        list(allocate_packs(packs, tracks, [], num_silent_tracks)),
        [])

    # no pack references; one solution as long as there are no silent tracks
    if num_silent_tracks == 0:
        assert allocation_eq(
            list(allocate_packs(packs, tracks, None, num_silent_tracks)),
            [[AllocatedPack(packs[0], [(packs[0].channels[0], expected_track(tracks))])]])


@pytest.mark.parametrize("tracks",
                         [[AllocationTrack(c1, p2),
                           AllocationTrack(c2, p2),
                           AllocationTrack(c3, p2),
                           AllocationTrack(c4, p2),
                           AllocationTrack(c5, p2),
                           ],
                          [AllocationTrack(c1, p1),
                           AllocationTrack(c2, p1),
                           AllocationTrack(c3, p2),
                           AllocationTrack(c4, p2),
                           AllocationTrack(c5, p2),
                           ],
                          ],
                         ids=["tracks reference parent pack",
                              "tracks reference sub-pack",
                              ])
@pytest.mark.parametrize("num_silent_tracks", [0, 1, 2])
def test_nested(tracks, num_silent_tracks):
    packs = [
        AllocationPack(p1, [AllocationChannel(c1, [p1]),
                            AllocationChannel(c2, [p1])]),
        AllocationPack(p2, [AllocationChannel(c1, [p2, p1]),
                            AllocationChannel(c2, [p2, p1]),
                            AllocationChannel(c3, [p2]),
                            AllocationChannel(c4, [p2]),
                            AllocationChannel(c5, [p2])]),
    ]

    expected_allocation = list(zip(packs[1].channels, tracks))

    # edit out silent tracks
    tracks = tracks[:2] + tracks[2 + num_silent_tracks:]
    for i in range(num_silent_tracks):
        expected_allocation[2 + i] = (expected_allocation[2 + i][0], None)

    expected = [AllocatedPack(packs[1], expected_allocation)]

    # one correct pack reference; one solution
    assert allocation_eq(
        list(allocate_packs(packs, tracks, [p2], num_silent_tracks)),
        [expected])

    # no pack references; one solution. Note that cases there num_silent_tracks
    # > 0 never happen in real use, as the CHNA chunk doesn't specify silent
    # tracks.
    assert allocation_eq(
        list(allocate_packs(packs, tracks, None, num_silent_tracks)),
        [expected])

    # zero pack references; no solution
    assert allocation_eq(
        list(allocate_packs(packs, tracks, [], num_silent_tracks)),
        [])

    # reference to sub-pack; no solution
    assert allocation_eq(
        list(allocate_packs(packs, tracks, [p1], num_silent_tracks)),
        [])


def test_multiple_identical_mono():
    """Check that when there are multiple mono tracks only one solution is given"""
    packs = [
        AllocationPack(p1, [AllocationChannel(c1, [p1]),
                            AllocationChannel(c2, [p1])]),
        AllocationPack(p2, [AllocationChannel(c1, [p2])]),
    ]

    tracks = [
        AllocationTrack(c1, p2),
        AllocationTrack(c1, p2),
    ]

    # two identical mono tracks
    expected = [AllocatedPack(packs[1], [(packs[1].channels[0], tracks[0])]),
                AllocatedPack(packs[1], [(packs[1].channels[0], tracks[1])])]
    assert allocation_eq(
        list(allocate_packs(packs, tracks, [p2, p2], 0)),
        [expected])

    # two identical silent mono tracks
    expected = [AllocatedPack(packs[1], [(packs[1].channels[0], None)]),
                AllocatedPack(packs[1], [(packs[1].channels[0], None)])]
    assert allocation_eq(
        list(allocate_packs(packs, [], [p2, p2], 2)),
        [expected])

    # one real, one silent
    expected = [AllocatedPack(packs[1], [(packs[1].channels[0], tracks[0])]),
                AllocatedPack(packs[1], [(packs[1].channels[0], None)])]
    assert allocation_eq(
        list(allocate_packs(packs, tracks[:1], [p2, p2], 1)),
        [expected])

    # chna-only case
    expected = [AllocatedPack(packs[1], [(packs[1].channels[0], tracks[0])]),
                AllocatedPack(packs[1], [(packs[1].channels[0], tracks[1])])]
    assert allocation_eq(
        list(allocate_packs(packs, tracks, None, 0)),
        [expected])

    # duplicate stereo is still ambiguous
    tracks = [
        AllocationTrack(c1, p1),
        AllocationTrack(c2, p1),
        AllocationTrack(c1, p1),
        AllocationTrack(c2, p1),
    ]
    assert len(list(allocate_packs(packs, tracks, [p1, p1], 0))) == 2
    assert len(list(allocate_packs(packs, tracks, None, 0))) == 2


@pytest.mark.parametrize("channels", [[c1], [c1, c2]],
                         ids=["mono", "stereo"])
@pytest.mark.parametrize("silent", [True, False])
def test_many_packs(channels, silent):
    """Test allocating lots of packs, to check that it's not unreasonably slow."""
    packs = [
        AllocationPack(p1, [AllocationChannel(channel, [p1])
                            for channel in channels]),
    ]

    n_pack_refs = 100

    pack_refs = [p1] * n_pack_refs
    if silent:
        tracks = []
        num_silent = len(channels) * n_pack_refs
    else:
        tracks = [AllocationTrack(channel, p1)
                  for i in range(n_pack_refs)
                  for channel in channels]
        num_silent = 0

    res = allocate_packs(packs, tracks, pack_refs, num_silent)
    res1 = next(res, None)
    res2 = next(res, None)

    assert res1 is not None
    # stereo with real tracks is ambiguous as there are many possible assignments
    if len(channels) > 1 and not silent:
        assert res2 is not None
    else:
        assert res2 is None


@pytest.mark.parametrize("chna_only", [False, True])
def test_lots_of_channels(chna_only):
    """Check that allocating lots of channels completes in a reasonable ammount
    of time."""
    channels = ["c{}".format(i) for i in range(100)]
    packs = [
        AllocationPack(p1, [AllocationChannel(channel, [p1])
                            for channel in channels]),
        AllocationPack(p2, [AllocationChannel(channel, [p2])
                            for channel in channels]),
    ]

    pack_refs = [p1, p2]

    tracks = [AllocationTrack(channel, pack)
              for pack in [p1, p2]
              for channel in channels]

    res = allocate_packs(packs, tracks, None if chna_only else pack_refs, 0)
    res1 = next(res, None)
    res2 = next(res, None)

    assert res1 is not None
    assert res2 is None
