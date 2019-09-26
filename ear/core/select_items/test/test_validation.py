from fractions import Fraction
import pytest
from ....fileio.adm.builder import ADMBuilder
from ....fileio.adm.elements import (TypeDefinition, Frequency,
                                     AudioBlockFormatHoa, AudioBlockFormatObjects,
                                     ObjectPolarPosition, ObjectCartesianPosition)
from ....fileio.adm.exceptions import AdmError
from ....fileio.adm.generate_ids import generate_ids
from ....fileio.adm.exceptions import AdmFormatRefError
from .. import select_rendering_items
from .test_matrix import EncodeDecodeBuilder
from .test_hoa import HOABuilder


def check_select_items_raises(builder, expected_fmt, generate_ids=True, *args, **kwargs):
    """Check that running select_rendering_items on builder.adm raises an
    AdmError with the expected format.

    Format arguments are passed in seperately so that this can generate IDs.
    """
    from ....fileio.adm.generate_ids import generate_ids as run_generate_ids
    if generate_ids:
        run_generate_ids(builder.adm)

    expected = expected_fmt.format(*args, **kwargs)

    with pytest.raises(AdmError, match=expected):
        select_rendering_items(builder.adm)


def test_object_loop_exception():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    content = builder.create_content(audioContentName="MyContent", parent=programme)
    object_1 = builder.create_item_objects(track_index=1, name="MyObject 1", parent=content)
    object_2 = builder.create_item_objects(track_index=2, name="MyObject 2", parent=object_1.audio_object)
    builder.create_item_objects(track_index=3, name="MyObject 3", parent=object_2.audio_object)
    object_1.audio_object.audioObjects.append(object_1.audio_object)

    check_select_items_raises(
        builder,
        "loop detected in audioObjects: .*$")


def test_pack_loop_exception():
    builder = ADMBuilder()
    pack_1 = builder.create_pack(parent=None, audioPackFormatName="pack_1", type=TypeDefinition.Objects)
    pack_2 = builder.create_pack(parent=pack_1, audioPackFormatName="pack_2", type=TypeDefinition.Objects)
    pack_2.audioPackFormats.append(pack_1)

    check_select_items_raises(
        builder,
        "loop detected in audioPackFormats: .*$")


def test_pack_diamond_exception():
    # test the folowing structure, with references pointing down:
    #
    #    1   2
    #     \ /
    #      p
    #     / \
    #    a   b
    #     \ /
    #      c

    builder = ADMBuilder()
    pack_1 = builder.create_pack(parent=None, audioPackFormatName="pack_1", type=TypeDefinition.Objects)
    pack_2 = builder.create_pack(parent=None, audioPackFormatName="pack_2", type=TypeDefinition.Objects)
    pack_p = builder.create_pack(parent=None, audioPackFormatName="pack_p", type=TypeDefinition.Objects)
    pack_1.audioPackFormats.append(pack_p)
    pack_2.audioPackFormats.append(pack_p)
    pack_a = builder.create_pack(parent=pack_p, audioPackFormatName="pack_a", type=TypeDefinition.Objects)
    pack_b = builder.create_pack(parent=pack_p, audioPackFormatName="pack_b", type=TypeDefinition.Objects)
    pack_c = builder.create_pack(parent=None, audioPackFormatName="pack_c", type=TypeDefinition.Objects)
    pack_a.audioPackFormats.append(pack_c)
    pack_b.audioPackFormats.append(pack_c)

    check_select_items_raises(
        builder,
        "audioPackFormat '{pack_c.id}' is included more than once in audioPackFormat '{pack_p.id}' via paths "
        "('{pack_p.id}' -> '{pack_a.id}' -> '{pack_c.id}' and '{pack_p.id}' -> '{pack_b.id}' -> '{pack_c.id}'"
        "|'{pack_p.id}' -> '{pack_b.id}' -> '{pack_c.id}' and '{pack_p.id}' -> '{pack_a.id}' -> '{pack_c.id}')",
        pack_p=pack_p, pack_a=pack_a, pack_b=pack_b, pack_c=pack_c)


def test_pack_channel_exception():
    builder = ADMBuilder()
    pack = builder.create_pack(parent=None, audioPackFormatName="pack_1", type=TypeDefinition.Objects)
    channel = builder.create_channel(parent=pack, audioChannelFormatName="channel_1", type=TypeDefinition.Objects)
    pack.audioChannelFormats.append(channel)

    check_select_items_raises(
        builder,
        "audioChannelFormat '{channel.id}' is included more than once in audioPackFormat '{pack.id}'",
        channel=channel, pack=pack)


