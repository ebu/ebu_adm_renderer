import pytest
from ....fileio.adm.builder import ADMBuilder
from ....fileio.adm.generate_ids import generate_ids
from .. import select_rendering_items
from ....fileio.adm.elements import TypeDefinition, FormatDefinition, AudioBlockFormatMatrix, MatrixCoefficient
from ...metadata_input import DirectTrackSpec, MixTrackSpec, MatrixCoefficientTrackSpec


@pytest.mark.parametrize("usage", ["direct", "pre_applied", "mono"])
def test_openhouse(usage):
    builder = ADMBuilder()
    builder.load_common_definitions()

    mono_pack = builder.adm["AP_00010001"]
    treo_pack = builder.create_pack(audioPackFormatName="treo", type=TypeDefinition.DirectSpeakers,
                                    audioChannelFormats=[builder.adm["AC_00010001"],
                                                         builder.adm["AC_00010002"],
                                                         builder.adm["AC_00010003"],
                                                         ])

    matrix_pack = builder.create_pack(
        audioPackFormatName="matrix", type=TypeDefinition.Matrix,
        inputPackFormat=mono_pack, outputPackFormat=treo_pack,
    )

    mc1 = MatrixCoefficient(inputChannelFormat=builder.adm["AC_00010003"], gain=0.3)
    channel_left = builder.create_channel(
        matrix_pack, audioChannelFormatName="matrix_c1", type=TypeDefinition.Matrix,
        audioBlockFormats=[AudioBlockFormatMatrix(
            outputChannelFormat=builder.adm["AC_00010001"],
            matrix=[mc1])])

    mc2 = MatrixCoefficient(inputChannelFormat=builder.adm["AC_00010003"], gain=0.3)
    channel_right = builder.create_channel(
        matrix_pack, audioChannelFormatName="matrix_c2", type=TypeDefinition.Matrix,
        audioBlockFormats=[AudioBlockFormatMatrix(
            outputChannelFormat=builder.adm["AC_00010002"],
            matrix=[mc2])])

    mc3 = MatrixCoefficient(inputChannelFormat=builder.adm["AC_00010003"], gain=1.0)
    channel_centre = builder.create_channel(
        matrix_pack, audioChannelFormatName="matrix_c3", type=TypeDefinition.Matrix,
        audioBlockFormats=[AudioBlockFormatMatrix(
            outputChannelFormat=builder.adm["AC_00010003"],
            matrix=[mc3])])

    builder.create_stream(audioStreamFormatName="left PCM", format=FormatDefinition.PCM,
                          audioChannelFormat=channel_left)
    left_track = builder.create_track(audioTrackFormatName="left PCM", format=FormatDefinition.PCM)

    builder.create_stream(audioStreamFormatName="right PCM", format=FormatDefinition.PCM,
                          audioChannelFormat=channel_right)
    right_track = builder.create_track(audioTrackFormatName="right PCM", format=FormatDefinition.PCM)

    builder.create_stream(audioStreamFormatName="centre PCM", format=FormatDefinition.PCM,
                          audioChannelFormat=channel_centre)
    centre_track = builder.create_track(audioTrackFormatName="centre PCM", format=FormatDefinition.PCM)

    builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent")

    if usage == "direct":
        builder.create_object(audioObjectName="MyObject",
                              audioPackFormats=[matrix_pack])
        builder.create_track_uid(trackIndex=1,
                                 audioTrackFormat=builder.adm["AT_00010003_01"],
                                 audioPackFormat=matrix_pack)

        expected = [
            ("AC_00010001", MixTrackSpec([MatrixCoefficientTrackSpec(DirectTrackSpec(0), mc1)])),
            ("AC_00010002", MixTrackSpec([MatrixCoefficientTrackSpec(DirectTrackSpec(0), mc2)])),
            ("AC_00010003", MixTrackSpec([MatrixCoefficientTrackSpec(DirectTrackSpec(0), mc3)])),
        ]
    elif usage == "pre_applied":
        builder.create_object(audioObjectName="MyObject",
                              audioPackFormats=[matrix_pack])
        builder.create_track_uid(trackIndex=1,
                                 audioTrackFormat=left_track,
                                 audioPackFormat=matrix_pack)
        builder.create_track_uid(trackIndex=2,
                                 audioTrackFormat=right_track,
                                 audioPackFormat=matrix_pack)
        builder.create_track_uid(trackIndex=3,
                                 audioTrackFormat=centre_track,
                                 audioPackFormat=matrix_pack)

        expected = [
            ("AC_00010001", DirectTrackSpec(0)),
            ("AC_00010002", DirectTrackSpec(1)),
            ("AC_00010003", DirectTrackSpec(2)),
        ]
    elif usage == "mono":
        builder.create_object(audioObjectName="MyObject",
                              audioPackFormats=[mono_pack])
        builder.create_track_uid(trackIndex=1,
                                 audioTrackFormat=builder.adm["AT_00010003_01"],
                                 audioPackFormat=mono_pack)
        expected = [
            ("AC_00010003", DirectTrackSpec(0)),
        ]
    else:
        assert False

    generate_ids(builder.adm)

    selected_items = select_rendering_items(builder.adm)

    results = sorted((item.adm_path.audioChannelFormat.id, item.track_spec)
                     for item in selected_items)

    assert results == expected


