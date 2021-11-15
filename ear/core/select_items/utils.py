from ...fileio.adm.exceptions import AdmError


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


def get_path_param(path, name, default=None):
    """Get a parameter which can be defined in any of the objects in path. Any
    specified parameters must be consistent. If none were specified then the
    default is returned.
    """
    all_values = [getattr(obj, name) for obj in path]

    not_none = [value for value in all_values if value is not None]

    if not_none:
        if any(value != not_none[0] for value in not_none):
            raise AdmError(
                "Conflicting {name} values in path from {start.id} to {end.id}".format(
                    name=name,
                    start=path[0],
                    end=path[-1],
                )
            )

        return not_none[0]
    else:
        return default


def get_single_param(pack_paths_channels, name, get_param):
    """Get one parameter which must be consistent in all channels.

    Parameters:
        pack_paths_channels (list): list of tuples of (audioPackFormat_path,
            audioChannelFormat), one for each audioChannelFormat in the root
            audioPackFormat.
        name (str): name of parameter to be used in exceptions
        get_param (callable): function from (audioPackFormat_path,
            audioChannelFormat) to the value of the parameter.
    """
    for pack_path_channel_a, pack_path_channel_b in zip(
        pack_paths_channels[:-1], pack_paths_channels[1:]
    ):
        pack_format_path_a, channel_a = pack_path_channel_a
        pack_format_path_b, channel_b = pack_path_channel_b
        if get_param(pack_format_path_a, channel_a) != get_param(
            pack_format_path_b, channel_b
        ):
            raise AdmError(
                "All audioChannelFormats in a single audioPackFormat must "
                "share the same {name} value, but {acf_a.id} and {acf_b.id} differ.".format(
                    name=name,
                    acf_a=channel_a,
                    acf_b=channel_b,
                )
            )

    pack_path, channel = pack_paths_channels[0]
    return get_param(pack_path, channel)


def get_per_channel_param(pack_paths_channels, get_param):
    """Get One value of a parameter per channel in pack_paths_channels.
    See get_single_param."""
    return [get_param(pack_path, channel) for pack_path, channel in pack_paths_channels]