def test_pack_pack_type_exception():
    builder = ADMBuilder()
    pack = builder.create_pack(parent=None, audioPackFormatName="pack_1", type=TypeDefinition.Objects)
    sub_pack = builder.create_pack(parent=pack, audioPackFormatName="pack_2", type=TypeDefinition.DirectSpeakers)

    check_select_items_raises(
        builder,
        "audioPackFormat {apf.id} has type Objects, but contains audioPackFormat {sub_apf.id} with type DirectSpeakers",
        apf=pack, sub_apf=sub_pack)


def test_pack_channel_type_exception():
    builder = ADMBuilder()
    pack = builder.create_pack(parent=None, audioPackFormatName="pack_1", type=TypeDefinition.DirectSpeakers)
    sub_pack = builder.create_pack(parent=pack, audioPackFormatName="pack_2", type=TypeDefinition.DirectSpeakers)
    channel = builder.create_channel(parent=sub_pack, audioChannelFormatName="channel_1", type=TypeDefinition.Objects)

    check_select_items_raises(
        builder,
        "audioPackFormat {sub_apf.id} has type DirectSpeakers, but contains audioChannelFormat {acf.id} with type Objects",
        sub_apf=sub_pack, acf=channel)


def test_audioTrackUID_pack_exception():
    builder = ADMBuilder()
    builder.load_common_definitions()

    atu = builder.create_track_uid(trackIndex=1, audioTrackFormat=builder.adm["AT_00010001_01"])

    check_select_items_raises(
        builder,
        "audioTrackUID {atu.id} does not have an audioPackFormat reference. "
        "This may be used in coded formats, which are not currently supported.",
        atu=atu)


def test_audioTrackUID_trackFormat_exception():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    item = builder.create_item_objects(track_index=1, name="MyObject")

    item.track_uid.audioTrackFormat = None

    check_select_items_raises(
        builder,
        "audioTrackUID {atu.id} is not linked to an audioTrackFormat",
        atu=item.track_uid)


def test_consistency_exception_1():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    item = builder.create_item_objects(track_index=1, name="MyObject")

    generate_ids(builder.adm)

    item.track_format.audioStreamFormat = None

    check_select_items_raises(
        builder,
        "audioTrackFormat {atf.id} is not linked to an audioStreamFormat",
        atf=item.track_format,
        generate_ids=False)


def test_consistency_exception_2():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    item = builder.create_item_objects(track_index=1, name="MyObject")
    item.stream_format.audioChannelFormat = None
    item.stream_format.audioPackFormat = item.pack_format

    check_select_items_raises(
        builder,
        "audioStreamFormat {asf.id} does not have an audioChannelFormat reference. "
        "This may be used in coded formats, which are not currently supported.",
        asf=item.stream_format)


def test_consistency_exception_3():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    item = builder.create_item_objects(track_index=1, name="MyObject")
    item.track_uid.trackIndex = None

    check_select_items_raises(
        builder,
        "audioTrackUID {atu.id} does not have a track index, "
        "which should be specified in the CHNA chunk",
        atu=item.track_uid)


def test_consistency_exception_4():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    item = builder.create_item_objects(track_index=1, name="MyObject")
    del item.audio_object.audioPackFormats[:]
    builder.create_pack(audioPackFormatName="MyPack", type=TypeDefinition.Objects)

    generate_ids(builder.adm)

    with pytest.raises(AdmFormatRefError) as excinfo:
        select_rendering_items(builder.adm)

    assert (excinfo.value.message ==
            "Conflicting format references found in audioObject {obj.id}".format(
                obj=item.audio_object,
            ))
    assert (excinfo.value.reasons ==
            ["audioPackFormat {apf.id} referenced from audioTrackUID {atu.id} "
             "is not referenced from audioObject".format(
                 apf=item.pack_format,
                 atu=item.track_uid,
             )])


