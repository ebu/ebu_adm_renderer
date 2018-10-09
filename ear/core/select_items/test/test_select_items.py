import pytest
from ....fileio.adm.builder import ADMBuilder
from ....fileio.adm.generate_ids import generate_ids
from .. import select_rendering_items
from ....fileio.adm.elements import TypeDefinition
from ....fileio.adm.exceptions import AdmError
from ...metadata_input import DirectTrackSpec, SilentTrackSpec


def test_basic():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    content = builder.create_content(audioContentName="MyContent", parent=programme)
    builder.create_item_objects(1, "MyObject 1", parent=content, block_formats=[])
    builder.create_item_objects(2, "MyObject 2", parent=content, block_formats=[])
    generate_ids(builder.adm)

    selected_items = select_rendering_items(builder.adm)

    assert len(selected_items) == 2
    assert selected_items[0].track_spec == DirectTrackSpec(1)
    assert selected_items[1].track_spec == DirectTrackSpec(2)


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
        selected_items = select_rendering_items(builder.adm)

    assert len(selected_items) == 2
    assert selected_items[0].track_spec == DirectTrackSpec(1)
    assert selected_items[1].track_spec == DirectTrackSpec(3)

    selected_items = select_rendering_items(builder.adm, builder.adm["APR_1002"])
    assert len(selected_items) == 2
    assert selected_items[0].track_spec == DirectTrackSpec(2)
    assert selected_items[1].track_spec == DirectTrackSpec(4)


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

    [item] = select_rendering_items(builder.adm)
    assert item.track_spec == DirectTrackSpec(1)

    [item] = select_rendering_items(
        builder.adm,
        selected_complementary_objects=[object_2.audio_object])
    assert item.track_spec == DirectTrackSpec(2)


def test_complementary_objects_multiple_selected():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme", id="APR_1001")
    content = builder.create_content(audioContentName="MyContent", parent=programme)
    object_1 = builder.create_item_objects(1, "MyObject 1", parent=content, block_formats=[])
    object_2 = builder.create_item_objects(2, "MyObject 2", parent=content, block_formats=[])
    object_3 = builder.create_item_objects(3, "MyObject 3", parent=content, block_formats=[])

    object_1.audio_object.audioComplementaryObjects.append(object_2.audio_object)
    object_1.audio_object.audioComplementaryObjects.append(object_3.audio_object)

    generate_ids(builder.adm)

    expected = ("multiple audioObjects selected from complementary "
                "object group '{object_1.id}': '{object_2.id}', '{object_3.id}'".format(
                    object_1=object_1.audio_object,
                    object_2=object_2.audio_object,
                    object_3=object_3.audio_object,
                ))

    with pytest.raises(AdmError, match=expected):
        select_rendering_items(
            builder.adm,
            selected_complementary_objects=[object_2.audio_object, object_3.audio_object])


def test_select_non_complementary():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme", id="APR_1001")
    content = builder.create_content(audioContentName="MyContent", parent=programme)
    object_1 = builder.create_item_objects(1, "MyObject 1", parent=content, block_formats=[])

    generate_ids(builder.adm)

    expected = ("selected audioObject {selected_obj.id} is not part "
                "of any complementary audioObject group".format(
                    selected_obj=object_1.audio_object,
                ))

    with pytest.raises(AdmError, match=expected):
        select_rendering_items(
            builder.adm,
            selected_complementary_objects=[object_1.audio_object])


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

    [item] = select_rendering_items(builder.adm)
    assert item.track_spec == DirectTrackSpec(1)

    [item] = select_rendering_items(
        builder.adm,
        selected_complementary_objects=[object_3])
    assert item.track_spec == DirectTrackSpec(2)

    [item] = select_rendering_items(
        builder.adm,
        selected_complementary_objects=[object_1])
    assert item.track_spec == DirectTrackSpec(1)


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

    [item] = select_rendering_items(builder.adm)
    assert item.track_spec == DirectTrackSpec(1)

    [item] = select_rendering_items(
        builder.adm,
        selected_complementary_objects=[object_5])
    assert item.track_spec == DirectTrackSpec(2)

    [item] = select_rendering_items(
        builder.adm,
        selected_complementary_objects=[object_1])
    assert item.track_spec == DirectTrackSpec(1)


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

    [item] = select_rendering_items(builder.adm)
    assert item.track_spec == DirectTrackSpec(1)

    [item] = select_rendering_items(
        builder.adm,
        selected_complementary_objects=[object_5])
    assert item.track_spec == DirectTrackSpec(2)

    [item] = select_rendering_items(
        builder.adm,
        selected_complementary_objects=[object_1])
    assert item.track_spec == DirectTrackSpec(1)


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

    selected_items = select_rendering_items(builder.adm)
    assert len(selected_items) == 6

    # lower importance values cascade to referenced objects so
    # all referenced audioObjects are removed as well, even if they themselves
    # may have a higher importance (i.e. removing a "branch from a tree")
    expected_importances = {1: None, 5: 5, 6: 8, 7: 2, 8: 4, 9: 7}
    for item in selected_items:
        expected = expected_importances[item.track_spec.track_index]
        assert expected == item.importance.audio_object, "track {}".format(item.track_spec.track_index)


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

    selected_items = select_rendering_items(builder.adm)
    assert len(selected_items) == 6

    expected_importances = {1: None, 5: 5, 6: 8, 7: 2, 8: 4, 9: 7}
    for item in selected_items:
        expected = expected_importances[item.track_spec.track_index]
        assert expected == item.importance.audio_pack_format, "track {}".format(item.track_spec.track_index)


def test_no_programme_content_object():
    builder = ADMBuilder()
    builder.load_common_definitions()

    builder.create_track_uid(
        trackIndex=1,
        audioTrackFormat=builder.adm.lookup_element("AT_00010003_01"),
        audioPackFormat=builder.adm.lookup_element("AP_00010001"),
    )

    generate_ids(builder.adm)

    [item] = select_rendering_items(builder.adm)

    assert item.track_spec == DirectTrackSpec(0)


def test_silent_track_mono():
    """Test an object referencing a mono pack format with a single silent track."""
    builder = ADMBuilder()
    builder.load_common_definitions()
    builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent")
    builder.create_object(audioObjectName="MyObject", audioTrackUIDs=[None],
                          audioPackFormats=[builder.adm["AP_00010001"]])
    generate_ids(builder.adm)

    [item] = select_rendering_items(builder.adm)

    assert item.track_spec == SilentTrackSpec()
    assert item.adm_path.audioChannelFormat is builder.adm["AC_00010003"]


def test_silent_track_stereo():
    """Test an object referencing a stereo pack format with one real track and
    one silent one.
    """
    builder = ADMBuilder()
    builder.load_common_definitions()
    builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent")

    atu = builder.create_track_uid(
        trackIndex=1,
        audioTrackFormat=builder.adm.lookup_element("AT_00010001_01"),
        audioPackFormat=builder.adm.lookup_element("AP_00010002"),
    )

    builder.create_object(audioObjectName="MyObject", audioTrackUIDs=[atu, None],
                          audioPackFormats=[builder.adm["AP_00010002"]])
    generate_ids(builder.adm)

    selected_items = select_rendering_items(builder.adm)
    [item_l, item_r] = sorted(selected_items, key=lambda item: item.adm_path.audioChannelFormat.id)

    assert item_l.track_spec == DirectTrackSpec(0)
    assert item_l.adm_path.audioChannelFormat is builder.adm["AC_00010001"]
    assert item_r.track_spec == SilentTrackSpec()
    assert item_r.adm_path.audioChannelFormat is builder.adm["AC_00010002"]
