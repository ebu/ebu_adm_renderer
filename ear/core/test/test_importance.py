from ..metadata_input import (
    ObjectRenderingItem,
    ObjectTypeMetadata,
    DirectSpeakersRenderingItem,
    DirectSpeakersTypeMetadata,
    HOARenderingItem,
    HOATypeMetadata,
    DirectTrackSpec,
    ImportanceData,
    MetadataSourceIter,
    MetadataSource,
)
from ...fileio.adm.elements import (
    AudioBlockFormatObjects,
    AudioBlockFormatDirectSpeakers,
    DirectSpeakerPolarPosition,
    BoundCoordinate,
)
from ..importance import (
    filter_by_importance,
    filter_audioObject_by_importance,
    filter_audioPackFormat_by_importance,
)
from attrs import evolve
from fractions import Fraction
import pytest


@pytest.fixture
def rendering_items():
    dummySource = MetadataSource()
    DTS = DirectTrackSpec
    return [ObjectRenderingItem(importance=ImportanceData(audio_object=1, audio_pack_format=2), track_spec=DTS(1), metadata_source=dummySource),
            ObjectRenderingItem(importance=ImportanceData(audio_object=2, audio_pack_format=3), track_spec=DTS(2), metadata_source=dummySource),
            ObjectRenderingItem(importance=ImportanceData(audio_object=2, audio_pack_format=None), track_spec=DTS(3), metadata_source=dummySource),
            ObjectRenderingItem(importance=ImportanceData(audio_object=3, audio_pack_format=10), track_spec=DTS(4), metadata_source=dummySource),
            ObjectRenderingItem(importance=ImportanceData(audio_object=None, audio_pack_format=2), track_spec=DTS(5), metadata_source=dummySource),
            ObjectRenderingItem(importance=ImportanceData(audio_object=4, audio_pack_format=7), track_spec=DTS(6), metadata_source=dummySource),
            ObjectRenderingItem(importance=ImportanceData(audio_object=10, audio_pack_format=3), track_spec=DTS(7), metadata_source=dummySource),
            HOARenderingItem(importances=[ImportanceData(audio_object=6, audio_pack_format=5),
                                          ImportanceData(audio_object=6, audio_pack_format=4),
                                          ImportanceData(audio_object=6, audio_pack_format=4),
                                          ImportanceData(audio_object=6, audio_pack_format=4),
                                          ],
                             track_specs=[DTS(8), DTS(9), DTS(10), DTS(11)],
                             metadata_source=dummySource),
            DirectSpeakersRenderingItem(
                importance=ImportanceData(audio_object=3, audio_pack_format=5),
                track_spec=DTS(12),
                metadata_source=dummySource),
            ]


@pytest.mark.parametrize('threshold,expected_indizes', [
    (0, [0, 1, 2, 3, 4, 5, 6, 7, 8]),
    (1, [0, 1, 2, 3, 4, 5, 6, 7, 8]),
    (2, [1, 2, 3, 4, 5, 6, 7, 8]),
    (3, [3, 4, 5, 6, 7, 8]),
    (4, [4, 5, 6, 7]),
    (5, [4, 6, 7]),
    (6, [4, 6, 7]),
    (7, [4, 6]),
    (8, [4, 6]),
    (9, [4, 6]),
    (10, [4, 6])
])
def test_importance_filter_objects(rendering_items, threshold, expected_indizes):
    expected_result = [rendering_items[x] for x in expected_indizes]
    items = list(filter_audioObject_by_importance(rendering_items, threshold=threshold))
    assert items == expected_result


@pytest.mark.parametrize('threshold,expected_indizes', [
    (0, [0, 1, 2, 3, 4, 5, 6, 7, 8]),
    (1, [0, 1, 2, 3, 4, 5, 6, 7, 8]),
    (2, [0, 1, 2, 3, 4, 5, 6, 7, 8]),
    (3, [1, 2, 3, 5, 6, 7, 8]),
    (4, [2, 3, 5, 7, 8]),
    (5, [2, 3, 5, 7, 8]),
    (6, [2, 3, 5]),
    (7, [2, 3, 5]),
    (8, [2, 3]),
    (9, [2, 3]),
    (10, [2, 3])
])
def test_importance_filter_packs(rendering_items, threshold, expected_indizes):
    expected_result = [rendering_items[x] for x in expected_indizes]
    items = list(filter_audioPackFormat_by_importance(rendering_items, threshold=threshold))
    assert items == expected_result


@pytest.mark.parametrize('threshold,expected_indizes', [
    (0, [0, 1, 2, 3, 4, 5, 6, 7, 8]),
    (1, [0, 1, 2, 3, 4, 5, 6, 7, 8]),
    (2, [1, 2, 3, 4, 5, 6, 7, 8]),
    (3, [3, 5, 6, 7, 8]),
    (4, [5, 7]),
    (5, [7]),
    (6, []),
    (7, []),
    (8, []),
    (9, []),
    (10, [])
])
def test_importance_filter(rendering_items, threshold, expected_indizes):
    expected_result = [rendering_items[x] for x in expected_indizes]
    items = list(filter_by_importance(rendering_items, threshold=threshold))

    def track_specs(item):
        return item.track_specs if isinstance(item, HOARenderingItem) else item.track_spec

    # the metadata sources will be different, so just check that we've got the right channel
    assert [track_specs(item) for item in items] == [track_specs(item) for item in expected_result]