def test_consistency_exception_5():
    builder = ADMBuilder()
    programme = builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent", parent=programme)
    item = builder.create_item_objects(track_index=1, name="MyObject")
    del item.pack_format.audioChannelFormats[:]
    builder.create_channel(audioChannelFormatName="MyChannel", type=TypeDefinition.Objects)

    generate_ids(builder.adm)

    with pytest.raises(AdmFormatRefError) as excinfo:
        select_rendering_items(builder.adm)

    assert (excinfo.value.message ==
            "Conflicting format references found in audioObject {obj.id}".format(
                obj=item.audio_object,
            ))
    assert (excinfo.value.reasons ==
            ["audioPackFormat {apf.id} does not reference audioChannelFormat {acf.id} "
             "which is referenced by audioTrackUID {atu.id} "
             "via audioTrackFormat and audioStreamFormat".format(
                 apf=item.pack_format,
                 acf=item.channel_format,
                 atu=item.track_uid,
             )])


def test_Objects_validation_no_frequency():
    builder = ADMBuilder()
    acf = builder.create_channel(type=TypeDefinition.Objects, audioChannelFormatName="foo",
                                 frequency=Frequency(lowPass=120.0),
                                 audioBlockFormats=[
                                     AudioBlockFormatObjects(rtime=Fraction(0), duration=Fraction(1),
                                                             position=ObjectPolarPosition(0.0, 0.0, 1.0)),
                                 ])

    check_select_items_raises(
        builder,
        "Objects audioChannelFormats must not have frequency information, but {acf.id} does",
        acf=acf)


def test_Objects_validation_cartesian_mismatch():
    for cartesian, position in [(True, ObjectPolarPosition(0.0, 0.0, 1.0)),
                                (False, ObjectCartesianPosition(0.0, 1.0, 0.0))]:
        builder = ADMBuilder()
        abf = AudioBlockFormatObjects(rtime=Fraction(0), duration=Fraction(1),
                                      cartesian=cartesian,
                                      position=position)
        builder.create_channel(type=TypeDefinition.Objects, audioChannelFormatName="foo",
                               audioBlockFormats=[abf],
                               )

        check_select_items_raises(
            builder,
            "mismatch between cartesian element and coordinate type used in {abf.id}",
            abf=abf)


def test_HOA_validation_one_block_format():
    builder = ADMBuilder()
    acf = builder.create_channel(type=TypeDefinition.HOA, audioChannelFormatName="foo", audioBlockFormats=[
        AudioBlockFormatHoa(rtime=Fraction(0), duration=Fraction(1), order=1, degree=1),
        AudioBlockFormatHoa(rtime=Fraction(1), duration=Fraction(1), order=1, degree=1),
    ])

    check_select_items_raises(
        builder,
        "HOA audioChannelFormats must have exactly one block format, but {acf.id} has 2",
        acf=acf)


def test_HOA_validation_no_frequency():
    builder = ADMBuilder()
    acf = builder.create_channel(type=TypeDefinition.HOA, audioChannelFormatName="foo",
                                 frequency=Frequency(lowPass=120.0),
                                 audioBlockFormats=[
                                     AudioBlockFormatHoa(rtime=Fraction(0), duration=Fraction(1), order=1, degree=1),
                                 ])

    check_select_items_raises(
        builder,
        "HOA audioChannelFormats must not have frequency information, but {acf.id} does",
        acf=acf)


def test_hoa_equation_error():
    builder = HOABuilder()

    channel_format = builder.first_pack.audioChannelFormats[0]
    [block_format] = channel_format.audioBlockFormats
    block_format.equation = "foo"

    check_select_items_raises(
        builder,
        "HOA audioBlockFormat {abf.id} has an 'equation' attribute, which overrides the "
        "'order' and 'degree' attributes but has no defined format.",
        abf=block_format)


def test_hoa_missing_order():
    builder = HOABuilder()

    channel_format = builder.first_pack.audioChannelFormats[0]
    [block_format] = channel_format.audioBlockFormats
    block_format.order = None

    check_select_items_raises(
        builder,
        "HOA audioBlockFormat {abf.id} has no 'order' attribute",
        abf=block_format)


def test_hoa_missing_degree():
    builder = HOABuilder()
    channel_format = builder.first_pack.audioChannelFormats[0]
    [block_format] = channel_format.audioBlockFormats
    block_format.degree = None

    check_select_items_raises(
        builder,
        "HOA audioBlockFormat {abf.id} has no 'degree' attribute",
        abf=block_format)


def test_hoa_duplicate_order_degree():
    builder = HOABuilder()

    channel_format = builder.first_pack.audioChannelFormats[0]
    [block_format] = channel_format.audioBlockFormats
    block_format.order = 1

    check_select_items_raises(
        builder,
        "duplicate orders and degrees found in HOA audioPackFormat {apf.id}",
        apf=builder.first_pack)


