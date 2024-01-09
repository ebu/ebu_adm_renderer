import importlib_resources
from .xml import parse_audioFormatExtended
import lxml.etree


def load_common_definitions(adm):
    """Load the common definitions file from IRU-R Rec. BS.2094-1, setting
    is_common_definition=True on all loaded elements.

    Parameters:
        adm (ADM): ADM structure to add to.
    """
    fname = "data/2094_common_definitions.xml"
    path = importlib_resources.files("ear.fileio.adm") / fname

    with path.open() as stream:
        element = lxml.etree.parse(stream)
        parse_audioFormatExtended(adm, element, common_definitions=True)
        adm.lazy_lookup_references()
