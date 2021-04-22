import warnings
from ...core.select_items.select_items import ObjectChannelMatcher
from .elements import AudioBlockFormatObjects, BlockFormat


def _has_interpolationLength(blockFormat):
    """Does blockFormat have a defined interpolationLength?"""
    assert isinstance(blockFormat, BlockFormat), "wrong type"
    return (
        isinstance(blockFormat, AudioBlockFormatObjects)
        and blockFormat.jumpPosition.flag
        and blockFormat.jumpPosition.interpolationLength is not None
    )


def fix_blockFormat_durations(adm):
    """Modify the duration of audioBlockFormats to ensure that the end of one
    audioBlockFormat always matches the start of the next.
    """
    for channelFormat in adm.audioChannelFormats:
        blockFormats = channelFormat.audioBlockFormats

        for bf_a, bf_b in zip(blockFormats[:-1], blockFormats[1:]):
            if (
                bf_a.rtime is None
                or bf_a.duration is None
                or bf_b.rtime is None
                or bf_b.duration is None
            ):
                continue

            old_duration = bf_a.duration
            new_duration = bf_b.rtime - bf_a.rtime

            if old_duration != new_duration:
                warnings.warn(
                    "{direction} duration of block format {id}; was: {old}, now: {new}".format(
                        direction=(
                            "expanded" if new_duration > old_duration else "contracted"
                        ),
                        id=bf_a.id,
                        old=old_duration,
                        new=new_duration,
                    )
                )
                bf_a.duration = new_duration

                # if contracting this block makes the interpolation end after
                # the block, fix it without any more noise
                if (
                    _has_interpolationLength(bf_a)
                    and old_duration >= bf_a.jumpPosition.interpolationLength
                    and new_duration < bf_a.jumpPosition.interpolationLength
                ):
                    bf_a.jumpPosition.interpolationLength = new_duration


def fix_blockFormat_interpolationLengths(adm):
    """Modify the interpolationLength of audioBlockFormats to ensure that they
    are not greater than the durations.
    """
    for channelFormat in adm.audioChannelFormats:
        for blockFormat in channelFormat.audioBlockFormats:
            if (
                blockFormat.rtime is None
                or blockFormat.duration is None
                or not _has_interpolationLength(blockFormat)
            ):
                continue

            if blockFormat.jumpPosition.interpolationLength > blockFormat.duration:
                warnings.warn(
                    "contracted interpolationLength of block format {id}; was: {old}, now: {new}".format(
                        id=blockFormat.id,
                        old=blockFormat.jumpPosition.interpolationLength,
                        new=blockFormat.duration,
                    )
                )
                blockFormat.jumpPosition.interpolationLength = blockFormat.duration


def _clamp_blockFormat_times(blockFormat, audioObject):
    """Modify the duration and interpolationLengths of blockFormat to ensure
    that it is within audioObject, which must have a start and duration.
    """
    if blockFormat.rtime is None or blockFormat.duration is None:
        _clamp_blockFormat_interpolationLength(blockFormat, audioObject)
    elif blockFormat.rtime is not None or blockFormat.duration is not None:
        _clamp_blockFormat_end(blockFormat, audioObject)
    else:
        assert False, "not validated"


def _clamp_blockFormat_interpolationLength(blockFormat, audioObject):
    if (
        _has_interpolationLength(blockFormat)
        and blockFormat.jumpPosition.interpolationLength > audioObject.duration
    ):
        warnings.warn(
            "reduced interpolationLength of {bf_id} to match duration of {obj_id}".format(
                bf_id=blockFormat.id, obj_id=audioObject.id
            )
        )
        blockFormat.jumpPosition.interpolationLength = audioObject.duration


def _clamp_blockFormat_end(blockFormat, audioObject):
    block_end = blockFormat.rtime + blockFormat.duration
    if block_end > audioObject.duration:
        shift = block_end - audioObject.duration

        fmt_args = dict(bf_id=blockFormat.id, obj_id=audioObject.id, shift=shift)

        if shift >= blockFormat.duration:
            raise ValueError(
                "tried to advance end of {bf_id} by {shift} to match end time of "
                "{obj_id}, but this would be before the block start".format(**fmt_args)
            )
        else:
            warnings.warn(
                "advancing end of {bf_id} by {shift} to match end time of {obj_id}".format(
                    **fmt_args
                )
            )

            blockFormat.duration -= shift
            if (
                _has_interpolationLength(blockFormat)
                and blockFormat.jumpPosition.interpolationLength > blockFormat.duration
            ):
                warnings.warn(
                    "while advancing end of {bf_id} to match end time of {obj_id}, had "
                    "to reduce the interpolationLength too".format(**fmt_args)
                )
                blockFormat.jumpPosition.interpolationLength = blockFormat.duration


def fix_blockFormat_times_for_audioObjects(adm):
    """Modify the rtimes, durations and interpolationLengths of
    audioBlockFormats to ensure that they are within their parent
    audioObjects.
    """
    matcher = ObjectChannelMatcher(adm)

    for audioObject in adm.audioObjects:
        if audioObject.start is None or audioObject.duration is None:
            continue

        for channelFormat in matcher.get_channel_formats_for_object(audioObject):
            for blockFormat in channelFormat.audioBlockFormats:
                _clamp_blockFormat_times(blockFormat, audioObject)


def fix_blockFormat_timings(adm):
    """Fix various audioBlockFormat timing issues."""
    fix_blockFormat_durations(adm)
    fix_blockFormat_interpolationLengths(adm)
    fix_blockFormat_times_for_audioObjects(adm)