def test_hoa_pack_channel_mismatch():
    builder = HOABuilder()

    channel_format = builder.first_pack.audioChannelFormats[0]
    [block_format] = channel_format.audioBlockFormats
    block_format.normalization = "N3D"
    builder.first_pack.normalization = "SN3D"

    check_select_items_raises(
        builder,
        "Conflicting normalization values in path from {apf.id} to {acf.id}",
        apf=builder.first_pack, acf=channel_format)


def test_hoa_channel_format_mismatch():
    builder = HOABuilder()

    channel_format = builder.first_pack.audioChannelFormats[0]
    [block_format] = channel_format.audioBlockFormats
    block_format.normalization = "N3D"

    check_select_items_raises(
        builder,
        "All HOA audioChannelFormats in a single audioPackFormat must "
        "share the same normalization value, but {acf_a.id} and {acf_b.id} differ.",
        acf_a=builder.first_pack.audioChannelFormats[0],
        acf_b=builder.first_pack.audioChannelFormats[1])


def test_matrix_one_block_format():
    builder = EncodeDecodeBuilder()
    del builder.encode_mid.audioBlockFormats[0]

    check_select_items_raises(
        builder,
        "matrix audioChannelFormat {acf.id} does not have a single audioBlockFormat",
        acf=builder.encode_mid)


def test_matrix_timing():
    builder = EncodeDecodeBuilder()
    builder.encode_mid.audioBlockFormats[0].rtime = Fraction(0)
    builder.encode_mid.audioBlockFormats[0].duration = Fraction(1)

    check_select_items_raises(
        builder,
        "matrix audioBlockFormat {block_format.id} has rtime or duration attributes",
        block_format=builder.encode_mid.audioBlockFormats[0])


@pytest.mark.parametrize("name,value", [("gainVar", "gain"),
                                        ("phaseVar", "phase"),
                                        ("phase", 90.0),
                                        ("delayVar", "delay"),
                                        ])
def test_matrix_unsupported_params(name, value):
    builder = EncodeDecodeBuilder()
    setattr(builder.encode_mid.audioBlockFormats[0].matrix[0], name, value)

    check_select_items_raises(
        builder,
        "{name} attribute used in {block_format.id} is not supported",
        block_format=builder.encode_mid.audioBlockFormats[0],
        name=name)


def test_matrix_delay():
    builder = EncodeDecodeBuilder()
    builder.encode_mid.audioBlockFormats[0].matrix[0].delay = -1.0

    check_select_items_raises(
        builder,
        "delay attribute used in {block_format.id} must be non-negative",
        block_format=builder.encode_mid.audioBlockFormats[0])


def test_matrix_missing_input_output():
    builder = EncodeDecodeBuilder()
    builder.encode_pack.inputPackFormat = None

    check_select_items_raises(
        builder,
        "matrix audioPackFormat {apf.id} must have an input or output audioPackFormat reference",
        apf=builder.encode_pack)


def test_matrix_input_type():
    builder = EncodeDecodeBuilder()
    builder.encode_pack.inputPackFormat = builder.decode_pack

    check_select_items_raises(
        builder,
        "audioPackFormat inputPackFormat reference in {apf.id} must not be of Matrix type",
        apf=builder.encode_pack)


def test_matrix_output_type():
    builder = EncodeDecodeBuilder()
    builder.decode_pack.outputPackFormat = builder.encode_pack

    check_select_items_raises(
        builder,
        "audioPackFormat outputPackFormat reference in {apf.id} must not be of Matrix type",
        apf=builder.decode_pack)


def test_matrix_has_encode():
    builder = EncodeDecodeBuilder()
    builder.encode_pack.encodePackFormats.append(builder.decode_pack)

    check_select_items_raises(
        builder,
        "audioPackFormat {apf.id} has encode pack formats but is not a decode matrix",
        apf=builder.encode_pack)


def test_matrix_wrong_num_encode():
    builder = EncodeDecodeBuilder()
    del builder.decode_pack.encodePackFormats[0]

    check_select_items_raises(
        builder,
        "decode matrix audioPackFormats must have 1 encode matrix reference, but {apf.id} has 0",
        apf=builder.decode_pack)


def test_matrix_wrong_encode_type():
    builder = EncodeDecodeBuilder()
    builder.decode_pack.encodePackFormats = [builder.stereo_pack]

    check_select_items_raises(
        builder,
        "audioPackFormat {apf.id} references non-Matrix type audioPackFormat "
        "{apf_encode.id} as an encode matrix",
        apf=builder.decode_pack, apf_encode=builder.stereo_pack)


