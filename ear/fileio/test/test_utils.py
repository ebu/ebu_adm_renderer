import pytest
from ..adm.builder import ADMBuilder
from ..adm.generate_ids import generate_ids
from ..utils import RenderingItemHandler
from ..adm.exceptions import AdmError
from ..adm.elements import TypeDefinition, FormatDefinition


def test_basic():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    content = builder.create_content(audioContentName="MyContent", parent=programme)
    builder.create_item_objects(1, "MyObject 1", parent=content, block_formats=[])
    builder.create_item_objects(2, "MyObject 2", parent=content, block_formats=[])

    handler = RenderingItemHandler(builder.adm)

    assert len(handler.selected_items) == 2
    assert handler.selected_items[0].track_index == 1
    assert handler.selected_items[1].track_index == 2


def test_object_loop_exception():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    content = builder.create_content(audioContentName="MyContent", parent=programme)
    object_1 = builder.create_item_objects(track_index=1, name="MyObject 1", parent=content)
    object_2 = builder.create_item_objects(track_index=2, name="MyObject 2", parent=object_1.audio_object)
    builder.create_item_objects(track_index=3, name="MyObject 3", parent=object_2.audio_object)
    object_1.audio_object.audioObjects.append(object_1.audio_object)
    generate_ids(builder.adm)

    expected = "loop detected in audioObjects: .*$"
    with pytest.raises(AdmError, match=expected):
        RenderingItemHandler(builder.adm)


def test_multiple_track_formats_exception():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    object = builder.create_item_objects(track_index=1, name="MyObject")

    # create another stream format referencing the audioTrackFormat
    stream_format = builder.create_stream(audioStreamFormatName="MyStream 2", format=FormatDefinition.PCM)
    stream_format.audioTrackFormats.append(object.track_format)
    generate_ids(builder.adm)

    expected = ("don't know how to handle audioTrackFormat linked to by "
                "multiple audioStreamFormats")
    with pytest.raises(AdmError, match=expected):
        RenderingItemHandler(builder.adm)


def test_consistency_exception_1():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    object = builder.create_item_objects(track_index=1, name="MyObject")
    generate_ids(builder.adm)
    del object.stream_format.audioTrackFormats[:]

    expected = ("audioTrackUID 'ATU_[0-9A-Fa-f]{8}' references "
                "audioTrackFormat 'AT_[0-9A-Fa-f]{8}_[0-9A-Fa-f]{2}', "
                "which is not referenced by any audioStreamFormat")
    with pytest.raises(AdmError, match=expected):
        RenderingItemHandler(builder.adm)


def test_consistency_exception_2():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    object = builder.create_item_objects(track_index=1, name="MyObject")
    object.stream_format.audioChannelFormat = None
    generate_ids(builder.adm)

    expected = "no audioChannelFormat linked from audioStreamFormat AS_[0-9A-Fa-f]{8}"
    with pytest.raises(AdmError, match=expected):
        RenderingItemHandler(builder.adm)


def test_consistency_exception_3():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    object = builder.create_item_objects(track_index=1, name="MyObject")
    generate_ids(builder.adm)
    object.track_uid.trackIndex = None

    expected = ("audioTrackUID ATU_[0-9A-Fa-f]{8} does not have a track index, "
                "which should be specified in the CHNA chunk")
    with pytest.raises(AdmError, match=expected):
        RenderingItemHandler(builder.adm)


def test_consistency_exception_4():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    object = builder.create_item_objects(track_index=1, name="MyObject")
    del object.audio_object.audioPackFormats[:]
    builder.create_pack(audioPackFormatName="MyPack", type=TypeDefinition.Objects)
    generate_ids(builder.adm)

    expected = ("audioObject AO_[0-9A-Fa-f]{4} does not reference "
                "audioPackFormat AP_[0-9A-Fa-f]{8} which is referenced by "
                "audioTrackUID ATU_[0-9A-Fa-f]{8}")
    with pytest.raises(AdmError, match=expected):
        RenderingItemHandler(builder.adm)


def test_consistency_exception_5():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    object = builder.create_item_objects(track_index=1, name="MyObject")
    del object.pack_format.audioChannelFormats[:]
    builder.create_channel(audioChannelFormatName="MyChannel", type=TypeDefinition.Objects)
    generate_ids(builder.adm)

    expected = ("audioPackFormat AP_[0-9A-Fa-f]{8} does not reference "
                "audioChannelFormat AC_[0-9A-Fa-f]{8} which is referenced "
                "by audioTrackUID ATU_[0-9A-Fa-f]{8}")
    with pytest.raises(AdmError, match=expected):
        RenderingItemHandler(builder.adm)


