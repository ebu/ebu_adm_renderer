from ..pack_allocation import allocate_packs, AllocationPack, AllocationChannel, AllocationTrack, AllocatedPack
from ..pack_allocation_alternative import allocate_packs as allocate_packs_alt
from ..utils import index_by_id
import pytest


p1, p2, p3 = "p1", "p2", "p3"
c1, c2, c3, c4, c5 = "c1", "c2", "c3", "c4", "c5"


def pack_allocation_to_ids(pack: AllocatedPack):
    """turn an AllocatedPack into a structure of object IDs that can be
    compared/sorted normally"""
    return id(pack.pack), [
        (id(channel), id(track)) for channel, track in pack.allocation
    ]


def normalise_allocation(allocation):
    """normalise an allocation by sorting the packs, so that equal allocations
    are equal"""
    return sorted(allocation, key=pack_allocation_to_ids)


def normalise_allocations(allocations):
    """normalise a list of allocations, so that equal lists of allocations are
    equal"""
    normalised_allocations = [
        normalise_allocation(allocation) for allocation in allocations
    ]

    return sorted(
        normalised_allocations,
        key=lambda allocation: [pack_allocation_to_ids(pack) for pack in allocation],
    )


def allocations_eq(a, b):
    """are two allocations equal?"""
    return normalise_allocations(a) == normalise_allocations(b)


def allocate_packs_reverse(packs, tracks, pack_refs, num_silent_tracks):
    """call allocate_packs with reversed tracks, which should give the same
    result"""
    return allocate_packs(packs, tracks[::-1], pack_refs, num_silent_tracks)


# test these implementations against each other
default_implementations = [
    ("real", allocate_packs),
    ("reverse", allocate_packs_reverse),
    ("alternative", allocate_packs_alt),
]

fast_implementations = [
    (name, fn) for (name, fn) in default_implementations if name != "alternative"
]


def print_problem(allocation_args, indent):
    packs, tracks, pack_refs, num_silent = allocation_args

    def p(this_indent, s):
        print("  " * (indent + this_indent) + str(s))

    p(0, "packs:")
    for pack in packs:
        p(1, pack.root_pack)
        for channel in pack.channels:
            p(2, channel)
    p(0, "tracks:")
    for track in tracks:
        p(1, track)
    p(0, f"pack_refs: {pack_refs}")
    p(0, f"num_silent: {num_silent}")


def print_solution(allocation_args, soln, indent):
    packs, tracks, pack_refs, num_silent = allocation_args

    def p(this_indent, s):
        print("  " * (indent + this_indent) + str(s))

    for pack in soln:
        p(0, f"{index_by_id(pack.pack, packs)} {pack.pack.root_pack}")
        for channel, track in pack.allocation:
            p(1, f"channel {index_by_id(channel, pack.pack.channels)} {channel}")

            track_id = "silent" if track is None else index_by_id(track, tracks)
            p(2, f"track {track_id} {track}")


