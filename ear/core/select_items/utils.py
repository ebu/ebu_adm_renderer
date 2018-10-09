def in_by_id(element, collection):
    """Check if element is in collection, by comparing identity rather than equality."""
    return any(element is item for item in collection)


def _paths_from(start_node, get_children):
    """All paths through a tree structure starting at start_node."""
    yield [start_node]

    for sub_node in get_children(start_node):
        for path in _paths_from(sub_node, get_children):
            yield [start_node] + path


def object_paths_from(root_audioObject):
    """Find all audioObject paths accessible from root_audioObject.

    Parameters:
        root_audioObject (AudioObject): object to start from

    Yields:
        lists of AudioObject: all possible paths through the audioObject
        hierarchy, starting at root_audioObject; all paths start with root_audioObject,
        and one path is returned for each sub-object accessible from
        root_audioObject.
    """
    return _paths_from(root_audioObject, lambda ao: ao.audioObjects)


def pack_format_paths_from(root_audioPackFormat):
    """Find all audioPackFormat paths accessible from root_audioPackFormat.

    Parameters:
        root_audioPackFormat (AudioPackFormat): pack format to start from

    Yields:
        lists of AudioPackFormat: all possible paths through the
        audioPackFormat hierarchy, starting at root_audioPackFormat; all paths
        start with root_audioPackFormat, and one path is returned for each
        sub-pack accessible from root_audioPackFormat.
    """
    return _paths_from(root_audioPackFormat, lambda apf: apf.audioPackFormats)


def pack_format_channels(root_audioPackFormat):
    """Get all audioChannelFormats referenced by root_audioPackFormat.

    Parameters:
        root_audioPackFormat (AudioPackFormat): pack format to start from

    Yields:
        AudioChannelFormat: audioChannelFormats referenced from
        root_audioPackFormat and all sub-packs.
    """
    for path in pack_format_paths_from(root_audioPackFormat):
        for channel in path[-1].audioChannelFormats:
            yield channel


def pack_format_packs(root_audioPackFormat):
    """Get all audioPackFormats referenced by root_audioPackFormat.

    Parameters:
        root_audioPackFormat (AudioPackFormat): pack format to start from

    Yields:
        AudioPackFormat: pack format referenced from root_audioPackFormat,
        including root_audioPackFormat.
    """
    yield root_audioPackFormat

    for sub_pack in root_audioPackFormat.audioPackFormats:
        for sub_sub_pack in pack_format_packs(sub_pack):
            yield sub_sub_pack