def test_multiple_programmes():
    builder = ADMBuilder()
    programme_1 = builder.create_programme(audioProgrammeName="MyProgramme 1", id="APR_1001")
    programme_2 = builder.create_programme(audioProgrammeName="MyProgramme 2", id="APR_1002")
    content_1 = builder.create_content(audioContentName="MyContent 1", parent=programme_1)
    content_2 = builder.create_content(audioContentName="MyContent 2", parent=programme_2)
    builder.create_item_objects(1, "MyObject 1", parent=content_1, block_formats=[])
    builder.create_item_objects(2, "MyObject 2", parent=content_2, block_formats=[])
    builder.create_item_objects(3, "MyObject 3", parent=content_1, block_formats=[])
    builder.create_item_objects(4, "MyObject 4", parent=content_2, block_formats=[])

    expected = "more than one audioProgramme; selecting the one with the lowest id"
    with pytest.warns(UserWarning, match=expected):
        handler = RenderingItemHandler(builder.adm)

    assert len(handler.selected_items) == 2
    assert handler.selected_items[0].track_index == 1
    assert handler.selected_items[1].track_index == 3

    handler = RenderingItemHandler(builder.adm, "APR_1002")
    assert len(handler.selected_items) == 2
    assert handler.selected_items[0].track_index == 2
    assert handler.selected_items[1].track_index == 4


def test_complementary_objects():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme", id="APR_1001")
    content = builder.create_content(audioContentName="MyContent", parent=programme)
    object_1 = builder.create_item_objects(1, "MyObject 1", parent=content, block_formats=[])
    object_2 = builder.create_item_objects(2, "MyObject 2", parent=content, block_formats=[])
    object_3 = builder.create_item_objects(3, "MyObject 3", parent=content, block_formats=[])
    object_4 = builder.create_item_objects(4, "MyObject 4", parent=content, block_formats=[])
    generate_ids(builder.adm)

    object_1.audio_object.audioComplementaryObjects.append(object_2.audio_object)
    object_1.audio_object.audioComplementaryObjects.append(object_3.audio_object)
    object_1.audio_object.audioComplementaryObjects.append(object_4.audio_object)

    handler = RenderingItemHandler(builder.adm)
    assert len(handler.selected_items) == 1
    assert handler.selected_items[0].track_index == 1

    handler = RenderingItemHandler(
        builder.adm,
        selected_complementary_objects={object_1.audio_object.id: object_2.audio_object.id})
    assert len(handler.selected_items) == 1
    assert handler.selected_items[0].track_index == 2


def test_complementary_objects_with_referenced_objects_1():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme", id="APR_1001")
    content = builder.create_content(audioContentName="MyContent", parent=programme)
    object_1 = builder.create_object(parent=content, audioObjectName="MyObject 1")
    object_2 = builder.create_item_objects(1, "MyObject 2", parent=object_1, block_formats=[])  # noqa: F841
    object_3 = builder.create_object(parent=content, audioObjectName="MyObject 3")
    object_4 = builder.create_item_objects(2, "MyObject 4", parent=object_3, block_formats=[])  # noqa: F841
    generate_ids(builder.adm)

    object_1.audioComplementaryObjects.append(object_3)

    handler = RenderingItemHandler(builder.adm)
    assert len(handler.selected_items) == 1
    assert handler.selected_items[0].track_index == 1

    handler = RenderingItemHandler(
        builder.adm,
        selected_complementary_objects={object_1.id: object_3.id})
    assert len(handler.selected_items) == 1
    assert handler.selected_items[0].track_index == 2

    handler = RenderingItemHandler(
        builder.adm,
        selected_complementary_objects={object_1.id: object_1.id})
    assert len(handler.selected_items) == 1
    assert handler.selected_items[0].track_index == 1


def test_complementary_objects_with_referenced_objects_multiple_nesting():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme", id="APR_1001")
    content = builder.create_content(audioContentName="MyContent", parent=programme)
    object_1 = builder.create_object(parent=content, audioObjectName="MyObject 1")
    object_2 = builder.create_object(parent=object_1, audioObjectName="MyObject 2")
    object_3 = builder.create_object(parent=object_2, audioObjectName="MyObject 3")
    object_4 = builder.create_item_objects(1, "MyObject 4", parent=object_3, block_formats=[])  # noqa: F841
    object_5 = builder.create_object(parent=content, audioObjectName="MyObject 5")
    object_6 = builder.create_object(parent=object_5, audioObjectName="MyObject 6")
    object_7 = builder.create_object(parent=object_6, audioObjectName="MyObject 7")
    object_8 = builder.create_item_objects(2, "MyObject 8", parent=object_7, block_formats=[])  # noqa: F841
    generate_ids(builder.adm)

    object_1.audioComplementaryObjects.append(object_5)

    handler = RenderingItemHandler(builder.adm)
    assert len(handler.selected_items) == 1
    assert handler.selected_items[0].track_index == 1

    handler = RenderingItemHandler(
        builder.adm,
        selected_complementary_objects={object_1.id: object_5.id})
    assert len(handler.selected_items) == 1
    assert handler.selected_items[0].track_index == 2

    handler = RenderingItemHandler(
        builder.adm,
        selected_complementary_objects={object_1.id: object_1.id})
    assert len(handler.selected_items) == 1
    assert handler.selected_items[0].track_index == 1