def check_allocation(
    allocation_args,
    count=None,
    expected=None,
    implementations=default_implementations,
):
    """given the arguments to allocate_packs (packs, tracks, pack_refs,
    num_silent_tracks), check the number of results (count) or actual results
    (expected) for all implementations, and check that all implementations
    return the same results
    """

    def check_result(impl_name, result):
        if count is not None:
            assert (
                len(result) == count
            ), f"{impl_name} returned the wrong number of results"
        if expected is not None:
            assert allocations_eq(
                result, expected
            ), f"{impl_name} returned an incorrect allocation"

        # TODO: check that the result actually meets the requirements, to
        # improve count-only tests

    results = []
    for impl_name, impl in implementations:
        result = list(impl(*allocation_args))

        results.append((impl_name, result))

    try:
        for impl_name, result in results:
            check_result(impl_name, result)

        first_impl_name, first_result = results[0]
        for impl_name, result in results[1:]:
            assert allocations_eq(first_result, result)

    except AssertionError as e:

        def first_matching_solution(to_find, results):
            for impl_name, result in results:
                if allocations_eq(result, to_find):
                    return impl_name

        print("problem:")
        print_problem(allocation_args, 1)
        for result_i, (impl_name, result) in enumerate(results):
            print(f"solutions for {impl_name}")
            matching = first_matching_solution(result, results[:result_i])
            if matching is not None:
                print(f"  same as {matching}")
            else:
                for i, soln in enumerate(result):
                    print(f"  {i}:")
                    print_solution(allocation_args, soln, 2)

        raise

    return results[0][1]


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
    check_allocation(
        (packs, tracks, [p1], num_silent_tracks),
        expected=[
            [AllocatedPack(packs[0], [(packs[0].channels[0], expected_track(tracks))])]
        ],
    )

    # two pack references specified, no solutions
    check_allocation((packs, tracks, [p1, p1], num_silent_tracks), expected=[])

    # zero pack references; no solution
    check_allocation((packs, tracks, [], num_silent_tracks), expected=[])

    # no pack references; one solution as long as there are no silent tracks
    if num_silent_tracks == 0:
        check_allocation(
            (packs, tracks, None, num_silent_tracks),
            expected=[
                [
                    AllocatedPack(
                        packs[0], [(packs[0].channels[0], expected_track(tracks))]
                    )
                ]
            ],
        )


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
    check_allocation((packs, tracks, [p2], num_silent_tracks), expected=[expected])

    # no pack references; one solution. Note that cases there num_silent_tracks
    # > 0 never happen in real use, as the CHNA chunk doesn't specify silent
    # tracks.
    check_allocation((packs, tracks, None, num_silent_tracks), expected=[expected])

    # zero pack references; no solution
    check_allocation((packs, tracks, [], num_silent_tracks), expected=[])

    # reference to sub-pack; no solution
    check_allocation((packs, tracks, [p1], num_silent_tracks), expected=[])


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
    expected = [
        AllocatedPack(packs[1], [(packs[1].channels[0], tracks[0])]),
        AllocatedPack(packs[1], [(packs[1].channels[0], tracks[1])]),
    ]
    check_allocation((packs, tracks, [p2, p2], 0), expected=[expected])

    # two identical silent mono tracks
    expected = [
        AllocatedPack(packs[1], [(packs[1].channels[0], None)]),
        AllocatedPack(packs[1], [(packs[1].channels[0], None)]),
    ]
    check_allocation((packs, [], [p2, p2], 2), expected=[expected])

    # one real, one silent
    expected = [
        AllocatedPack(packs[1], [(packs[1].channels[0], tracks[0])]),
        AllocatedPack(packs[1], [(packs[1].channels[0], None)]),
    ]
    check_allocation((packs, tracks[:1], [p2, p2], 1), expected=[expected])

    # chna-only case
    expected = [
        AllocatedPack(packs[1], [(packs[1].channels[0], tracks[0])]),
        AllocatedPack(packs[1], [(packs[1].channels[0], tracks[1])]),
    ]
    check_allocation((packs, tracks, None, 0), expected=[expected])

    # duplicate stereo is still ambiguous
    tracks = [
        AllocationTrack(c1, p1),
        AllocationTrack(c2, p1),
        AllocationTrack(c1, p1),
        AllocationTrack(c2, p1),
    ]
    check_allocation((packs, tracks, [p1, p1], 0), count=2)
    check_allocation((packs, tracks, None, 0), count=2)


@pytest.mark.parametrize("channels", [[c1], [c1, c2]],
                         ids=["mono", "stereo"])
@pytest.mark.parametrize("silent", [True, False])
@pytest.mark.parametrize(
    "allocate_packs_impl",
    [fn for (name, fn) in fast_implementations],
    ids=[name for (name, fn) in fast_implementations],
)
def test_many_packs(channels, silent, allocate_packs_impl):
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

    res = allocate_packs_impl(packs, tracks, pack_refs, num_silent)
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

    res = check_allocation(
        (packs, tracks, None if chna_only else pack_refs, 0),
        count=1,
        implementations=fast_implementations,
    )


def test_silent_stereo_51():
    """stereo and 5.1 pack structure, with all silent channels"""
    packs = [
        AllocationPack(p1, [AllocationChannel(c1, [p1]), AllocationChannel(c2, [p1])]),
        AllocationPack(
            p2,
            [
                AllocationChannel(c1, [p2, p1]),
                AllocationChannel(c2, [p2, p1]),
                AllocationChannel(c3, [p2]),
                AllocationChannel(c4, [p2]),
                AllocationChannel(c5, [p2]),
            ],
        ),
    ]

    check_allocation((packs, [], [p1, p2], 7), count=1)


