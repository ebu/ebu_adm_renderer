from fractions import Fraction
from ....fileio.adm.builder import ADMBuilder
from ....fileio.adm.generate_ids import generate_ids
from .. import select_rendering_items
from ....fileio.adm.elements import TypeDefinition, FormatDefinition, AudioBlockFormatHoa


class HOABuilder(ADMBuilder):
    """ADMBuilder with pre-defined encode and decode matrix, with references to
    the various components"""

    def __init__(self):
        super(HOABuilder, self).__init__()
        # self.load_common_definitions()

        self.first_pack = self.create_pack(audioPackFormatName="foa", type=TypeDefinition.HOA)

        self.first_orders = [0, 1, 1, 1]
        self.first_degrees = [0, -1, 0, 1]

        for order, degree in zip(self.first_orders, self.first_degrees):
            self.create_channel(audioChannelFormatName="foa_{order}_{degree}".format(order=order, degree=degree),
                                type=TypeDefinition.HOA,
                                audioBlockFormats=[AudioBlockFormatHoa(order=order, degree=degree)])

        self.second_pack = self.create_pack(audioPackFormatName="2oa", type=TypeDefinition.HOA,
                                            audioPackFormats=[self.first_pack])

        self.second_orders = [2, 2, 2, 2, 2]
        self.second_degrees = [-2, -1, 0, 1, 2]

        for order, degree in zip(self.second_orders, self.second_degrees):
            self.create_channel(audioChannelFormatName="2oa_{order}_{degree}".format(order=order, degree=degree),
                                type=TypeDefinition.HOA,
                                audioBlockFormats=[AudioBlockFormatHoa(order=order, degree=degree)])

        self.first_tracks = []
        for channel in self.first_pack.audioChannelFormats:
            self.create_stream(audioStreamFormatName="stream", format=FormatDefinition.PCM,
                               audioChannelFormat=channel)
            self.first_tracks.append(self.create_track(audioTrackFormatName="track", format=FormatDefinition.PCM))

        self.second_tracks = []
        for channel in self.second_pack.audioChannelFormats:
            self.create_stream(audioStreamFormatName="stream", format=FormatDefinition.PCM,
                               audioChannelFormat=channel)
            self.second_tracks.append(self.create_track(audioTrackFormatName="track", format=FormatDefinition.PCM))


def test_hoa_basic_no_object():
    builder = HOABuilder()

    for i, track in enumerate(builder.first_tracks, 1):
        builder.create_track_uid(audioPackFormat=builder.first_pack, audioTrackFormat=track,
                                 trackIndex=i)

    generate_ids(builder.adm)

    [item] = select_rendering_items(builder.adm)
    meta = item.metadata_source.get_next_block()

    assert [track_spec.track_index for track_spec in item.track_specs] == list(range(4))
    assert meta.orders == builder.first_orders
    assert meta.degrees == builder.first_degrees

    assert meta.normalization == "SN3D"
    assert meta.nfcRefDist is None
    assert meta.screenRef is False
    assert meta.rtime is None and meta.duration is None


def test_hoa_basic_programme_content_object():
    builder = HOABuilder()

    builder.create_programme(audioProgrammeName="programme")
    builder.create_content(audioContentName="content")
    builder.create_object(audioObjectName="object", audioPackFormats=[builder.first_pack])

    for i, track in enumerate(builder.first_tracks, 1):
        builder.create_track_uid(audioPackFormat=builder.first_pack, audioTrackFormat=track,
                                 trackIndex=i)

    generate_ids(builder.adm)
    [item] = select_rendering_items(builder.adm)
    meta = item.metadata_source.get_next_block()

    assert [track_spec.track_index for track_spec in item.track_specs] == list(range(4))
    assert meta.orders == builder.first_orders
    assert meta.degrees == builder.first_degrees

    assert meta.normalization == "SN3D"
    assert meta.nfcRefDist is None
    assert meta.screenRef is False
    assert meta.rtime is None and meta.duration is None


def test_hoa_populated_blocks():
    builder = HOABuilder()

    for channel in (builder.first_pack.audioChannelFormats +
                    builder.second_pack.audioChannelFormats):
        [block_format] = channel.audioBlockFormats
        block_format.rtime = Fraction(0)
        block_format.duration = Fraction(1)
        block_format.normalization = "N3D"
        block_format.nfcRefDist = 1.0
        block_format.screenRef = True

    for i, track in enumerate(builder.first_tracks, 1):
        builder.create_track_uid(audioPackFormat=builder.first_pack, audioTrackFormat=track,
                                 trackIndex=i)

    generate_ids(builder.adm)
    [item] = select_rendering_items(builder.adm)
    meta = item.metadata_source.get_next_block()

    assert meta.normalization == "N3D"
    assert meta.nfcRefDist == 1.0
    assert meta.screenRef is True
    assert meta.rtime == Fraction(0) and meta.duration == Fraction(1)


def test_hoa_pack_params():
    builder = HOABuilder()

    for pack in builder.first_pack, builder.second_pack:
        pack.normalization = "N3D"
        pack.nfcRefDist = 1.0
        pack.screenRef = True

    for i, track in enumerate(builder.first_tracks, 1):
        builder.create_track_uid(audioPackFormat=builder.first_pack, audioTrackFormat=track,
                                 trackIndex=i)

    generate_ids(builder.adm)
    [item] = select_rendering_items(builder.adm)
    meta = item.metadata_source.get_next_block()

    assert meta.normalization == "N3D"
    assert meta.nfcRefDist == 1.0
    assert meta.screenRef is True