def test_complementary_objects_without_audioprogramme():
    builder = ADMBuilder()
    object_1 = builder.create_object(audioObjectName="MyObject 1")
    object_2 = builder.create_object(parent=object_1, audioObjectName="MyObject 2")
    object_3 = builder.create_object(parent=object_2, audioObjectName="MyObject 3")
    object_4 = builder.create_item_objects(1, "MyObject 4", parent=object_3, block_formats=[])  # noqa: F841
    object_5 = builder.create_object(audioObjectName="MyObject 5")
    object_6 = builder.create_object(parent=object_5, audioObjectName="MyObject 6")
    object_7 = builder.create_object(parent=object_6, audioObjectName="MyObject 7")
    object_8 = builder.create_item_objects(2, "MyObject 8", parent=object_7, block_formats=[])  # noqa: F841
    generate_ids(builder.adm)

    object_1.audioComplementaryObjects.append(object_5)

    handler = RenderingItemHandler(builder.adm)
    assert len(handler.selected_items) == 1
    assert handler.selected_items[0].track_index == 1

    handler = RenderingItemHandler(
        builder.adm,
        selected_complementary_objects={object_1.id: object_5.id})
    assert len(handler.selected_items) == 1
    assert handler.selected_items[0].track_index == 2

    handler = RenderingItemHandler(
        builder.adm,
        selected_complementary_objects={object_1.id: object_1.id})
    assert len(handler.selected_items) == 1
    assert handler.selected_items[0].track_index == 1


@pytest.mark.parametrize("with_programme", [False, True])
@pytest.mark.parametrize("child_before_parent", [False, True])
def test_audio_object_importance_extraction(with_programme, child_before_parent):
    # The following structure will is created by the code below for testing.
    # Numbers indicate audioObject number/track index,
    # the number in brackets, if any, indicates the importance of this audioObject
    #
    #         +------------------------------------------+
    #         |               audioContent               |
    #         ----------------------|---------------------
    #        /          /           |          \          \
    #       /          /            |           \          \
    # +-----+      +-----+       +-----+      +-----+     +-----+
    # |  1  |      |  2  |       |  3  |      |  4  |     |  9  |
    # |     |     /| (8) |\      |     |\     | (4) |\    | (7) |
    # +-----+    / +-----+ \     +-----+ \    +-----+ \   +-----+
    #           /           \             \            \
    #        +-----+      +-----+       +-----+      +-----+
    #        |  5  |      |  6  |       |  7  |      |  8  |
    #        | (5) |      | (9) |       | (2) |      |     |
    #        +-----+      +-----+       +-----+      +-----+
    #
    # The expected "effective" importance for each audioObject is given
    # by the `expected_importances` map below

    builder = ADMBuilder()
    if with_programme:
        programme = builder.create_programme(audioProgrammeName="MyProgramme")
        content = builder.create_content(
            audioContentName="MyContent", parent=programme)
    else:
        content = None

    object_1 = builder.create_item_objects(1, "AudioObject1", parent=content, block_formats=[])  # noqa: F841

    object_2 = builder.create_object(
        parent=content, audioObjectName="AudioObject2", importance=8)
    object_5 = builder.create_item_objects(5, "AudioObject5", parent=object_2, block_formats=[])
    object_5.audio_object.importance = 5
    object_6 = builder.create_item_objects(6, "AudioObject6", parent=object_2, block_formats=[])
    object_6.audio_object.importance = 9

    object_3 = builder.create_object(
        parent=content, audioObjectName="AudioObject3")  # noqa: F841
    object_7 = builder.create_item_objects(7, "AudioObject7", parent=object_3, block_formats=[])
    object_7.audio_object.importance = 2

    object_4 = builder.create_object(
        parent=content, audioObjectName="AudioObject4", importance=4)
    object_8 = builder.create_item_objects(8, "AudioObject8", parent=object_4, block_formats=[])  # noqa: F841

    object_9 = builder.create_item_objects(9, "AudioObject9", block_formats=[], parent=content)
    object_9.audio_object.importance = 7

    if child_before_parent:
        builder.adm.audioObjects.reverse()

    generate_ids(builder.adm)

    handler = RenderingItemHandler(builder.adm)
    selected_items = handler.selected_items
    assert len(selected_items) == 6

    # lower importance values cascade to referenced objects so
    # all referenced audioObjects are removed as well, even if they themselves
    # may have a higher importance (i.e. removing a "branch from a tree")
    expected_importances = {1: None, 5: 5, 6: 8, 7: 2, 8: 4, 9: 7}
    for item in selected_items:
        expected = expected_importances[item.track_index]
        assert expected == item.importance.audio_object, "track {}".format(item.track_index)


