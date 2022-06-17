from functools import partial
from ...fileio.adm.exceptions import AdmError
from .utils import get_path_param

# functions which take a path through the audioPackFormats and an
# audioChannelFormat, and extract some parameter for a single HOA channel, for
# use with .utils.get_single_param and .utils.get_per_channel_param


def _get_pack_param(audioPackFormat_path, audioChannelFormat, name, default=None):
    """Get a parameter which can be defined in either audioPackFormats or
    audioBlockFormats. Any specified parameters must be consistent. If none
    were specified then the default is returned. This just looks at the
    path from the root audioPackFormat to a single audioBlockFormat -- the
    consistency in the whole pack is checked in get_single_param."""
    path = audioPackFormat_path + [audioChannelFormat.audioBlockFormats[0]]
    return get_path_param(path, name, default)


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
