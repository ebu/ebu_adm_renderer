from ..builder import ADMBuilder
from ..elements import AudioBlockFormatObjects
from .. import timing_fixes
from ..generate_ids import generate_ids
from fractions import Fraction
import pytest


def make_abfo(**kwargs):
    return AudioBlockFormatObjects(
        position=dict(azimuth=0.0, elevation=0.0, distance=1.0), **kwargs
    )


@pytest.fixture
def two_blocks():
    builder = ADMBuilder()
    builder.create_item_objects(
        track_index=1,
        name="MyObject 1",
        block_formats=[
            make_abfo(rtime=Fraction(0), duration=Fraction(1)),
            make_abfo(rtime=Fraction(1), duration=Fraction(1)),
        ],
    )
    generate_ids(builder.adm)

    return builder


@pytest.fixture
def one_block():
    builder = ADMBuilder()
    builder.create_item_objects(
        track_index=1,
        name="MyObject 1",
        block_formats=[make_abfo(rtime=None, duration=None)],
    )
    generate_ids(builder.adm)

    return builder


def test_fix_blockFormat_durations_expansion(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[1].rtime = Fraction(2)

    with pytest.warns(
        UserWarning,
        match="expanded duration of block format {bf.id} to match next "
        "rtime; was: 1, now: 2".format(bf=block_formats[0]),
    ):
        timing_fixes.check_blockFormat_durations(two_blocks.adm, fix=True)

    assert block_formats[0].duration == Fraction(2)


def test_fix_blockFormat_durations_contraction(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].duration = Fraction(2)

    with pytest.warns(
        UserWarning,
        match="contracted duration of block format {bf.id} to match next "
        "rtime; was: 2, now: 1".format(bf=block_formats[0]),
    ):
        timing_fixes.check_blockFormat_durations(two_blocks.adm, fix=True)

    assert block_formats[0].duration == Fraction(1)


def test_check_blockFormat_durations(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].duration = Fraction(2)

    with pytest.warns(
        UserWarning,
        match="duration of block format {bf.id} does not match rtime of next block".format(
            bf=block_formats[0]
        ),
    ):
        timing_fixes.check_blockFormat_durations(two_blocks.adm, fix=False)

    assert block_formats[0].duration == Fraction(2)


def test_fix_blockFormat_durations_interpolationLength(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].duration = Fraction(2)
    block_formats[0].jumpPosition.flag = True
    block_formats[0].jumpPosition.interpolationLength = Fraction(2)

    with pytest.warns(
        UserWarning,
        match="contracted duration of block format {bf.id} to match next "
        "rtime; was: 2, now: 1".format(bf=block_formats[0]),
    ):
        timing_fixes.check_blockFormat_durations(two_blocks.adm, fix=True)

    assert block_formats[0].duration == Fraction(1)
    assert block_formats[0].jumpPosition.interpolationLength == Fraction(1)


def test_fix_blockFormat_durations_correct_interpolationLength(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].duration = Fraction(2)
    block_formats[0].jumpPosition.flag = True
    block_formats[0].jumpPosition.interpolationLength = Fraction("1/2")

    with pytest.warns(
        UserWarning,
        match="contracted duration of block format {bf.id} to match next "
        "rtime; was: 2, now: 1".format(bf=block_formats[0]),
    ):
        timing_fixes.check_blockFormat_durations(two_blocks.adm, fix=True)

    assert block_formats[0].duration == Fraction(1)
    assert block_formats[0].jumpPosition.interpolationLength == Fraction("1/2")


def test_fix_blockFormat_interpolationLengths(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].jumpPosition.flag = True
    block_formats[0].jumpPosition.interpolationLength = Fraction("2")

    with pytest.warns(
        UserWarning,
        match="contracted interpolationLength of block format {bf.id} to "
        "match duration; was: 2, now: 1".format(bf=block_formats[0]),
    ):
        timing_fixes.check_blockFormat_interpolationLengths(two_blocks.adm, fix=True)

    assert block_formats[0].jumpPosition.interpolationLength == Fraction(1)


def test_fix_blockFormat_interpolationLengths_no_change(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].jumpPosition.flag = True
    block_formats[0].jumpPosition.interpolationLength = Fraction("1/2")

    timing_fixes.check_blockFormat_interpolationLengths(two_blocks.adm, fix=True)

    assert block_formats[0].jumpPosition.interpolationLength == Fraction("1/2")


def test_check_blockFormat_interpolationLengths(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].jumpPosition.flag = True
    block_formats[0].jumpPosition.interpolationLength = Fraction("2")

    with pytest.warns(
        UserWarning,
        match="interpolationLength of block format {bf.id} is greater than duration".format(
            bf=block_formats[0]
        ),
    ):
        timing_fixes.check_blockFormat_interpolationLengths(two_blocks.adm, fix=False)

    assert block_formats[0].jumpPosition.interpolationLength == Fraction("2")


def test_fix_blockFormat_times_for_audioObjects_no_change(two_blocks):
    timing_fixes.check_blockFormat_times_for_audioObjects(two_blocks.adm, fix=True)


@pytest.mark.parametrize("fix", [False, True])
def test_fix_blockFormat_times_for_audioObjects_advance_end(two_blocks, fix):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    two_blocks.adm.audioObjects[0].start = Fraction("2")
    two_blocks.adm.audioObjects[0].duration = Fraction("1.5")

    msg_fmt = (
        "advancing end of {bf.id} by 1/2 to match end time of {ao.id}"
        if fix
        else "end of {bf.id} is after end time of {ao.id}"
    )
    msg = msg_fmt.format(bf=block_formats[1], ao=two_blocks.adm.audioObjects[0])
    with pytest.warns(UserWarning, match=msg):
        timing_fixes.check_blockFormat_times_for_audioObjects(two_blocks.adm, fix=fix)

    assert block_formats[1].duration == Fraction("1/2" if fix else "1.0")


def test_fix_blockFormat_times_for_audioObjects_advance_end_before_start(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    two_blocks.adm.audioObjects[0].start = Fraction(0)
    two_blocks.adm.audioObjects[0].duration = Fraction(1)

    msg = (
        "tried to advance end of {bf.id} by 1 to match end time of {ao.id}, "
        "but this would be before the block start"
    ).format(bf=block_formats[1], ao=two_blocks.adm.audioObjects[0])
    with pytest.raises(ValueError, match=msg):
        timing_fixes.check_blockFormat_times_for_audioObjects(two_blocks.adm, fix=True)


def test_fix_blockFormat_times_for_audioObjects_advance_end_interpolationLength(
    two_blocks,
):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    two_blocks.adm.audioObjects[0].start = Fraction(0)
    two_blocks.adm.audioObjects[0].duration = Fraction("1.25")
    block_formats[1].jumpPosition.flag = True
    block_formats[1].jumpPosition.interpolationLength = Fraction("1/2")

    with pytest.warns(UserWarning) as warnings:
        timing_fixes.check_blockFormat_times_for_audioObjects(two_blocks.adm, fix=True)
    msg = "advancing end of {bf.id} by 3/4 to match end time of {ao.id}".format(
        bf=block_formats[1], ao=two_blocks.adm.audioObjects[0]
    )
    assert str(warnings[0].message) == msg
    msg = (
        "while advancing end of {bf.id} to match end time of {ao.id}, had "
        "to reduce the interpolationLength too"
    ).format(bf=block_formats[1], ao=two_blocks.adm.audioObjects[0])
    assert str(warnings[1].message) == msg

    assert block_formats[1].duration == Fraction("1/4")
    assert block_formats[1].jumpPosition.interpolationLength == Fraction("1/4")


@pytest.mark.parametrize("fix", [False, True])
def test_fix_blockFormat_times_for_audioObjects_only_interp(one_block, fix):
    [block_format] = one_block.adm.audioChannelFormats[0].audioBlockFormats
    one_block.adm.audioObjects[0].start = Fraction(0)
    one_block.adm.audioObjects[0].duration = Fraction(1)
    block_format.jumpPosition.flag = True
    block_format.jumpPosition.interpolationLength = Fraction(2)

    msg_fmt = (
        "reduced interpolationLength of {bf.id} to match duration of {ao.id}"
        if fix
        else "interpolationLength of {bf.id} is longer than duration of {ao.id}"
    )
    msg = msg_fmt.format(bf=block_format, ao=one_block.adm.audioObjects[0])
    with pytest.warns(UserWarning, match=msg):
        timing_fixes.check_blockFormat_times_for_audioObjects(one_block.adm, fix=fix)

    assert block_format.jumpPosition.interpolationLength == Fraction(1 if fix else 2)