def test_matrix_encode_not_encode():
    builder = EncodeDecodeBuilder()
    builder.decode_pack.encodePackFormats = [builder.decode_pack]

    check_select_items_raises(
        builder,
        "audioPackFormat {apf.id} references non-encode type audioPackFormat "
        "{apf_encode.id} as an encode matrix",
        apf=builder.decode_pack, apf_encode=builder.decode_pack)


def test_matrix_nested_packs():
    builder = EncodeDecodeBuilder()
    builder.decode_pack.audioPackFormats.append(builder.encode_pack)

    check_select_items_raises(
        builder,
        "matrix audioPackFormat {apf.id} has audioPackFormat references",
        apf=builder.decode_pack)


def test_matrix_inputChannelFormat_error():
    builder = EncodeDecodeBuilder()
    centre_channel = builder.adm["AC_00010003"]

    [bf] = builder.encode_mid.audioBlockFormats
    bf.matrix[0].inputChannelFormat = centre_channel

    check_select_items_raises(
        builder,
        "matrix in audioChannelFormat {matrix_channel.id} references input audioChannelFormat "
        "{input_channel.id} which is not in the input or encode audioPackFormat {input_pack.id}",
        matrix_channel=builder.encode_mid,
        input_channel=centre_channel,
        input_pack=builder.stereo_pack)


def test_matrix_missing_outputChannelFormat_element():
    builder = EncodeDecodeBuilder()

    [bf] = builder.decode_left.audioBlockFormats
    bf.outputChannelFormat = None

    check_select_items_raises(
        builder,
        "outputChannelFormat reference is missing in direct or "
        "decode matrix block format {block_format.id}",
        block_format=bf)


def test_matrix_duplicate_outputChannelFormat():
    builder = EncodeDecodeBuilder()

    [bf] = builder.decode_left.audioBlockFormats
    bf.outputChannelFormat = builder.right_channel

    check_select_items_raises(
        builder,
        "duplicate outputChannelFormat reference to {output_channel.id} "
        "in matrix audioPackFormat {matrix_pack.id}",
        output_channel=builder.right_channel,
        matrix_pack=builder.decode_pack)


def test_matrix_wrong_outputChannelFormat():
    builder = EncodeDecodeBuilder()
    centre_channel = builder.adm["AC_00010003"]

    [bf] = builder.decode_left.audioBlockFormats
    bf.outputChannelFormat = centre_channel

    check_select_items_raises(
        builder,
        "matrix audioChannelFormat {matrix_channel.id} references audioChannelFormat "
        "{output_channel.id} which is not in the output audioPackFormat of {matrix_pack.id}",
        matrix_channel=builder.decode_left,
        output_channel=centre_channel,
        matrix_pack=builder.decode_pack)


def test_matrix_missing_outputChannelFormat_reference():
    builder = EncodeDecodeBuilder()
    del builder.decode_pack.audioChannelFormats[1]

    check_select_items_raises(
        builder,
        "matrix audioPackFormat {matrix_pack.id} does not reference audioChannelFormat "
        "{output_pack_channel.id} of output audioPackFormat",
        output_pack_channel=builder.right_channel,
        matrix_pack=builder.decode_pack)


def test_matrix_non_matrix_with_inputPackFormat():
    builder = EncodeDecodeBuilder()
    builder.adm["AP_00010001"].inputPackFormat = builder.adm["AP_00010002"]
    check_select_items_raises(
        builder,
        "non-matrix audioPackFormat {apf.id} has inputPackFormat reference",
        apf=builder.adm["AP_00010001"])


def test_matrix_non_matrix_with_outputPackFormat():
    builder = EncodeDecodeBuilder()
    builder.adm["AP_00010001"].outputPackFormat = builder.adm["AP_00010002"]

    check_select_items_raises(
        builder,
        "non-matrix audioPackFormat {apf.id} has outputPackFormat reference",
        apf=builder.adm["AP_00010001"])


def test_matrix_non_matrix_with_encodePackFormats():
    builder = EncodeDecodeBuilder()
    builder.adm["AP_00010001"].encodePackFormats = [builder.adm["AP_00010002"]]

    check_select_items_raises(
        builder,
        "non-matrix audioPackFormat {apf.id} has encodePackFormat references",
        apf=builder.adm["AP_00010001"])
