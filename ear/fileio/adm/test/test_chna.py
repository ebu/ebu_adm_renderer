import pytest
from ...bw64.chunks import AudioID, ChnaChunk
from ..adm import ADM
from ..chna import load_chna_chunk, populate_chna_chunk
from ..common_definitions import load_common_definitions
from ..elements import AudioTrackUID


@pytest.fixture
def adm():
    adm = ADM()
    load_common_definitions(adm)
    return adm


@pytest.fixture
def chna():
    return ChnaChunk()


class TestLoad:
    def test_track_ref(self, adm, chna):
        chna.audioIDs = [AudioID(1, "ATU_00000001", "AT_00010001_01", "AP_00010002")]
        load_chna_chunk(adm, chna)
        assert adm.audioTrackUIDs[0].trackIndex == 1
        assert adm.audioTrackUIDs[0].id == "ATU_00000001"
        assert adm.audioTrackUIDs[0].audioTrackFormat is adm["AT_00010001_01"]
        assert adm.audioTrackUIDs[0].audioPackFormat is adm["AP_00010002"]

    def test_missing_pack_ref(self, adm, chna):
        chna.audioIDs = [AudioID(2, "ATU_00000002", "AT_00010002_01", None)]
        load_chna_chunk(adm, chna)
        assert adm.audioTrackUIDs[0].audioPackFormat is None

    def test_inconsistent_pack_ref(self, adm, chna):
        adm.addAudioTrackUID(
            AudioTrackUID(
                id="ATU_00000001",
                trackIndex=1,
                audioTrackFormat=adm["AT_00010001_01"],
                audioPackFormat=adm["AP_00010002"],
            )
        )
        chna.audioIDs = [AudioID(1, "ATU_00000001", "AT_00010001_01", "AP_00010003")]
        expected = (
            "Error in track UID ATU_00000001: audioPackFormatIDRef in CHNA, "
            "'AP_00010003' does not match value in AXML, 'AP_00010002'."
        )
        with pytest.raises(Exception, match=expected):
            load_chna_chunk(adm, chna)

    def test_inconsistent_track_ref(self, adm, chna):
        adm.addAudioTrackUID(
            AudioTrackUID(
                id="ATU_00000001",
                trackIndex=1,
                audioTrackFormat=adm["AT_00010001_01"],
                audioPackFormat=adm["AP_00010002"],
            )
        )
        chna.audioIDs = [AudioID(1, "ATU_00000001", "AT_00010002_01", "AP_00010002")]
        expected = (
            "Error in track UID ATU_00000001: CHNA entry references "
            "'AT_00010002_01' but AXML references 'AT_00010001_01'"
        )
        with pytest.raises(Exception, match=expected):
            load_chna_chunk(adm, chna)

    def test_zero_track_uid(self, adm, chna):
        chna.audioIDs = [AudioID(1, "ATU_00000000", "AT_00010001_01", "AP_00010002")]
        expected = (
            "audioTrackUID element or CHNA row found with UID "
            "ATU_00000000, which is reserved for silent tracks."
        )
        with pytest.raises(Exception, match=expected):
            load_chna_chunk(adm, chna)

    def test_channel_ref(self, adm, chna):
        chna.audioIDs = [AudioID(1, "ATU_00000001", "AC_00010001", "AP_00010002")]
        load_chna_chunk(adm, chna)
        assert adm.audioTrackUIDs[0].trackIndex == 1
        assert adm.audioTrackUIDs[0].id == "ATU_00000001"
        assert adm.audioTrackUIDs[0].audioChannelFormat is adm["AC_00010001"]
        assert adm.audioTrackUIDs[0].audioPackFormat is adm["AP_00010002"]

    def test_inconsistent_channel_ref(self, adm, chna):
        adm.addAudioTrackUID(
            AudioTrackUID(
                id="ATU_00000001",
                trackIndex=1,
                audioChannelFormat=adm["AC_00010001"],
                audioPackFormat=adm["AP_00010002"],
            )
        )
        chna.audioIDs = [AudioID(1, "ATU_00000001", "AC_00010002", "AP_00010002")]
        expected = (
            "Error in track UID ATU_00000001: CHNA entry references "
            "'AC_00010002' but AXML references 'AC_00010001'"
        )
        with pytest.raises(Exception, match=expected):
            load_chna_chunk(adm, chna)

    def test_adm_channel_chna_track(self, adm, chna):
        adm.addAudioTrackUID(
            AudioTrackUID(
                id="ATU_00000001",
                trackIndex=1,
                audioChannelFormat=adm["AC_00010001"],
                audioPackFormat=adm["AP_00010002"],
            )
        )
        chna.audioIDs = [AudioID(1, "ATU_00000001", "AT_00010001_01", "AP_00010002")]
        expected = (
            "Error in track UID ATU_00000001: CHNA entry references "
            "'AT_00010001_01' but AXML references 'AC_00010001'"
        )
        with pytest.raises(Exception, match=expected):
            load_chna_chunk(adm, chna)

    def test_adm_track_chna_channel(self, adm, chna):
        adm.addAudioTrackUID(
            AudioTrackUID(
                id="ATU_00000001",
                trackIndex=1,
                audioTrackFormat=adm["AT_00010001_01"],
                audioPackFormat=adm["AP_00010002"],
            )
        )
        chna.audioIDs = [AudioID(1, "ATU_00000001", "AC_00010001", "AP_00010002")]
        expected = (
            "Error in track UID ATU_00000001: CHNA entry references "
            "'AC_00010001' but AXML references 'AT_00010001_01'"
        )
        with pytest.raises(Exception, match=expected):
            load_chna_chunk(adm, chna)


