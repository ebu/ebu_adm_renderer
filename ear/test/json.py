import attrs
import ear.common
import ear.core.metadata_input
import ear.fileio.adm.elements
from fractions import Fraction


def value_to_json(value, include_defaults=True):
    """turn EAR types into JSON

    This is not complete but will be extended as needed.

    The result can be turned back into objects using json_to_value

    Parameters:
        include_defaults (bool): add default values (True), or skip them (False)
    Returns:
        a json-serialisable object, composed of dict, list, bool, int, float,
        str or None

        objects are represented as a dictionary containing the keyword
        arguments for the constructor, and a _type key naming the type
    """

    def recurse(v):
        return value_to_json(v, include_defaults=include_defaults)

    if value is None:
        return None
    elif isinstance(value, (bool, int, float, str)):
        return value
    elif isinstance(value, list):
        return [recurse(v) for v in value]
    elif isinstance(value, dict):
        return {k: recurse(v) for k, v in value.items()}
    elif attrs.has(type(value)):
        d = dict(_type=type(value).__name__)

        for field in attrs.fields(type(value)):
            v = getattr(value, field.name)

            if include_defaults or not _field_is_default(field, v):
                d[field.name] = recurse(v)
        return d
    # types that need special handling; make this generic if we need to add more
    elif isinstance(value, Fraction):
        return dict(
            _type="Fraction", numerator=value.numerator, denominator=value.denominator
        )
    else:
        assert False, "unknown type"


def json_to_value(value):
    """turn the results of value_to_json back into objects"""
    if isinstance(value, dict):
        converted = {k: json_to_value(v) for k, v in value.items()}
        if "_type" in value:
            t = _known_types[value["_type"]]
            del converted["_type"]
            return t(**converted)
        else:
            return converted
    if isinstance(value, list):
        return [json_to_value(v) for v in value]
    else:
        return value


def _field_is_default(field: attrs.Attribute, value):
    """does an attrs field have the default value?

    this depends on values being properly equality-comparable
    """
    default = field.default
    if default is attrs.NOTHING:
        return False

    if isinstance(default, attrs.Factory):
        assert not default.takes_self, "not implemented"

        default = default.factory()

    return type(value) is type(default) and value == default


def _get_known_types():
    known_types = [
        ear.common.CartesianPosition,
        ear.common.CartesianScreen,
        ear.common.PolarPosition,
        ear.common.PolarScreen,
        ear.core.metadata_input.ExtraData,
        ear.core.metadata_input.ObjectTypeMetadata,
        ear.fileio.adm.elements.AudioBlockFormatObjects,
        ear.fileio.adm.elements.CartesianZone,
        ear.fileio.adm.elements.ChannelLock,
        ear.fileio.adm.elements.Frequency,
        ear.fileio.adm.elements.JumpPosition,
        ear.fileio.adm.elements.ObjectCartesianPosition,
        ear.fileio.adm.elements.ObjectDivergence,
        ear.fileio.adm.elements.ObjectPolarPosition,
        ear.fileio.adm.elements.PolarZone,
        ear.fileio.adm.elements.ScreenEdgeLock,
        Fraction,
    ]

    return {t.__name__: t for t in known_types}


_known_types = _get_known_types()