type_metadatas = [
    ObjectTypeMetadata(block_format=AudioBlockFormatObjects(rtime=Fraction(0), position={'azimuth': 0, 'elevation': 0})),
    ObjectTypeMetadata(block_format=AudioBlockFormatObjects(rtime=Fraction(1), position={'azimuth': 0, 'elevation': 0})),
    ObjectTypeMetadata(block_format=AudioBlockFormatObjects(rtime=Fraction(2), position={'azimuth': 0, 'elevation': 0}, importance=4)),
    ObjectTypeMetadata(block_format=AudioBlockFormatObjects(rtime=Fraction(3), position={'azimuth': 0, 'elevation': 0})),
    ObjectTypeMetadata(block_format=AudioBlockFormatObjects(rtime=Fraction(4), position={'azimuth': 0, 'elevation': 0}, importance=4)),
    ObjectTypeMetadata(block_format=AudioBlockFormatObjects(rtime=Fraction(5), position={'azimuth': 0, 'elevation': 0}, importance=3)),
    ObjectTypeMetadata(block_format=AudioBlockFormatObjects(rtime=Fraction(6), position={'azimuth': 0, 'elevation': 0})),
    ObjectTypeMetadata(block_format=AudioBlockFormatObjects(rtime=Fraction(7), position={'azimuth': 0, 'elevation': 0}, importance=8)),
    ObjectTypeMetadata(block_format=AudioBlockFormatObjects(rtime=Fraction(8), position={'azimuth': 0, 'elevation': 0})),
    ObjectTypeMetadata(block_format=AudioBlockFormatObjects(rtime=Fraction(9), position={'azimuth': 0, 'elevation': 0}))
]


def get_blocks(metadata_source):
    """get the blocks from a metadata_source as a list"""
    blocks = []
    while True:
        block = metadata_source.get_next_block()
        if block is None:
            break
        blocks.append(block)

    return blocks


def make_objects_type_metadata(**kwargs):
    return ObjectTypeMetadata(
        block_format=AudioBlockFormatObjects(
            position={"azimuth": 0, "elevation": 0}, **kwargs
        )
    )


def make_direct_speakers_type_metadata(**kwargs):
    return DirectSpeakersTypeMetadata(
        block_format=AudioBlockFormatDirectSpeakers(
            position=DirectSpeakerPolarPosition(
                bounded_azimuth=BoundCoordinate(0.0),
                bounded_elevation=BoundCoordinate(0.0),
            ),
            **kwargs,
        )
    )


@pytest.mark.parametrize(
    "make_type_metadata,make_rendering_item",
    [
        (make_objects_type_metadata, ObjectRenderingItem),
        (make_direct_speakers_type_metadata, DirectSpeakersRenderingItem),
    ],
)
def test_importance_filter_blocks_single_channel(make_type_metadata, make_rendering_item):
    """check that blocks are modified to apply importance filtering for single-channel types"""
    type_metadatas = [
        make_type_metadata(rtime=Fraction(0)),
        make_type_metadata(rtime=Fraction(1), importance=5),
        make_type_metadata(rtime=Fraction(2), importance=6),
    ]
    expected = [
        make_type_metadata(rtime=Fraction(0)),
        make_type_metadata(rtime=Fraction(1), importance=5, gain=0.0),
        make_type_metadata(rtime=Fraction(2), importance=6),
    ]

    source = MetadataSourceIter(type_metadatas)
    rendering_items = [
        make_rendering_item(track_spec=DirectTrackSpec(1), metadata_source=source),
    ]

    rendering_items_out = filter_by_importance(rendering_items, 6)
    [rendering_item_out] = rendering_items_out
    assert get_blocks(rendering_item_out.metadata_source) == expected


@pytest.mark.parametrize(
    "gains",
    [
        [1.0, 1.0, 1.0, 1.0],
        [0.5, 0.25, 0.25, 0.25],
    ],
)
def test_importance_filter_hoa(gains):
    type_metadatas = [
        HOATypeMetadata(  # all but first channel muted
            orders=[0, 1, 1, 1],
            degrees=[0, -1, 0, 1],
            importances=[6, 5, 5, 5],
            normalization="SN3D",
            gains=gains,
        ),
        HOATypeMetadata(  # not modified
            orders=[0, 1, 1, 1],
            degrees=[0, -1, 0, 1],
            importances=[6, 6, 6, 6],
            normalization="SN3D",
            gains=gains,
        ),
    ]
    expected = [
        evolve(
            type_metadatas[0],
            gains=[gains[0], 0.0, 0.0, 0.0],
        ),
        evolve(
            type_metadatas[1],
            gains=gains,
        ),
    ]
    rendering_items = [
        HOARenderingItem(
            track_specs=[DirectTrackSpec(i) for i in range(4)],
            metadata_source=MetadataSourceIter(type_metadatas),
        ),
    ]

    rendering_items_out = filter_by_importance(rendering_items, 6)
    [rendering_item_out] = rendering_items_out
    assert get_blocks(rendering_item_out.metadata_source) == expected
