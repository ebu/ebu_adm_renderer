from ..builder import ADMBuilder
from ..elements import AlternativeValueSet, AudioBlockFormatObjects, ObjectPolarPosition
from ..generate_ids import generate_ids


def test_generate_ids():
    builder = ADMBuilder()

    programme = builder.create_programme(audioProgrammeName="programme")
    content = builder.create_content(audioContentName="content")

    item = builder.create_item_objects(
        1,
        "object",
        parent=content,
        block_formats=[
            AudioBlockFormatObjects(position=ObjectPolarPosition(0.0, 0.0, 1.0)),
        ],
    )

    item.audio_object.alternativeValueSets = [AlternativeValueSet()]

    generate_ids(builder.adm)

    assert builder.adm.audioProgrammes[0].id == "APR_1001"

    assert builder.adm.audioContents[0].id == "ACO_1001"

    ao = builder.adm.audioObjects[0]
    assert ao.id == "AO_1001"
    assert ao.alternativeValueSets[0].id == "AVS_1001_0001"

    assert builder.adm.audioPackFormats[0].id == "AP_00031001"

    acf = builder.adm.audioChannelFormats[0]
    assert acf.id == "AC_00031001"
    assert acf.audioBlockFormats[0].id == "AB_00031001_00000001"

    assert builder.adm.audioStreamFormats[0].id == "AS_00031001"

    assert builder.adm.audioTrackFormats[0].id == "AT_00031001_01"

    assert builder.adm.audioTrackUIDs[0].id == "ATU_00000001"
