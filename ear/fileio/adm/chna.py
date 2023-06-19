from collections import namedtuple
import re
from .elements import AudioTrackUID
from ..bw64.chunks import AudioID

_TrackOrChannelRef = namedtuple("_TrackOrChannelRef", ("is_channel", "id"))


def _load_track_or_channel_ref(track, chna_entry):
    """update an audioTrackUID with the track format or channel format reference in a CHNA entry"""
    # chna and audioTrackUID both reference either a track or a channel format;
    # for both, find which it is, and its ID
    chna_track_ref = chna_entry.audioTrackFormatIDRef
    chna_ref = _TrackOrChannelRef(
        chna_track_ref.startswith("AC_"), chna_track_ref.upper()
    )

    track_ref = None
    if track.audioTrackFormat is not None and track.audioChannelFormat is not None:
        # this check is already in validation, but this code normally runs
        # first, and if we don't check here then the exception below could be
        # thrown first, which would be confusing
        raise Exception(
            f"audioTrackUID {track.id} is linked to both an audioTrackFormat and a audioChannelFormat"
        )
    elif track.audioChannelFormat is not None:
        track_ref = _TrackOrChannelRef(True, track.audioChannelFormat.id.upper())
    elif track.audioTrackFormat is not None:
        track_ref = _TrackOrChannelRef(False, track.audioTrackFormat.id.upper())

    # then assign if it has no reference, or check the reference is the same
    if track_ref is None:
        if chna_ref.is_channel:
            track.audioChannelFormatIDRef = chna_ref.id
        else:
            track.audioTrackFormatIDRef = chna_ref.id
    elif chna_ref != track_ref:
        raise Exception(
            f"Error in track UID {track.id}: CHNA entry references '{chna_ref.id}' "
            f"but AXML references '{track_ref.id}'"
        )


def _load_pack_ref(track, chna_entry):
    """update an audioTrackUID with the pack format reference in a CHNA entry"""
    if chna_entry.audioPackFormatIDRef is not None:
        if track.audioPackFormat is None:
            track.audioPackFormatIDRef = chna_entry.audioPackFormatIDRef
        elif (
            track.audioPackFormat.id.upper() != chna_entry.audioPackFormatIDRef.upper()
        ):
            raise Exception(
                "Error in track UID {track.id}: audioPackFormatIDRef in CHNA, '{chna_entry.audioPackFormatIDRef}' "
                "does not match value in AXML, '{track.audioPackFormat.id}'.".format(
                    track=track, chna_entry=chna_entry
                )
            )


def load_chna_chunk(adm, chna):
    """Add information from the chna chunk to the adm track UIDs structure.

    Any existing track UIDs in adm are checked for consistency against the data
    in chna; any non-existent track-UIDs are created.

    The track index, pack format ref and track format ref attributes are
    transferred; there references are resolved, and we assume that any
    references in adm have already been resolved

    Parameters:
        adm (ADM): adm structure to add information to
        chna (ChnaChunk): chna chunk to get information from
    """
    track_uid_by_id = {track.id.upper(): track for track in adm.audioTrackUIDs}

    for chna_entry in chna.audioIDs:
        track = track_uid_by_id.get(chna_entry.audioTrackUID.upper())

        if track is None:
            track = AudioTrackUID(id=chna_entry.audioTrackUID.upper())
            adm.addAudioTrackUID(track)

        if track.trackIndex is None:
            track.trackIndex = chna_entry.trackIndex
        else:
            assert track.trackIndex == chna_entry.trackIndex

        _load_track_or_channel_ref(track, chna_entry)
        _load_pack_ref(track, chna_entry)

    for atu in adm.audioTrackUIDs:
        if atu.id is not None and atu.id.upper() == "ATU_00000000":
            raise Exception("audioTrackUID element or CHNA row found with UID "
                            "ATU_00000000, which is reserved for silent tracks.")

    adm.lazy_lookup_references()


def _get_chna_entries(adm):
    for track_uid in adm.audioTrackUIDs:
        if track_uid.trackIndex is None:
            raise Exception("Track UID {track_uid.id} has no track number.".format(track_uid=track_uid))
        if (track_uid.audioTrackFormat is None) and (track_uid.audioChannelFormat is None):
            raise Exception("Track UID {track_uid.id} has no track or channel format.".format(track_uid=track_uid))
        if (track_uid.audioTrackFormat is not None) and (track_uid.audioChannelFormat is not None):
            raise Exception("Track UID {track_uid.id} has both track and channel formats.".format(track_uid=track_uid))

        assert track_uid.id is not None, "ids have not been generated"
        assert track_uid.audioTrackFormat is None or track_uid.audioTrackFormat.id is not None, "ids have not been generated"
        assert track_uid.audioChannelFormat is None or track_uid.audioChannelFormat.id is not None, "ids have not been generated"
        assert track_uid.audioPackFormat is None or track_uid.audioPackFormat.id is not None, "ids have not been generated"

        yield AudioID(
            trackIndex=track_uid.trackIndex,
            audioTrackUID=track_uid.id,
            audioTrackFormatIDRef=(track_uid.audioTrackFormat.id
                                   if track_uid.audioTrackFormat is not None
                                   else track_uid.audioChannelFormat.id),
            audioPackFormatIDRef=(track_uid.audioPackFormat.id
                                  if track_uid.audioPackFormat is not None
                                  else None))


def populate_chna_chunk(chna, adm):
    """Populate the CHNA chunk with information from the ADM model.

    All CHNA entries are replaced, and are populated from the trackIndex,
    audioTrackUID, and the track format/pack format references.

    Since the CHNA chunk contains IDs, the IDs in the ADM must have been
    generated before calling this.

    Parameters:
        adm (ADM): adm structure to get information to
        chna (ChnaChunk): chna chunk to populate
    """
    chna.audioIDs = list(_get_chna_entries(adm))


_TRACK_UID_RE = re.compile("ATU_([0-9a-fA-F]{8})$")


def guess_track_indices(adm):
    """Guess track indices from the audioTrackUID IDs.

    This information should really come from the CHNA, but sometimes that isn't
    available.

    Parameters:
        adm (ADM): ADM structure to modify
    """
    for track_uid in adm.audioTrackUIDs:
        assert track_uid.trackIndex is None

        match = _TRACK_UID_RE.match(track_uid.id)
        if match is None:
            raise Exception("Invalid track UID {}.".format(track_uid.id))

        track_uid.trackIndex = int(match.group(1), 16)