class EncodeDecodeBuilder(ADMBuilder):
    """ADMBuilder with pre-defined encode and decode matrix, with references to
    the various components"""

    def __init__(self):
        super(EncodeDecodeBuilder, self).__init__()
        self.load_common_definitions()

        self.stereo_pack = self.adm["AP_00010002"]
        self.left_channel = self.adm["AC_00010001"]
        self.right_channel = self.adm["AC_00010002"]

        self.encode_pack = self.create_pack(audioPackFormatName="m/s encode", type=TypeDefinition.Matrix,
                                            inputPackFormat=self.stereo_pack)
        self.encode_mid = self.create_channel(audioChannelFormatName="encode mid", type=TypeDefinition.Matrix, audioBlockFormats=[
            AudioBlockFormatMatrix(matrix=[
                MatrixCoefficient(inputChannelFormat=self.left_channel, gain=0.5 ** 0.5),
                MatrixCoefficient(inputChannelFormat=self.right_channel, gain=0.5 ** 0.5),
            ])])
        self.encode_side = self.create_channel(audioChannelFormatName="encode side", type=TypeDefinition.Matrix, audioBlockFormats=[
            AudioBlockFormatMatrix(matrix=[
                MatrixCoefficient(inputChannelFormat=self.left_channel, gain=-0.5 ** 0.5),
                MatrixCoefficient(inputChannelFormat=self.right_channel, gain=0.5 ** 0.5),
            ])])

        self.decode_pack = self.create_pack(audioPackFormatName="m/s decode stereo", type=TypeDefinition.Matrix,
                                            outputPackFormat=self.stereo_pack)
        self.decode_left = self.create_channel(audioChannelFormatName="decode left", type=TypeDefinition.Matrix, audioBlockFormats=[
            AudioBlockFormatMatrix(outputChannelFormat=self.left_channel, matrix=[
                MatrixCoefficient(inputChannelFormat=self.encode_mid, gain=0.5 ** 0.5),
                MatrixCoefficient(inputChannelFormat=self.encode_side, gain=-0.5 ** 0.5),
            ])])
        self.decode_right = self.create_channel(audioChannelFormatName="decode right", type=TypeDefinition.Matrix, audioBlockFormats=[
            AudioBlockFormatMatrix(outputChannelFormat=self.right_channel, matrix=[
                MatrixCoefficient(inputChannelFormat=self.encode_mid, gain=0.5 ** 0.5),
                MatrixCoefficient(inputChannelFormat=self.encode_side, gain=0.5 ** 0.5),
            ])])

        self.decode_pack.encodePackFormats = [self.encode_pack]

        self.create_stream(audioStreamFormatName="mid PCM", format=FormatDefinition.PCM,
                           audioChannelFormat=self.encode_mid)
        self.mid_track = self.create_track(audioTrackFormatName="mid PCM", format=FormatDefinition.PCM)

        self.create_stream(audioStreamFormatName="side PCM", format=FormatDefinition.PCM,
                           audioChannelFormat=self.encode_side)
        self.side_track = self.create_track(audioTrackFormatName="side PCM", format=FormatDefinition.PCM)

        self.create_stream(audioStreamFormatName="decode left PCM", format=FormatDefinition.PCM,
                           audioChannelFormat=self.decode_left)
        self.decode_left_track = self.create_track(audioTrackFormatName="decode left PCM", format=FormatDefinition.PCM)

        self.create_stream(audioStreamFormatName="decode right PCM", format=FormatDefinition.PCM,
                           audioChannelFormat=self.decode_right)
        self.decode_right_track = self.create_track(audioTrackFormatName="decode right PCM", format=FormatDefinition.PCM)


