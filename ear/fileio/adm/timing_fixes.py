import warnings
from ...core.select_items.select_items import ObjectChannelMatcher
from .adm import ADM
from .elements import AudioBlockFormatObjects, AudioBlockFormat


def _has_interpolationLength(blockFormat):
    """Does blockFormat have a defined interpolationLength?"""
    assert isinstance(blockFormat, AudioBlockFormat), "wrong type"
    return (
        isinstance(blockFormat, AudioBlockFormatObjects)
        and blockFormat.jumpPosition.flag
        and blockFormat.jumpPosition.interpolationLength is not None
    )


def _check_blockFormat_duration(bf_a, bf_b, fix=False):
    old_duration = bf_a.duration
    new_duration = bf_b.rtime - bf_a.rtime

    if old_duration != new_duration:
        if fix:
            warnings.warn(
                "{direction} duration of block format {id} to match next "
                "rtime; was: {old}, now: {new}".format(
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
        else:
            warnings.warn(
                "duration of block format {id} does not match rtime of next block".format(
                    id=bf_a.id,
                )
            )


def check_blockFormat_durations(adm, fix=False):
    """If fix, modify the duration of audioBlockFormats to ensure that the end
    of one audioBlockFormat always matches the start of the next.
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

            _check_blockFormat_duration(bf_a, bf_b, fix=fix)


def check_blockFormat_interpolationLengths(adm, fix=False):
    """If fix, modify the interpolationLength of audioBlockFormats to ensure
    that they are not greater than the durations.
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
                if fix:
                    warnings.warn(
                        "contracted interpolationLength of block format {id} to match "
                        "duration; was: {old}, now: {new}".format(
                            id=blockFormat.id,
                            old=blockFormat.jumpPosition.interpolationLength,
                            new=blockFormat.duration,
                        )
                    )
                    blockFormat.jumpPosition.interpolationLength = blockFormat.duration
                else:
                    warnings.warn(
                        "interpolationLength of block format {id} is greater than duration".format(
                            id=blockFormat.id,
                        )
                    )


def _clamp_blockFormat_times(blockFormat, audioObject, fix=False):
    """Modify the duration and interpolationLengths of blockFormat to ensure
    that it is within audioObject, which must have a start and duration.
    """
    if blockFormat.rtime is None and blockFormat.duration is None:
        _clamp_blockFormat_interpolationLength(blockFormat, audioObject, fix=fix)
    elif blockFormat.rtime is not None and blockFormat.duration is not None:
        _clamp_blockFormat_end(blockFormat, audioObject, fix=fix)
    else:
        assert False, "not validated"


def _clamp_blockFormat_interpolationLength(blockFormat, audioObject, fix=False):
    """Modify the interpolationLength of blockFormat to fit within audioObject,
    in the case where audioObject has a start and duration, but blockFormat
    doesn't.
    """
    if (
        _has_interpolationLength(blockFormat)
        and blockFormat.jumpPosition.interpolationLength > audioObject.duration
    ):
        if fix:
            warnings.warn(
                "reduced interpolationLength of {bf_id} to match duration of {obj_id}".format(
                    bf_id=blockFormat.id, obj_id=audioObject.id
                )
            )
            blockFormat.jumpPosition.interpolationLength = audioObject.duration
        else:
            warnings.warn(
                "interpolationLength of {bf_id} is longer than duration of {obj_id}".format(
                    bf_id=blockFormat.id, obj_id=audioObject.id
                )
            )


def _clamp_blockFormat_end(blockFormat, audioObject, fix=False):
    """Modify the duration and interpolationLength of blockFormat to fit within
    audioObject, in the case where both blockFormat and audioObject have
    rtime/start/duration.
    """
    block_end = blockFormat.rtime + blockFormat.duration
    if block_end > audioObject.duration:
        shift = block_end - audioObject.duration

        fmt_args = dict(bf_id=blockFormat.id, obj_id=audioObject.id, shift=shift)

        if fix:
            if shift >= blockFormat.duration:
                raise ValueError(
                    "tried to advance end of {bf_id} by {shift} to match end time of "
                    "{obj_id}, but this would be before the block start".format(
                        **fmt_args
                    )
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
                    and blockFormat.jumpPosition.interpolationLength
                    > blockFormat.duration
                ):
                    warnings.warn(
                        "while advancing end of {bf_id} to match end time of {obj_id}, had "
                        "to reduce the interpolationLength too".format(**fmt_args)
                    )
                    blockFormat.jumpPosition.interpolationLength = blockFormat.duration
        else:
            warnings.warn(
                "end of {bf_id} is after end time of {obj_id}".format(**fmt_args)
            )


def check_blockFormat_times_for_audioObjects(adm: ADM, fix=False):
    """If fix, modify the rtimes, durations and interpolationLengths of
    audioBlockFormats to ensure that they are within their parent audioObjects.
    """
    matcher = ObjectChannelMatcher(adm)

    for audioObject in adm.audioObjects:
        if audioObject.duration is None:
            continue

        for channelFormat in matcher.get_channel_formats_for_object(audioObject):
            for blockFormat in channelFormat.audioBlockFormats:
                _clamp_blockFormat_times(blockFormat, audioObject, fix=fix)


def check_blockFormat_timings(adm: ADM, fix=False):
    """If fix, fix various audioBlockFormat timing issues, otherwise just issue
    warnings.

    Parameters:
        adm: ADM document to modify
    """
    check_blockFormat_durations(adm, fix=fix)
    check_blockFormat_interpolationLengths(adm, fix=fix)
    check_blockFormat_times_for_audioObjects(adm, fix=fix)


def fix_blockFormat_timings(adm: ADM):
    """Fix various audioBlockFormat timing issues, issuing warnings.

    Parameters:
        adm: ADM document to modify
    """
    check_blockFormat_timings(adm, fix=True)
