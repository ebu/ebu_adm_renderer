def non_common(elements):
    for element in elements:
        if not element.is_common_definition:
            yield element


def _stream_track_formats(adm, stream_format):
    for track_format in non_common(adm.audioTrackFormats):
        if track_format.audioStreamFormat is stream_format:
            yield track_format


def _stream_type_definition(stream_format):
    """get the TypeDefinition from the channel or pack format linked to a stream format"""
    if stream_format.audioChannelFormat is not None:
        return stream_format.audioChannelFormat.type
    elif stream_format.audioPackFormat is not None:
        return stream_format.audioPackFormat.type
    else:
        assert False, (
            "can not generate IDs for an audioStreamFormat not linked"
            "to an audioChannelFormat or an audioPackFormat; run validation first"
        )


def generate_ids(adm):
    """regenerate ids for all elements in adm

    Parameters:
        adm (ADM): ADM structure to modify
    """
    # clear track format ids so that we can check these have all been allocated
    for element in non_common(adm.audioTrackFormats):
        element.id = None

    for id, element in enumerate(adm.audioProgrammes, 0x1001):
        element.id = "APR_{id:04X}".format(id=id)

    for id, element in enumerate(adm.audioContents, 0x1001):
        element.id = "ACO_{id:04X}".format(id=id)

    for id, element in enumerate(adm.audioObjects, 0x1001):
        element.id = "AO_{id:04X}".format(id=id)

        for avs_id, avs in enumerate(element.alternativeValueSets, 0x1):
            avs.id = "AVS_{id:04X}_{avs_id:04X}".format(id=id, avs_id=avs_id)

    for id, element in enumerate(non_common(adm.audioPackFormats), 0x1001):
        element.id = "AP_{type.value:04X}{id:04X}".format(id=id, type=element.type)

    for id, element in enumerate(non_common(adm.audioChannelFormats), 0x1001):
        element.id = "AC_{type.value:04X}{id:04X}".format(id=id, type=element.type)

        for block_id, block in enumerate(element.audioBlockFormats, 0x1):
            block.id = "AB_{type.value:04X}{id:04X}_{block_id:08X}".format(id=id, type=element.type, block_id=block_id)

    for id, element in enumerate(non_common(adm.audioStreamFormats), 0x1001):
        type_id = _stream_type_definition(element).value

        element.id = "AS_{type_id:04X}{id:04X}".format(id=id, type_id=type_id)

        for track_id, element in enumerate(_stream_track_formats(adm, element), 0x1):
            element.id = "AT_{type_id:04X}{id:04X}_{track_id:02X}".format(
                id=id, type_id=type_id, track_id=track_id
            )

    for id, element in enumerate(adm.audioTrackUIDs, 0x1):
        element.id = "ATU_{id:08X}".format(id=id)

    # check for any track uids that have not been allocated
    for element in non_common(adm.audioTrackFormats):
        assert element.id is not None, "cannot create id for audioTrackFormat not linked to any audioStreamFormat"