class TestPopulate:
    def test_track_format(self, adm, chna):
        adm.addAudioTrackUID(
            AudioTrackUID(
                id="ATU_00000001",
                trackIndex=1,
                audioTrackFormat=adm["AT_00010001_01"],
                audioPackFormat=adm["AP_00010002"],
            )
        )

        populate_chna_chunk(chna, adm)
        assert chna.audioIDs == [
            AudioID(
                audioTrackUID="ATU_00000001",
                trackIndex=1,
                audioTrackFormatIDRef="AT_00010001_01",
                audioPackFormatIDRef="AP_00010002",
            )
        ]

    def test_missing_pack(self, adm, chna):
        adm.addAudioTrackUID(
            AudioTrackUID(
                id="ATU_00000002", trackIndex=2, audioTrackFormat=adm["AT_00010002_01"]
            )
        )

        populate_chna_chunk(chna, adm)
        assert chna.audioIDs == [
            AudioID(
                audioTrackUID="ATU_00000002",
                trackIndex=2,
                audioTrackFormatIDRef="AT_00010002_01",
                audioPackFormatIDRef=None,
            )
        ]

    def test_channel_format(self, adm, chna):
        adm.addAudioTrackUID(
            AudioTrackUID(
                id="ATU_00000003",
                trackIndex=3,
                audioChannelFormat=adm["AC_00010001"],
                audioPackFormat=adm["AP_00010002"],
            )
        )

        populate_chna_chunk(chna, adm)
        assert chna.audioIDs == [
            AudioID(
                audioTrackUID="ATU_00000003",
                trackIndex=3,
                audioTrackFormatIDRef="AC_00010001",
                audioPackFormatIDRef="AP_00010002",
            )
        ]

    def test_missing_track_index(self, adm, chna):
        adm.addAudioTrackUID(
            AudioTrackUID(
                id="ATU_00000001",
                audioTrackFormat=adm["AT_00010001_01"],
                audioPackFormat=adm["AP_00010002"],
            )
        )

        expected = "Track UID ATU_00000001 has no track number."
        with pytest.raises(Exception, match=expected):
            populate_chna_chunk(chna, adm)

    def test_missing_track_channel(self, adm, chna):
        adm.addAudioTrackUID(AudioTrackUID(id="ATU_00000001", trackIndex=1))

        expected = "Track UID ATU_00000001 has no track or channel format."
        with pytest.raises(Exception, match=expected):
            populate_chna_chunk(chna, adm)

    def test_both_track_channel(self, adm, chna):
        adm.addAudioTrackUID(
            AudioTrackUID(
                id="ATU_00000001",
                trackIndex=1,
                audioTrackFormat=adm["AT_00010001_01"],
                audioChannelFormat=adm["AC_00010001"],
                audioPackFormat=adm["AP_00010002"],
            )
        )

        expected = "Track UID ATU_00000001 has both track and channel formats."
        with pytest.raises(Exception, match=expected):
            populate_chna_chunk(chna, adm)
