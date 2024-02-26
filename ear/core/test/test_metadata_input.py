from .. import metadata_input


def test_HOARenderingItem():
    metadata_source = metadata_input.MetadataSourceIter([])
    track_specs = [metadata_input.DirectTrackSpec(i) for i in range(4)]
    ri = metadata_input.HOARenderingItem(
        track_specs=track_specs,
        metadata_source=metadata_source,
    )

    assert len(ri.importances) == 4
    assert all(
        importance == metadata_input.ImportanceData() for importance in ri.importances
    )