def test_audio_pack_importance_extraction():
    # The following structure will is created by the code below for testing.
    # Numbers indicate audioPackFormat number/track index,
    # the number in brackets, if any, indicates the importance of this audioPackFormat
    #
    #    |            |             |           |          |
    #    |            |             |           |          |
    # +-----+      +-----+       +-----+      +-----+     +-----+
    # |  1  |      |  2  |       |  3  |      |  4  |     |  9  |
    # |     |     /| (8) |\      |     |\     | (4) |\    | (7) |
    # +-----+    / +-----+ \     +-----+ \    +-----+ \   +-----+
    #           /           \             \            \
    #        +-----+      +-----+       +-----+      +-----+
    #        |  5  |      |  6  |       |  7  |      |  8  |
    #        | (5) |      | (9) |       | (2) |      |     |
    #        +-----+      +-----+       +-----+      +-----+
    #
    # The expected "effective" importance for each audioPackFormat is given
    # by the `expected_importances` map below
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    content = builder.create_content(audioContentName="MyContent", parent=programme)  # noqa: F841

    # ok, what follows is a somewhat crude way to build nested audiopackformats:
    # using the helper function to create "items" with all elements,
    # we try to inject additional audioPackFormats inbetween
    # the audioObject and audioPackFormat that is created by create_item_objects.
    # We need the full set of stream/track/channel/etc. to be present, otherwise
    # it won't be picked up as RenderableItem. But we still try to keep this
    # test-code somewhat readable ...
    item_1 = builder.create_item_objects(1, "AudioObject1", block_formats=[])
    assert item_1.pack_format.importance is None
    item_5 = builder.create_item_objects(5, "AudioObject5", block_formats=[])
    item_5.pack_format.importance = 5
    item_6 = builder.create_item_objects(6, "AudioObject6", block_formats=[])
    item_6.pack_format.importance = 9
    item_7 = builder.create_item_objects(7, "AudioObject7", block_formats=[])
    item_7.pack_format.importance = 2
    item_8 = builder.create_item_objects(8, "AudioObject8", block_formats=[])
    assert item_8.pack_format.importance is None
    item_9 = builder.create_item_objects(9, "AudioObject9", block_formats=[])
    item_9.pack_format.importance = 7

    pack_5 = item_5.audio_object.audioPackFormats[0]
    del item_5.audio_object.audioPackFormats[:]
    pack_6 = item_6.audio_object.audioPackFormats[0]
    del item_6.audio_object.audioPackFormats[:]
    item_5.audio_object.audioTrackUIDs.append(item_6.audio_object.audioTrackUIDs[0])
    del item_6.audio_object.audioTrackUIDs[:]
    pack_2 = builder.create_pack(audioPackFormatName="Pack2", type=TypeDefinition.Objects,  # noqa: F841
                                 importance=8, audioPackFormats=[pack_5, pack_6], parent=item_5.audio_object)
    assert pack_6.importance == 9

    pack_7 = item_7.audio_object.audioPackFormats[0]
    del item_7.audio_object.audioPackFormats[:]
    pack_3 = builder.create_pack(audioPackFormatName="Pack3", type=TypeDefinition.Objects,  # noqa: F841
                                 importance=None, audioPackFormats=[pack_7], parent=item_7.audio_object)

    pack_8 = item_8.audio_object.audioPackFormats[0]
    del item_8.audio_object.audioPackFormats[:]
    pack_4 = builder.create_pack(audioPackFormatName="Pack4", type=TypeDefinition.Objects,  # noqa: F841
                                 importance=4, audioPackFormats=[pack_8], parent=item_8.audio_object)

    generate_ids(builder.adm)

    handler = RenderingItemHandler(builder.adm)
    selected_items = handler.selected_items
    assert len(selected_items) == 6

    expected_importances = {1: None, 5: 5, 6: 8, 7: 2, 8: 4, 9: 7}
    for item in selected_items:
        expected = expected_importances[item.track_index]
        assert expected == item.importance.audio_pack_format, "track {}".format(item.track_index)