@pytest.mark.parametrize("usage", ["decode", "pre_decoded", "stereo", "encode_decode"])
def test_encode_decode(usage):
    builder = EncodeDecodeBuilder()

    def matrix(channel_format):
        [block_format] = channel_format.audioBlockFormats
        return block_format.matrix

    builder.create_programme(audioProgrammeName="MyProgramme")
    builder.create_content(audioContentName="MyContent")

    if usage == "decode":
        builder.create_object(audioObjectName="MyObject",
                              audioPackFormats=[builder.decode_pack])
        builder.create_track_uid(trackIndex=1,
                                 audioTrackFormat=builder.mid_track,
                                 audioPackFormat=builder.decode_pack)
        builder.create_track_uid(trackIndex=2,
                                 audioTrackFormat=builder.side_track,
                                 audioPackFormat=builder.decode_pack)

        expected = [
            (builder.left_channel.id, MixTrackSpec([
                MatrixCoefficientTrackSpec(DirectTrackSpec(0), matrix(builder.decode_left)[0]),
                MatrixCoefficientTrackSpec(DirectTrackSpec(1), matrix(builder.decode_left)[1]),
            ])),
            (builder.right_channel.id, MixTrackSpec([
                MatrixCoefficientTrackSpec(DirectTrackSpec(0), matrix(builder.decode_right)[0]),
                MatrixCoefficientTrackSpec(DirectTrackSpec(1), matrix(builder.decode_right)[1]),
            ])),
        ]
    elif usage == "pre_decoded":
        builder.create_object(audioObjectName="MyObject",
                              audioPackFormats=[builder.decode_pack])
        builder.create_track_uid(trackIndex=1,
                                 audioTrackFormat=builder.decode_left_track,
                                 audioPackFormat=builder.decode_pack)
        builder.create_track_uid(trackIndex=2,
                                 audioTrackFormat=builder.decode_right_track,
                                 audioPackFormat=builder.decode_pack)

        expected = [
            (builder.left_channel.id, DirectTrackSpec(0)),
            (builder.right_channel.id, DirectTrackSpec(1)),
        ]
    elif usage == "stereo":
        builder.create_object(audioObjectName="MyObject",
                              audioPackFormats=[builder.stereo_pack])
        builder.create_track_uid(trackIndex=1,
                                 audioTrackFormat=builder.adm["AT_00010001_01"],
                                 audioPackFormat=builder.stereo_pack)
        builder.create_track_uid(trackIndex=2,
                                 audioTrackFormat=builder.adm["AT_00010002_01"],
                                 audioPackFormat=builder.stereo_pack)

        expected = [
            (builder.left_channel.id, DirectTrackSpec(0)),
            (builder.right_channel.id, DirectTrackSpec(1)),
        ]

    elif usage == "encode_decode":
        builder.create_object(audioObjectName="MyObject",
                              audioPackFormats=[builder.decode_pack])
        builder.create_track_uid(trackIndex=1,
                                 audioTrackFormat=builder.adm["AT_00010001_01"],
                                 audioPackFormat=builder.encode_pack)
        builder.create_track_uid(trackIndex=2,
                                 audioTrackFormat=builder.adm["AT_00010002_01"],
                                 audioPackFormat=builder.encode_pack)

        input_ts = [DirectTrackSpec(0), DirectTrackSpec(1)]

        encoded_ts = [
            MixTrackSpec([MatrixCoefficientTrackSpec(input_ts[0], matrix(builder.encode_mid)[0]),
                          MatrixCoefficientTrackSpec(input_ts[1], matrix(builder.encode_mid)[1])]),
            MixTrackSpec([MatrixCoefficientTrackSpec(input_ts[0], matrix(builder.encode_side)[0]),
                          MatrixCoefficientTrackSpec(input_ts[1], matrix(builder.encode_side)[1])]),
        ]

        expected = [
            (builder.left_channel.id, MixTrackSpec([
                MatrixCoefficientTrackSpec(encoded_ts[0], matrix(builder.decode_left)[0]),
                MatrixCoefficientTrackSpec(encoded_ts[1], matrix(builder.decode_left)[1]),
            ])),
            (builder.right_channel.id, MixTrackSpec([
                MatrixCoefficientTrackSpec(encoded_ts[0], matrix(builder.decode_right)[0]),
                MatrixCoefficientTrackSpec(encoded_ts[1], matrix(builder.decode_right)[1]),
            ])),
        ]
    else:
        assert False

    generate_ids(builder.adm)

    selected_items = select_rendering_items(builder.adm)

    results = sorted((item.adm_path.audioChannelFormat.id, item.track_spec)
                     for item in selected_items)

    assert results == expected
