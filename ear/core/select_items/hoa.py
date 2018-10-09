from functools import partial
from ...fileio.adm.exceptions import AdmError


# functions which take a path through the audioPackFormats and an
# audioChannelFormat, and extract some parameter for a single HOA channel

def _get_pack_param(audioPackFormat_path, audioChannelFormat, name, default=None):
    """Get a parameter which can be defined in either audioPackFormats or
    audioBlockFormats. Any specified parameters must be consistent. If none
    were specified then the default is returned. This just looks at the
    path from the root audioPackFormat to a single audioBlockFormat -- the
    consistency in the whole pack is checked in get_single_param."""
    path = audioPackFormat_path + [audioChannelFormat.audioBlockFormats[0]]
    all_values = [getattr(obj, name) for obj in path]

    not_none = [value for value in all_values if value is not None]

    if not_none:
        if any(value != not_none[0] for value in not_none):
            raise AdmError("Conflicting {name} values in path from {apf.id} to {acf.id}".format(
                name=name,
                apf=audioPackFormat_path[0],
                acf=audioChannelFormat,
            ))

        return not_none[0]
    else:
        return default


def get_nfcRefDist(audioPackFormat_path, audioChannelFormat):
    nfcRefDist = _get_pack_param(audioPackFormat_path, audioChannelFormat, "nfcRefDist")
    return None if nfcRefDist == 0.0 else nfcRefDist


get_screenRef = partial(_get_pack_param, name="screenRef", default=False)
get_normalization = partial(_get_pack_param, name="normalization", default="SN3D")


def _get_block_format_attr(_audioPackFormat_path, audioChannelFormat, attr):
    [block_format] = audioChannelFormat.audioBlockFormats
    return getattr(block_format, attr)


get_order = partial(_get_block_format_attr, attr="order")
get_degree = partial(_get_block_format_attr, attr="degree")
get_rtime = partial(_get_block_format_attr, attr="rtime")
get_duration = partial(_get_block_format_attr, attr="duration")


# functions to use the above definitions for multiple channels

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
    for pack_path_channel_a, pack_path_channel_b in zip(pack_paths_channels[:-1], pack_paths_channels[1:]):
        pack_format_path_a, channel_a = pack_path_channel_a
        pack_format_path_b, channel_b = pack_path_channel_b
        if get_param(pack_format_path_a, channel_a) != get_param(pack_format_path_b, channel_b):
            raise AdmError("All HOA audioChannelFormats in a single audioPackFormat must "
                           "share the same {name} value, but {acf_a.id} and {acf_b.id} differ.".format(
                               name=name,
                               acf_a=channel_a,
                               acf_b=channel_b,
                           ))

    pack_path, channel = pack_paths_channels[0]
    return get_param(pack_path, channel)


def get_per_channel_param(pack_paths_channels, get_param):
    """Get One value of a parameter per channel in pack_paths_channels.
    See get_single_param."""
    return [get_param(pack_path, channel) for pack_path, channel in pack_paths_channels]
