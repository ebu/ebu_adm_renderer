import pytest
from ..chna import load_chna_chunk, populate_chna_chunk
from ..adm import ADM
from ..elements import AudioTrackUID
from ..common_definitions import load_common_definitions
from ...bw64.chunks import ChnaChunk, AudioID


def test_load():
    adm = ADM()
    load_common_definitions(adm)
    chna = ChnaChunk()

    # normal use
    chna.audioIDs = [AudioID(1, "ATU_00000001", "AT_00010001_01", "AP_00010002")]
    load_chna_chunk(adm, chna)
    assert adm.audioTrackUIDs[0].trackIndex == 1
    assert adm.audioTrackUIDs[0].id == "ATU_00000001"
    assert adm.audioTrackUIDs[0].audioTrackFormat is adm["AT_00010001_01"]
    assert adm.audioTrackUIDs[0].audioPackFormat is adm["AP_00010002"]

    # missing pack ref
    chna.audioIDs = [AudioID(2, "ATU_00000002", "AT_00010002_01", None)]
    load_chna_chunk(adm, chna)
    assert adm.audioTrackUIDs[1].audioPackFormat is None

    # inconsistent pack ref
    chna.audioIDs = [AudioID(1, "ATU_00000001", "AT_00010002_01", "AP_00010002")]
    with pytest.raises(Exception) as excinfo:
        load_chna_chunk(adm, chna)
    assert str(excinfo.value) == ("Error in track UID ATU_00000001: audioTrackFormatIDRef in CHNA, "
                                  "'AT_00010002_01' does not match value in AXML, 'AT_00010001_01'.")

    # inconsistent track ref
    chna.audioIDs = [AudioID(1, "ATU_00000001", "AT_00010001_01", "AP_00010003")]
    with pytest.raises(Exception) as excinfo:
        load_chna_chunk(adm, chna)
    assert str(excinfo.value) == ("Error in track UID ATU_00000001: audioPackFormatIDRef in CHNA, "
                                  "'AP_00010003' does not match value in AXML, 'AP_00010002'.")

    # zero track uid
    chna.audioIDs = [AudioID(1, "ATU_00000000", "AT_00010001_01", "AP_00010002")]
    expected = ("audioTrackUID element or CHNA row found with UID "
                "ATU_00000000, which is reserved for silent tracks.")
    with pytest.raises(Exception, match=expected):
        load_chna_chunk(adm, chna)


def test_populate():
    adm = ADM()
    load_common_definitions(adm)
    chna = ChnaChunk()

    # normal use
    adm.addAudioTrackUID(AudioTrackUID(
        id="ATU_00000001",
        trackIndex=1,
        audioTrackFormat=adm["AT_00010001_01"],
        audioPackFormat=adm["AP_00010002"]))

    # missing pack format
    adm.addAudioTrackUID(AudioTrackUID(
        id="ATU_00000002",
        trackIndex=2,
        audioTrackFormat=adm["AT_00010002_01"]))

    populate_chna_chunk(chna, adm)
    assert chna.audioIDs == [AudioID(audioTrackUID="ATU_00000001",
                                     trackIndex=1,
                                     audioTrackFormatIDRef="AT_00010001_01",
                                     audioPackFormatIDRef="AP_00010002"),
                             AudioID(audioTrackUID="ATU_00000002",
                                     trackIndex=2,
                                     audioTrackFormatIDRef="AT_00010002_01",
                                     audioPackFormatIDRef=None)]
