from ..metadata_input import ObjectRenderingItem, HOARenderingItem, ImportanceData, MetadataSourceIter, MetadataSource
from ..metadata_input import ObjectTypeMetadata
from ..metadata_input import DirectTrackSpec
from ...fileio.adm.elements import AudioBlockFormatObjects
from ..importance import filter_by_importance, filter_audioObject_by_importance, filter_audioPackFormat_by_importance, MetadataSourceImportanceFilter
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
            ]


@pytest.mark.parametrize('threshold,expected_indizes', [
    (0, [0, 1, 2, 3, 4, 5, 6, 7]),
    (1, [0, 1, 2, 3, 4, 5, 6, 7]),
    (2, [1, 2, 3, 4, 5, 6, 7]),
    (3, [3, 4, 5, 6, 7]),
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
    (0, [0, 1, 2, 3, 4, 5, 6, 7]),
    (1, [0, 1, 2, 3, 4, 5, 6, 7]),
    (2, [0, 1, 2, 3, 4, 5, 6, 7]),
    (3, [1, 2, 3, 5, 6, 7]),
    (4, [2, 3, 5, 7]),
    (5, [2, 3, 5, 7]),
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
    (0, [0, 1, 2, 3, 4, 5, 6, 7]),
    (1, [0, 1, 2, 3, 4, 5, 6, 7]),
    (2, [1, 2, 3, 4, 5, 6, 7]),
    (3, [3, 5, 6, 7]),
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


@pytest.mark.parametrize('threshold,muted_indizes', [
    (0, []),
    (1, []),
    (2, []),
    (3, []),
    (4, [5]),
    (5, [2, 4, 5]),
    (6, [2, 4, 5]),
    (7, [2, 4, 5]),
    (8, [2, 4, 5]),
    (9, [2, 4, 5, 7]),
    (10, [2, 4, 5, 7])
])
def test_importance_filter_source(threshold, muted_indizes):
    source = MetadataSourceIter(type_metadatas)
    adapted = MetadataSourceImportanceFilter(source, threshold=threshold)
    for idx in range(len(type_metadatas)):
        block = adapted.get_next_block()
        if idx in muted_indizes:
            assert block.block_format.gain == 0.0
        else:
            assert block == type_metadatas[idx]
