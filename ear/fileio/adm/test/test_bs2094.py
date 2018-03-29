from ..adm import ADM
from ..common_definitions import load_common_definitions


def test_load_common_definitions():
    adm = ADM()
    load_common_definitions(adm)

    assert len(adm.audioChannelFormats) == 300
    assert len(adm.audioPackFormats) == 43
    assert len(adm.audioTrackFormats) == 300
    assert len(adm.audioStreamFormats) == 300
    assert len(list(adm.elements)) == (300 + 43 + 300 + 300)
