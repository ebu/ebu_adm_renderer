import pkg_resources
from .xml import parse_adm_elements
import lxml.etree


def load_common_definitions(adm):
    """Load the common definitions file from IRU-R Rec. BS.2094-1, setting
    is_common_definition=True on all loaded elements.

    Parameters:
        adm (ADM): ADM structure to add to.
    """
    fname = "data/2094_common_definitions.xml"
    with pkg_resources.resource_stream(__name__, fname) as stream:
        element = lxml.etree.parse(stream)
        parse_adm_elements(adm, element, common_definitions=True)
        adm.lazy_lookup_references()