def test_onlysilent_simple():
    """simplified version of test_silent_stereo_51"""
    packs = [
        AllocationPack(p1, [AllocationChannel(c1, [p1])]),
        AllocationPack(p2, [AllocationChannel(c1, [p2])]),
    ]

    check_allocation((packs, [], [p1, p2], 2), count=1)


def test_duplicate_packs_different_channels():
    """test duplicate pack IDs with different channels"""
    packs = [
        AllocationPack(p1, [AllocationChannel(c1, [p1])]),
        AllocationPack(p1, [AllocationChannel(c2, [p1])]),
    ]

    tracks = [AllocationTrack(c1, p1), AllocationTrack(c2, p1)]
    pack_refs = [p1, p1]

    check_allocation((packs, tracks, pack_refs, 0), count=1)


def test_duplicate_packs():
    """duplicate pack IDs and channels"""
    packs = [
        AllocationPack(p1, [AllocationChannel(c1, [p1])]),
        AllocationPack(p1, [AllocationChannel(c1, [p1])]),
    ]

    tracks = [AllocationTrack(c1, p1), AllocationTrack(c1, p1)]

    check_allocation((packs, tracks, [p1, p1], 0), count=4)


# tests below represent interesting cases from randomised testing on buggy
# implementations during development


def test_complex_pack_order():
    """randomised test with three packs and ambiguity"""
    packs = [
        AllocationPack(
            p1,
            [
                AllocationChannel(channel_format=c4, pack_formats=[p1, p2]),
                AllocationChannel(channel_format=c3, pack_formats=[p2]),
            ],
        ),
        AllocationPack(
            p3,
            [
                AllocationChannel(channel_format=c5, pack_formats=[p2]),
                AllocationChannel(channel_format=c2, pack_formats=[p1, p2]),
                AllocationChannel(channel_format=c4, pack_formats=[p1, p3]),
            ],
        ),
        AllocationPack(
            p2,
            [
                AllocationChannel(channel_format=c1, pack_formats=[p1, p3]),
                AllocationChannel(channel_format=c2, pack_formats=[p1, p3]),
            ],
        ),
    ]
    tracks = [
        AllocationTrack(channel_format=c1, pack_format=p1),
        AllocationTrack(channel_format=c2, pack_format=p3),
        AllocationTrack(channel_format=c2, pack_format=p1),
        AllocationTrack(channel_format=c4, pack_format=p2),
    ]
    pack_refs = [p1, p2, p2]
    num_silent = 2

    check_allocation((packs, tracks, pack_refs, num_silent), count=2)


def test_ambiguous_pack_silent():
    """randomised test with ambiguity between two identically-named packs"""
    packs = [
        AllocationPack(
            p1,
            [
                AllocationChannel(channel_format=c1, pack_formats=[p1]),
            ],
        ),
        AllocationPack(
            p1,
            [
                AllocationChannel(channel_format=c2, pack_formats=[p1]),
            ],
        ),
    ]
    tracks = [
        AllocationTrack(channel_format=c1, pack_format=p1),
    ]
    pack_refs = [p1, p1]
    num_silent = 1

    check_allocation((packs, tracks, pack_refs, num_silent), count=2)


def test_one_silent_in_two_identical_pack_refs():
    """randomised test with duplicate packs, one silent channel each (but not
    the first channel), but not actually ambiguous"""
    packs = [
        AllocationPack(
            p1,
            [
                AllocationChannel(channel_format=c1, pack_formats=[p1]),
                AllocationChannel(channel_format=c2, pack_formats=[p1]),
            ],
        ),
    ]
    tracks = [
        AllocationTrack(channel_format=c2, pack_format=p1),
        AllocationTrack(channel_format=c2, pack_format=p1),
    ]
    pack_refs = [p1, p1]
    num_silent = 2

    check_allocation((packs, tracks, pack_refs, num_silent), count=1)
