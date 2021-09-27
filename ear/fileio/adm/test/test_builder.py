import pytest
from ..builder import ADMBuilder
from ..elements import (
    AudioBlockFormatHoa,
    AudioBlockFormatObjects,
    ObjectPolarPosition,
    TypeDefinition,
)


@pytest.mark.parametrize("use_wrapper", [False, True])
def test_hoa(use_wrapper):
    builder = ADMBuilder()

    programme = builder.create_programme(audioProgrammeName="programme")
    content = builder.create_content(audioContentName="content")

    normalization = "SN3D"
    orders = [0, 1, 1, 1]
    degrees = [0, -1, 0, 1]

    blocks = [
        [AudioBlockFormatHoa(order=order, degree=degree, normalization=normalization)]
        for order, degree in zip(orders, degrees)
    ]
    track_indices = list(range(len(blocks)))

    if use_wrapper:
        item = builder.create_item_multichannel(
            type=TypeDefinition.HOA,
            track_indices=track_indices,
            name="myitem",
            block_formats=blocks,
        )
    else:
        item = builder.create_item_hoa(
            track_indices=track_indices,
            name="myitem",
            orders=orders,
            degrees=degrees,
            normalization=normalization,
        )

    for i in range(len(blocks)):
        track_index = track_indices[i]
        channel_blocks = blocks[i]
        track_format = item.track_formats[i]
        stream_format = item.stream_formats[i]
        channel_format = item.channel_formats[i]
        track_uid = item.track_uids[i]

        assert track_uid.trackIndex == track_index + 1
        assert track_uid.audioPackFormat is item.pack_format
        assert track_uid.audioTrackFormat is track_format

        assert track_format.audioStreamFormat is stream_format

        assert stream_format.audioChannelFormat is channel_format

        assert channel_format.audioBlockFormats == channel_blocks
        assert channel_format.audioChannelFormatName == f"myitem_{i+1}"

    assert item.pack_format.audioChannelFormats == item.channel_formats

    assert item.audio_object.audioPackFormats == [item.pack_format]
    assert item.audio_object.audioTrackUIDs == item.track_uids

    assert programme.audioContents == [content]
    assert content.audioObjects == [item.audio_object]


def test_mono():
    builder = ADMBuilder()

    programme = builder.create_programme(audioProgrammeName="programme")
    content = builder.create_content(audioContentName="content")

    block_formats = [
        AudioBlockFormatObjects(
            position=ObjectPolarPosition(azimuth=0.0, elevation=0.0, distance=1.0),
        ),
    ]
    item = builder.create_item_objects(0, "MyObject 1", block_formats=block_formats)

    assert item.track_uid.trackIndex == 1
    assert item.track_uid.audioPackFormat is item.pack_format
    assert item.track_uid.audioTrackFormat is item.track_format

    assert item.track_format.audioStreamFormat is item.stream_format

    assert item.stream_format.audioChannelFormat is item.channel_format

    assert item.channel_format.audioBlockFormats == block_formats
    assert item.channel_format.audioChannelFormatName == "MyObject 1"

    assert item.pack_format.audioChannelFormats == [item.channel_format]

    assert item.audio_object.audioPackFormats == [item.pack_format]
    assert item.audio_object.audioTrackUIDs == [item.track_uid]

    assert programme.audioContents == [content]
    assert content.audioObjects == [item.audio_object]
