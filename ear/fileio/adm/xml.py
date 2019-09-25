import sys
import warnings
from fractions import Fraction

from attr import attrs, attrib, Factory
import lxml.etree
from lxml.etree import QName
from lxml.builder import ElementMaker
from six import viewkeys, iteritems, reraise

from .adm import ADM
from .elements import (
    AudioBlockFormatObjects, AudioBlockFormatDirectSpeakers, AudioBlockFormatBinaural, AudioBlockFormatHoa, AudioBlockFormatMatrix,
    ChannelLock, BoundCoordinate, JumpPosition, ObjectDivergence, CartesianZone, PolarZone, ScreenEdgeLock, MatrixCoefficient)
from .elements import (
    AudioProgramme, AudioContent, AudioObject, AudioChannelFormat, AudioPackFormat, AudioStreamFormat, AudioTrackFormat, AudioTrackUID,
    FormatDefinition, TypeDefinition, Frequency, LoudnessMetadata)
from .elements.geom import (DirectSpeakerPolarPosition, DirectSpeakerCartesianPosition,
                            ObjectPolarPosition, ObjectCartesianPosition)
from .time_format import parse_time, unparse_time
from ...common import PolarPosition, CartesianPosition, CartesianScreen, PolarScreen


namespaces = [None,
              "urn:ebu:metadata-schema:ebuCore_2014",
              "urn:ebu:metadata-schema:ebuCore_2015",
              "urn:ebu:metadata-schema:ebuCore_2016",
              "urn:ebu:metadata-schema:ebuCore_2017",
              "urn:ebu:metadata-schema:ebuCore",
              "urn:metadata-schema:adm",
              ]

default_ns = "urn:ebu:metadata-schema:ebuCore_2017"
default_nsmap = {None: default_ns}


def qnames(localname):
    """Get all qualified names with a given local name."""
    return [localname if ns is None else lxml.etree.QName(ns, localname).text for ns in namespaces]


def xpath(element, xpath):
    """Select sub-elements from element with a given xpath, replacing '{ns}'
    with each of the namespaces.
    """
    for ns in namespaces:
        xpath_fmt = xpath.format(ns="" if ns is None else "adm:")
        for found_element in element.xpath(xpath_fmt,
                                           namespaces=dict() if ns is None else dict(adm=ns)):
            yield found_element


def text(element):
    """Get the text of an element as a string."""
    text = element.text
    return text if text is not None else ""


@attrs(eq=False)
class ParseError(Exception):
    """Represents an error that occured while processing a piece of xml."""
    exception = attrib()
    element = attrib()
    attr_name = attrib(default=None)

    def __str__(self):
        if self.attr_name is not None:
            str_format = "error while parsing attr {attr_name} of element {tag} on line {line}: {exc_type}: {exc}"
        else:
            str_format = "error while parsing element {tag} on line {line}: {exc_type}: {exc}"

        return str_format.format(
            attr_name=self.attr_name,
            tag=QName(self.element.tag).localname,
            line=self.element.sourceline,
            exc_type=type(self.exception).__name__,
            exc=str(self.exception))


@attrs
class TypeConvert(object):
    """Defines a conversion between some python type and strings."""
    # function from string to type; None implies no conversion
    loads = attrib()
    # function from type to string; None implies no conversion
    dumps = attrib()

    # as above, but convert none to the identity function

    @property
    def loads_func(self):
        if self.loads is None:
            return lambda data: data
        else:
            return self.loads

    @property
    def dumps_func(self):
        if self.dumps is None:
            return lambda data: data
        else:
            return self.dumps


def load_bool(data):
    if data == "0":
        return False
    elif data == "1":
        return True
    else:
        raise ValueError("could not parse bool: {}".format(data))


StringType = TypeConvert(None, None)
IntType = TypeConvert(int, str)
FloatType = TypeConvert(float, "{:.5f}".format)  # noqa: P103
SecondsType = TypeConvert(Fraction, lambda t: "{:07.5f}".format(float(t)))
BoolType = TypeConvert(load_bool, "{:d}".format)  # noqa: P103
TimeType = TypeConvert(parse_time, unparse_time)
RefType = TypeConvert(loads=None,
                      dumps=lambda data: data.id)

TrackUIDRefType = TypeConvert(
    loads=lambda s: None if s == "ATU_00000000" else s,
    dumps=lambda data: "ATU_00000000" if data is None else data.id)


@attrs
class Attribute(object):
    """An xml attribute that is turned into a constructor kwarg, either directly
    or via some conversion function."""
    adm_name = attrib()
    arg_name = attrib()
    type = attrib(default=StringType)
    required = attrib(default=False)
    default = attrib(default=None)

    def get_handlers(self):
        arg_name = self.arg_name
        convert = self.type.loads

        if convert is None:
            def f(kwargs, value):
                kwargs[arg_name] = value
        else:
            def f(kwargs, value):
                kwargs[arg_name] = convert(value)

        return [("attr", self.adm_name, f)]

    def to_xml(self, element, obj):
        attr = getattr(obj, self.arg_name)
        if attr != self.default:
            element.attrib[self.adm_name] = self.type.dumps_func(attr)


@attrs
class Element(object):
    """An xml sub-element; see sub-classes."""
    adm_name = attrib()


@attrs
class ListElement(Element):
    """An xml sub-element whose text contents is added to a list in the
    constructor kwargs, either directly or via some conversion."""
    arg_name = attrib()
    attr_name = attrib(default=Factory(lambda self: self.arg_name, takes_self=True))
    type = attrib(default=StringType)
    required = attrib(default=False)
    parse_only = attrib(default=False)

    def get_handlers(self):
        arg_name = self.arg_name
        convert = self.type.loads

        if convert is None:
            def f(kwargs, element):
                kwargs.setdefault(arg_name, []).append(text(element))
        else:
            def f(kwargs, element):
                kwargs.setdefault(arg_name, []).append(convert(text(element)))

        return [("element", qname, f) for qname in qnames(self.adm_name)]

    def to_xml(self, element, obj):
        if self.parse_only: return

        for data in getattr(obj, self.attr_name):
            new_el = element.makeelement(QName(default_ns, self.adm_name))
            new_el.text = self.type.dumps_func(data)
            element.append(new_el)


@attrs
class AttrElement(Element):
    """An xml sub-element whose text contents is converted to a constructor
    kwarg, either directly or via some conversion."""
    arg_name = attrib()
    attr_name = attrib(default=Factory(lambda self: self.arg_name, takes_self=True))
    type = attrib(default=StringType)
    required = attrib(default=False)
    default = attrib(default=None)
    parse_only = attrib(default=False)

    def get_handlers(self):
        arg_name = self.arg_name
        convert = self.type.loads

        if convert is None:
            def f(kwargs, element):
                if arg_name in kwargs:
                    raise ValueError("multiple {attr_name} elements found".format(attr_name=self.attr_name))
                kwargs[arg_name] = text(element)
        else:
            def f(kwargs, element):
                if arg_name in kwargs:
                    raise ValueError("multiple {attr_name} elements found".format(attr_name=self.attr_name))
                kwargs[arg_name] = convert(text(element))

        return [("element", qname, f) for qname in qnames(self.adm_name)]

    def to_xml(self, element, obj):
        if self.parse_only: return

        attr = getattr(obj, self.attr_name)
        if attr != self.default:
            new_el = element.makeelement(QName(default_ns, self.adm_name))
            new_el.text = self.type.dumps_func(attr)
            element.append(new_el)


@attrs
class HandleText(object):
    """Mapping between the text of an element and an attribute."""
    arg_name = attrib()
    attr_name = attrib(default=Factory(lambda self: self.arg_name, takes_self=True))
    type = attrib(default=StringType)
    required = False

    def get_handlers(self):
        arg_name = self.arg_name
        convert = self.type.loads
        if convert is None:
            def f(kwargs, text):
                kwargs[arg_name] = text
        else:
            def f(kwargs, text):
                kwargs[arg_name] = convert(text)

        return [("text", None, f)]

    def to_xml(self, element, obj):
        element.text = self.type.dumps_func(getattr(obj, self.attr_name))


@attrs
class CustomElement(Element):
    """An xml sub-element that is handled by some handler function."""
    handler = attrib()
    to_xml = attrib(default=None)
    arg_name = attrib(default=None)
    required = attrib(default=False)

    def get_handlers(self):
        return [("element", qname, self.handler) for qname in qnames(self.adm_name)]


class ElementParser(object):
    """Parser for an xml element type, that defers to the given properties to
    handle the attributes and sub-elements."""

    def __init__(self, cls, adm_name, properties, validate=None):
        self.cls = cls
        self.adm_name = adm_name
        self.properties = properties
        self.attr_handlers = {}
        self.element_handlers = {}
        self.text_handler = None
        self.required_args = set()
        self.arg_to_name = {}
        self.validate = validate

        for prop in properties:
            for handler_type, adm_name, handler in prop.get_handlers():
                if handler_type == "attr":
                    self.attr_handlers[adm_name] = handler
                elif handler_type == "element":
                    self.element_handlers[adm_name] = handler
                elif handler_type == "text":
                    assert self.text_handler is None, "more than one text handler"
                    self.text_handler = handler
                else:
                    assert False  # pragma: no cover

                if prop.required:
                    self.required_args.add(prop.arg_name)
                    self.arg_to_name[prop.arg_name] = QName(adm_name).localname

    def parse(self, element):
        kwargs = {}

        def null_handler(kwargs, x):
            pass

        for key, value in iteritems(element.attrib):
            try:
                self.attr_handlers.get(key, null_handler)(kwargs, value)
            except ParseError: raise
            except Exception as e: reraise(ParseError, ParseError(e, element, key), sys.exc_info()[2])

        for child in element.getchildren():
            try:
                self.element_handlers.get(child.tag, null_handler)(kwargs, child)
            except ParseError: raise
            except Exception as e: reraise(ParseError, ParseError(e, child), sys.exc_info()[2])

        if self.text_handler is not None:
            self.text_handler(kwargs, text(element))

        if not (viewkeys(kwargs) >= self.required_args):
            missing_args = self.required_args - viewkeys(kwargs)
            missing_items = (self.arg_to_name[arg_name] for arg_name in missing_args)
            err = ValueError("missing items: {missing}".format(missing=', '.join(missing_items)))
            raise ParseError(err, element)

        if self.validate is not None:
            self.validate(kwargs)

        try:
            return self.cls(**kwargs)
        except ParseError: raise
        except Exception as e: reraise(ParseError, ParseError(e, element), sys.exc_info()[2])

    def to_xml(self, parent, obj):
        element = parent.makeelement(QName(default_ns, self.adm_name))
        parent.append(element)

        for prop in self.properties:
            if prop.to_xml is not None:
                prop.to_xml(element, obj)

        return element

    def as_handler(self, arg_name, default=None, required=False):
        def handle(kwargs, el):
            kwargs[arg_name] = self.parse(el)

        def to_xml(parent, obj):
            attr = getattr(obj, arg_name)
            if attr is not None and (default is None or attr != default):
                self.to_xml(parent, attr)

        return CustomElement(
            adm_name=self.adm_name,
            handler=handle,
            to_xml=to_xml,
            arg_name=arg_name,
            required=False,
        )

    def as_list_handler(self, arg_name):
        """Get a CustomElement for use in another ElementParser which turns
        multiple sub-elements into a list called arg_name, and the reverse.
        """
        def handle(kwargs, el):
            kwargs.setdefault(arg_name, []).append(self.parse(el))

        def to_xml(parent, obj):
            for attr in getattr(obj, arg_name):
                self.to_xml(parent, attr)

        return CustomElement(
            adm_name=self.adm_name,
            handler=handle,
            to_xml=to_xml,
            arg_name=arg_name,
            required=False,
        )


# helpers for common element types


def RefList(name, **kwargs):
    return ListElement(
        adm_name=name + "IDRef",
        arg_name=name + "IDRef",
        attr_name=name + "s",
        type=RefType,
        **kwargs)


def RefElement(name, **kwargs):
    return AttrElement(
        adm_name=name + "IDRef",
        arg_name=name + "IDRef",
        attr_name=name,
        type=RefType,
        **kwargs)


@attrs
class TypeAttribute(object):
    """Attribute type used to convert *Label and *Definition attributes to and
    from single enum attributes."""
    enum = attrib()
    definition_name = attrib()
    label_name = attrib()
    arg_name = attrib()
    required = attrib(default=True)

    def get_handlers(self):
        def definition_handler(kwargs, value):
            try:
                found = self.enum[value]
            except KeyError:
                raise ValueError("Unknown {name}: {value}".format(name=self.definition_name, value=value))

            if self.arg_name in kwargs and kwargs[self.arg_name] != found:
                raise ValueError("Unexpected {name}: found {found.name}, expected {expected.name}".format(
                    name=self.definition_name,
                    found=found, expected=kwargs[self.arg_name]))

            kwargs[self.arg_name] = found

        def label_handler(kwargs, value):
            try:
                found = self.enum(int(value, 16))
            except ValueError:
                raise ValueError("Unknown {name}: {value}".format(name=self.label_name, value=value))

            if self.arg_name in kwargs and kwargs[self.arg_name] != found:
                raise ValueError("Unexpected {name}: found {found.value}, expected {expected.value}".format(
                    name=self.label_name,
                    found=found, expected=kwargs[self.arg_name]))

            kwargs[self.arg_name] = found

        return [("attr", self.definition_name, definition_handler),
                ("attr", self.label_name, label_handler)]

    def to_xml(self, element, obj):
        attr = getattr(obj, self.arg_name)
        element.attrib[self.label_name] = "{:04X}".format(attr.value)
        element.attrib[self.definition_name] = attr.name


type_handler = TypeAttribute(TypeDefinition, "typeDefinition", "typeLabel", "type")
format_handler = TypeAttribute(FormatDefinition, "formatDefinition", "formatLabel", "format")


# properties common to all block formats
block_format_props = [
    Attribute(adm_name="audioBlockFormatID", arg_name="id", required=True),
    Attribute(adm_name="rtime", arg_name="rtime", type=TimeType),
    Attribute(adm_name="duration", arg_name="duration", type=TimeType),
]


# typeDefinition == "Objects"

def parse_block_format_objects(element):
    props = block_format_objects_handler.parse(element)
    props["position"] = parse_objects_position(element)
    return AudioBlockFormatObjects(**props)


def parse_objects_position(element):
    position = {}

    screen_edge_lock = ScreenEdgeLock()
    for element in xpath(element, "{ns}position"):
        try:
            coordinate = element.attrib["coordinate"]
        except KeyError:
            raise ValueError("missing coordinate attr")
        if coordinate in position:
            raise ValueError("duplicate {coord} coordinates specified".format(coord=coordinate))

        position[coordinate] = float(text(element))

        if "screenEdgeLock" in element.attrib:
            coordinate = element.attrib["coordinate"]
            screenEdgeLock = element.attrib["screenEdgeLock"]

            if coordinate in ["azimuth", "X"] and screenEdgeLock in ["left", "right"]:
                screen_edge_lock.horizontal = screenEdgeLock
            elif coordinate in ["elevation", "Z"] and screenEdgeLock in ["top", "bottom"]:
                screen_edge_lock.vertical = screenEdgeLock
            else:
                raise ValueError("invalid screenEdgeLock value {screenEdgeLock} for coordinate {coordinate}".format(
                    screenEdgeLock=screenEdgeLock,
                    coordinate=coordinate,
                ))

    coordinates = set(position.keys())

    if coordinates in ({"azimuth", "elevation"}, {"azimuth", "elevation", "distance"}):
        return ObjectPolarPosition(
            azimuth=position['azimuth'],
            elevation=position['elevation'],
            distance=position.get('distance', 1.0),
            screenEdgeLock=screen_edge_lock
        )
    elif coordinates in ({"X", "Y"}, {"X", "Y", "Z"}):
        return ObjectCartesianPosition(
            X=position["X"],
            Y=position["Y"],
            Z=position.get("Z", 0.0),
            screenEdgeLock=screen_edge_lock
        )
    else:
        raise ValueError("Found coordinates {{{found}}}, but expected either "
                         "{{azimuth,elevation,distance}}, {{azimuth,elevation}}, {{X,Y,Z}} or {{X,Y}}."
                         .format(found=','.join(coordinates)))


def block_format_objects_to_xml(parent, obj):
    element = block_format_objects_handler.to_xml(parent, obj)
    object_position_to_xml(element, obj)


def object_position_to_xml(parent, obj):
    pos = obj.position

    def dump_coordinate(coordinate, value, screenEdgeLock=None):
        element = parent.makeelement(QName(default_ns, "position"), coordinate=coordinate)
        element.text = FloatType.dumps(value)

        if screenEdgeLock is not None:
            element.attrib["screenEdgeLock"] = screenEdgeLock

        parent.append(element)

    if isinstance(pos, ObjectPolarPosition):
        dump_coordinate("azimuth", pos.azimuth, pos.screenEdgeLock.horizontal)
        dump_coordinate("elevation", pos.elevation, pos.screenEdgeLock.vertical)
        if pos.distance != 1.0:
            dump_coordinate("distance", pos.distance)
    elif isinstance(pos, ObjectCartesianPosition):
        dump_coordinate("X", pos.X, pos.screenEdgeLock.horizontal)
        dump_coordinate("Y", pos.Y)
        if pos.Z != 0.0 or pos.screenEdgeLock.vertical is not None:
            dump_coordinate("Z", pos.Z, pos.screenEdgeLock.vertical)
    else:
        assert False, "unexpected type"  # pragma: no cover


def handle_channel_lock(kwargs, el):
    if text(el) == "0":
        pass
    elif text(el) == "1":
        kwargs["channelLock"] = ChannelLock(
            maxDistance=float(el.attrib["maxDistance"]) if "maxDistance" in el.attrib else None,
        )
    else:
        raise ValueError("channelLock value must be 0 or 1, not {value!r}".format(value=text(el)))


def channel_lock_to_xml(parent, obj):
    channelLock = obj.channelLock

    if channelLock is not None:
        element = parent.makeelement(QName(default_ns, "channelLock"))
        element.text = "1"

        if channelLock.maxDistance is not None:
            element.attrib["maxDistance"] = FloatType.dumps(channelLock.maxDistance)

        parent.append(element)


def handle_jump_position(kwargs, el):
    kwargs["jumpPosition"] = JumpPosition(
        flag=BoolType.loads(text(el)),
        interpolationLength=(SecondsType.loads(el.attrib["interpolationLength"])
                             if "interpolationLength" in el.attrib else None))


def jump_position_to_xml(parent, obj):
    jumpPosition = obj.jumpPosition
    if jumpPosition.flag:
        element = parent.makeelement(QName(default_ns, "jumpPosition"))

        element.text = BoolType.dumps(jumpPosition.flag)
        if jumpPosition.interpolationLength is not None:
            element.attrib["interpolationLength"] = SecondsType.dumps(jumpPosition.interpolationLength)

        parent.append(element)


def handle_divergence(kwargs, el):
    kwargs["objectDivergence"] = ObjectDivergence(
        value=float(text(el)),
        azimuthRange=(float(el.attrib['azimuthRange'])
                      if 'azimuthRange' in el.attrib
                      else None),
        positionRange=(float(el.attrib['positionRange'])
                       if 'positionRange' in el.attrib
                       else None))


def divergence_to_xml(parent, obj):
    divergence = obj.objectDivergence

    if divergence is not None:
        element = parent.makeelement(QName(default_ns, "objectDivergence"))
        element.text = FloatType.dumps(divergence.value)
        if divergence.azimuthRange is not None:
            element.attrib["azimuthRange"] = FloatType.dumps(divergence.azimuthRange)
        if divergence.positionRange is not None:
            element.attrib["positionRange"] = FloatType.dumps(divergence.positionRange)
        parent.append(element)


def parse_zone(el):
    keys = set(el.attrib.keys())
    cart_keys = set(["minX", "minY", "minZ", "maxX", "maxY", "maxZ"])
    polar_keys = set(["minAzimuth", "maxAzimuth", "minElevation", "maxElevation"])

    if keys >= cart_keys and not keys & polar_keys:
        return CartesianZone(**{key: float(value) for key, value in el.attrib.items()
                                if key in cart_keys})
    elif keys >= polar_keys and not keys & cart_keys:
        return PolarZone(**{key: float(value) for key, value in el.attrib.items()
                            if key in polar_keys})
    else:
        raise ValueError("Do not know how to parse a zone with keys {}.".format(", ".join(sorted(el.attrib.keys()))))


def handle_zone(kwargs, el):
    kwargs.setdefault("zones", []).append(parse_zone(el))


def zone_to_xml(parent, obj):
    if isinstance(obj, CartesianZone):
        parent.append(parent.makeelement(QName(default_ns, "zone"),
                                         minX=FloatType.dumps(obj.minX),
                                         minY=FloatType.dumps(obj.minY),
                                         minZ=FloatType.dumps(obj.minZ),
                                         maxX=FloatType.dumps(obj.maxX),
                                         maxY=FloatType.dumps(obj.maxY),
                                         maxZ=FloatType.dumps(obj.maxZ)))
    elif isinstance(obj, PolarZone):
        parent.append(parent.makeelement(QName(default_ns, "zone"),
                                         minAzimuth=FloatType.dumps(obj.minAzimuth),
                                         maxAzimuth=FloatType.dumps(obj.maxAzimuth),
                                         minElevation=FloatType.dumps(obj.minElevation),
                                         maxElevation=FloatType.dumps(obj.maxElevation)))
    else:
        assert False, "unexpected type"


def zones_to_xml(parent, obj):
    for zone in obj:
        zone_to_xml(parent, zone)


zone_exclusion_handler = ElementParser((lambda zones=[]: zones), "zoneExclusion", [
    CustomElement("zone", handle_zone, to_xml=zones_to_xml),
])


block_format_objects_handler = ElementParser(dict, "audioBlockFormat", block_format_props + [
    CustomElement("channelLock", handle_channel_lock, to_xml=channel_lock_to_xml),
    CustomElement("jumpPosition", handle_jump_position, to_xml=jump_position_to_xml),
    CustomElement("objectDivergence", handle_divergence, to_xml=divergence_to_xml),
    AttrElement(adm_name="width", arg_name="width", type=FloatType, default=0.0),
    AttrElement(adm_name="height", arg_name="height", type=FloatType, default=0.0),
    AttrElement(adm_name="depth", arg_name="depth", type=FloatType, default=0.0),
    AttrElement(adm_name="gain", arg_name="gain", type=FloatType, default=1.0),
    AttrElement(adm_name="diffuse", arg_name="diffuse", type=FloatType, default=0.0),
    AttrElement(adm_name="cartesian", arg_name="cartesian", type=BoolType, default=False),
    AttrElement(adm_name="screenRef", arg_name="screenRef", type=BoolType, default=False),
    AttrElement(adm_name="importance", arg_name="importance", type=IntType, default=10),
    zone_exclusion_handler.as_handler("zoneExclusion", default=[]),
])


# typeDefinition == "DirectSpeakers"


def parse_speaker_position(element):
    position = {}

    screen_edge_lock = ScreenEdgeLock()
    for element in xpath(element, "{ns}position"):
        coordinate = element.attrib["coordinate"]

        bound = element.attrib.get('bound', 'value')

        position.setdefault(coordinate, {})[bound] = float(text(element))

        if "screenEdgeLock" in element.attrib:
            screenEdgeLock = element.attrib["screenEdgeLock"]
            if bound != "value":
                raise ValueError("screenEdgeLock must be specified on the position, not the bound")

            if coordinate in ["azimuth", "X"] and screenEdgeLock in ["left", "right"]:
                screen_edge_lock.horizontal = screenEdgeLock
            elif coordinate in ["elevation", "Z"] and screenEdgeLock in ["top", "bottom"]:
                screen_edge_lock.vertical = screenEdgeLock
            else:
                raise ValueError("invalid screenEdgeLock value {screenEdgeLock} for coordinate {coordinate}".format(
                    screenEdgeLock=screenEdgeLock,
                    coordinate=coordinate,
                ))

    coordinates = set(position.keys())

    if coordinates in ({"azimuth", "elevation"}, {"azimuth", "elevation", "distance"}):
        return DirectSpeakerPolarPosition(
            bounded_azimuth=BoundCoordinate(**position['azimuth']),
            bounded_elevation=BoundCoordinate(**position['elevation']),
            bounded_distance=BoundCoordinate(**position.get('distance', dict(value=1.0))),
            screenEdgeLock=screen_edge_lock
        )
    elif coordinates in ({"X", "Y"}, {"X", "Y", "Z"}):
        return DirectSpeakerCartesianPosition(
            bounded_X=BoundCoordinate(**position["X"]),
            bounded_Y=BoundCoordinate(**position["Y"]),
            bounded_Z=BoundCoordinate(**position.get("Z", dict(value=0.0))),
            screenEdgeLock=screen_edge_lock
        )
    else:
        raise ValueError("Found coordinates {{{found}}}, but expected either "
                         "{{azimuth,elevation,distance}}, {{azimuth,elevation}}, {{X,Y,Z}} or {{X,Y}}."
                         .format(found=','.join(coordinates)))


def speaker_position_to_xml(parent, obj):
    pos = obj.position

    def add_pos_el(coordinate, value, **kwargs):
        element = parent.makeelement(QName(default_ns, "position"), coordinate=coordinate, **kwargs)
        element.text = FloatType.dumps(value)
        parent.append(element)

    def dump_bound(coordinate, bound, screen_edge_lock=None):
        if screen_edge_lock is not None:
            add_pos_el(coordinate, bound.value, screenEdgeLock=screen_edge_lock)
        else:
            add_pos_el(coordinate, bound.value)
        if bound.max is not None:
            add_pos_el(coordinate, bound.max, bound="max")
        if bound.min is not None:
            add_pos_el(coordinate, bound.min, bound="min")

    if isinstance(pos, DirectSpeakerPolarPosition):
        dump_bound("azimuth", pos.bounded_azimuth, pos.screenEdgeLock.horizontal)
        dump_bound("elevation", pos.bounded_elevation, pos.screenEdgeLock.vertical)
        if pos.bounded_distance != BoundCoordinate(1.0):
            dump_bound("distance", pos.bounded_distance)
    elif isinstance(pos, DirectSpeakerCartesianPosition):
        dump_bound("X", pos.bounded_X, pos.screenEdgeLock.horizontal)
        dump_bound("Y", pos.bounded_Y)
        dump_bound("Z", pos.bounded_Z, pos.screenEdgeLock.vertical)
    else:
        assert False, "unexpected type"  # pragma: no cover


block_format_direct_speakers_handler = ElementParser(dict, "audioBlockFormat", block_format_props + [
    ListElement(adm_name="speakerLabel", arg_name="speakerLabel"),
])


block_format_binaural_handler = ElementParser(AudioBlockFormatBinaural, "audioBlockFormat", block_format_props)


def parse_block_format_direct_speakers(element):
    props = block_format_direct_speakers_handler.parse(element)
    props["position"] = parse_speaker_position(element)
    return AudioBlockFormatDirectSpeakers(**props)


def block_format_direct_speakers_to_xml(parent, obj):
    element = block_format_direct_speakers_handler.to_xml(parent, obj)
    speaker_position_to_xml(element, obj)


block_format_HOA_handler = ElementParser(AudioBlockFormatHoa, "audioBlockFormat", block_format_props + [
    AttrElement(adm_name="equation", arg_name="equation", type=StringType),
    AttrElement(adm_name="order", arg_name="order", type=IntType),
    AttrElement(adm_name="degree", arg_name="degree", type=IntType),
    AttrElement(adm_name="normalization", arg_name="normalization", type=StringType),
    AttrElement(adm_name="nfcRefDist", arg_name="nfcRefDist", type=FloatType),
    AttrElement(adm_name="screenRef", arg_name="screenRef", type=BoolType),
])


matrix_coefficient_handler = ElementParser(MatrixCoefficient, "coefficient", [
    HandleText(arg_name="inputChannelFormatIDRef", attr_name="inputChannelFormat", type=RefType),
    Attribute(adm_name="gain", arg_name="gain", type=FloatType),
    Attribute(adm_name="phase", arg_name="phase", type=FloatType),
    Attribute(adm_name="delay", arg_name="delay", type=FloatType),
    Attribute(adm_name="gainVar", arg_name="gainVar", type=StringType),
    Attribute(adm_name="phaseVar", arg_name="phaseVar", type=StringType),
    Attribute(adm_name="delayVar", arg_name="delayVar", type=StringType),
])


def handle_matrix(kwargs, el):
    if "matrix" in kwargs:
        raise ValueError("multiple matrix elements found")

    kwargs["matrix"] = [matrix_coefficient_handler.parse(child)
                        for child in xpath(el, "{ns}coefficient")]


def matrix_to_xml(parent, obj):
    el = parent.makeelement(QName(default_ns, "matrix"))

    for coefficient in obj.matrix:
        matrix_coefficient_handler.to_xml(el, coefficient)

    parent.append(el)


block_format_matrix_handler = ElementParser(AudioBlockFormatMatrix, "audioBlockFormat", block_format_props + [
    AttrElement(adm_name="outputChannelFormatIDRef",
                arg_name="outputChannelFormatIDRef",
                attr_name="outputChannelFormat", type=RefType),
    AttrElement(adm_name="outputChannelIDRef",
                arg_name="outputChannelFormatIDRef",
                attr_name="outputChannelFormat", type=RefType, parse_only=True),
    CustomElement("matrix", handle_matrix, to_xml=matrix_to_xml),
])


block_format_handlers = {
    TypeDefinition.Objects: parse_block_format_objects,
    TypeDefinition.DirectSpeakers: parse_block_format_direct_speakers,
    TypeDefinition.Binaural: block_format_binaural_handler.parse,
    TypeDefinition.HOA: block_format_HOA_handler.parse,
    TypeDefinition.Matrix: block_format_matrix_handler.parse,
}


def handle_block_format(kwargs, el):
    type = kwargs["type"]
    try:
        handler = block_format_handlers[type]
    except KeyError:
        raise ValueError("Do not know how to parse block format of type {type.name}".format(type=type))
    block_format = handler(el)
    kwargs.setdefault("audioBlockFormats", []).append(block_format)


block_format_to_xml_handlers = {
    TypeDefinition.Objects: block_format_objects_to_xml,
    TypeDefinition.DirectSpeakers: block_format_direct_speakers_to_xml,
    TypeDefinition.Binaural: block_format_binaural_handler.to_xml,
    TypeDefinition.HOA: block_format_HOA_handler.to_xml,
    TypeDefinition.Matrix: block_format_matrix_handler.to_xml,
}


def block_format_to_xml(parent, obj):
    try:
        handler = block_format_to_xml_handlers[obj.type]
    except KeyError:
        raise ValueError("Do not know how to generate block format of type {type.name}".format(type=obj.type))
    for bf in obj.audioBlockFormats:
        handler(parent, bf)


def handle_frequency(kwargs, el):
    frequency = kwargs.setdefault("frequency", Frequency())

    type = el.attrib["typeDefinition"]
    value = FloatType.loads_func(el.text)

    if type == "lowPass":
        if frequency.lowPass is not None:
            raise ValueError("More than one lowPass frequency element specified.")
        frequency.lowPass = value
    elif type == "highPass":
        if frequency.highPass is not None:
            raise ValueError("More than one highPass frequency element specified.")
        frequency.highPass = value
    else:
        raise ValueError("frequency type must be lowPass or highPass, not {type}".format(type=type))


def frequency_to_xml(parent, obj):
    if obj.frequency.lowPass is not None:
        element = parent.makeelement(QName(default_ns, "frequency"), typeDefinition="lowPass")
        element.text = FloatType.dumps(obj.frequency.lowPass)
        parent.append(element)
    if obj.frequency.highPass is not None:
        element = parent.makeelement(QName(default_ns, "frequency"), typeDefinition="highPass")
        element.text = FloatType.dumps(obj.frequency.highPass)
        parent.append(element)


channel_format_handler = ElementParser(AudioChannelFormat, "audioChannelFormat", [
    Attribute(adm_name="audioChannelFormatID", arg_name="id", required=True),
    Attribute(adm_name="audioChannelFormatName", arg_name="audioChannelFormatName", required=True),
    type_handler,
    CustomElement("audioBlockFormat", handle_block_format, arg_name="audioBlockFormats", to_xml=block_format_to_xml, required=True),
    CustomElement("frequency", handle_frequency, to_xml=frequency_to_xml),
])

pack_format_handler = ElementParser(AudioPackFormat, "audioPackFormat", [
    Attribute(adm_name="audioPackFormatID", arg_name="id", required=True),
    Attribute(adm_name="audioPackFormatName", arg_name="audioPackFormatName", required=True),
    type_handler,
    Attribute(adm_name="importance", arg_name="importance", type=IntType),
    RefList("audioChannelFormat"),
    RefList("audioPackFormat"),
    AttrElement(adm_name="absoluteDistance", arg_name="absoluteDistance", type=FloatType),
    RefList("encodePackFormat"),
    RefList("decodePackFormat", parse_only=True),
    RefElement("inputPackFormat"),
    RefElement("outputPackFormat"),
    AttrElement(adm_name="normalization", arg_name="normalization", type=StringType),
    AttrElement(adm_name="nfcRefDist", arg_name="nfcRefDist", type=FloatType),
    AttrElement(adm_name="screenRef", arg_name="screenRef", type=BoolType),
])


def _check_stream_track_ref(kwargs):
    if "audioTrackFormatIDRef" not in kwargs:
        warnings.warn("audioStreamFormat {id} has no audioTrackFormatIDRef; "
                      "this may be incompatible with some software".format(id=kwargs["id"]))


stream_format_handler = ElementParser(AudioStreamFormat, "audioStreamFormat", [
    Attribute(adm_name="audioStreamFormatID", arg_name="id", required=True),
    Attribute(adm_name="audioStreamFormatName", arg_name="audioStreamFormatName", required=True),
    format_handler,
    RefList("audioTrackFormat"),
    RefElement("audioChannelFormat"),
    RefElement("audioPackFormat"),
], _check_stream_track_ref)


def _check_track_stream_ref(kwargs):
    if "audioStreamFormatIDRef" not in kwargs:
        warnings.warn("audioTrackFormat {id} has no audioStreamFormatIDRef; "
                      "this may be incompatible with some software".format(id=kwargs["id"]))


track_format_handler = ElementParser(AudioTrackFormat, "audioTrackFormat", [
    Attribute(adm_name="audioTrackFormatID", arg_name="id", required=True),
    Attribute(adm_name="audioTrackFormatName", arg_name="audioTrackFormatName", required=True),
    format_handler,
    RefElement("audioStreamFormat"),
], _check_track_stream_ref)


default_screen = PolarScreen(aspectRatio=1.78,
                             centrePosition=PolarPosition(
                                 azimuth=0.0,
                                 elevation=0.0,
                                 distance=1.0),
                             widthAzimuth=58.0)


def handle_screen_type(kwargs, screen_type):
    if "screen_type" in kwargs:
        if kwargs["screen_type"] != screen_type:
            raise ValueError("Expected {expected} screen data, got {got}.".format(expected=kwargs["screen_type"], got=screen_type))
    else:
        kwargs["screen_type"] = screen_type


def handle_centre_position(kwargs, el):
    keys = set(el.attrib.keys())

    if keys >= set(["X", "Y", "Z"]):
        kwargs["centrePosition"] = CartesianPosition(X=float(el.attrib["X"]),
                                                     Y=float(el.attrib["Y"]),
                                                     Z=float(el.attrib["Z"]))
        handle_screen_type(kwargs, "cartesian")
    elif keys >= set(["azimuth", "elevation"]):
        kwargs["centrePosition"] = PolarPosition(azimuth=float(el.attrib["azimuth"]),
                                                 elevation=float(el.attrib["elevation"]),
                                                 distance=float(el.attrib.get("distance", 1.0)))
        handle_screen_type(kwargs, "polar")
    else:
        raise ValueError("Do not know how to parse a screenCentrePosition with keys {}.".format(", ".join(sorted(el.attrib.keys()))))


def centre_position_to_xml(parent, obj):
    pos = obj.centrePosition

    if isinstance(pos, CartesianPosition):
        parent.append(
            parent.makeelement(QName(default_ns, "screenCentrePosition"),
                               X=FloatType.dumps(pos.X),
                               Y=FloatType.dumps(pos.Y),
                               Z=FloatType.dumps(pos.Z)))
    elif isinstance(pos, PolarPosition):
        parent.append(
            parent.makeelement(QName(default_ns, "screenCentrePosition"),
                               azimuth=FloatType.dumps(pos.azimuth),
                               elevation=FloatType.dumps(pos.elevation),
                               distance=FloatType.dumps(pos.distance)))
    else:
        assert False, "unexpected type"  # pragma: no cover


def handle_screen_width(kwargs, el):
    if "X" in el.attrib:
        kwargs["width"] = float(el.attrib["X"])
        handle_screen_type(kwargs, "cartesian")
    elif "azimuth" in el.attrib:
        kwargs["width"] = float(el.attrib["azimuth"])
        handle_screen_type(kwargs, "polar")
    else:
        raise ValueError("Do not know how to parse a screenWidth with keys {}.".format(", ".join(sorted(el.attrib.keys()))))


def screen_width_to_xml(parent, obj):
    if isinstance(obj, CartesianScreen):
        parent.append(
            parent.makeelement(QName(default_ns, "screenWidth"),
                               X=FloatType.dumps(obj.widthX)))
    elif isinstance(obj, PolarScreen):
        parent.append(
            parent.makeelement(QName(default_ns, "screenWidth"),
                               azimuth=FloatType.dumps(obj.widthAzimuth)))
    else:
        assert False, "unexpected type"  # pragma: no cover


def make_screen(aspectRatio, centrePosition, width, screen_type):
    if screen_type == "cartesian":
        return CartesianScreen(aspectRatio=aspectRatio,
                               centrePosition=centrePosition,
                               widthX=width)
    elif screen_type == "polar":
        return PolarScreen(aspectRatio=aspectRatio,
                           centrePosition=centrePosition,
                           widthAzimuth=width)
    else:
        assert False, "unexpected type"  # pragma: no cover


screen_handler = ElementParser(make_screen, "audioProgrammeReferenceScreen", [
    Attribute(adm_name="aspectRatio", arg_name="aspectRatio", type=FloatType, required=True),
    CustomElement("screenCentrePosition", handle_centre_position, arg_name="centrePosition", to_xml=centre_position_to_xml, required=True),
    CustomElement("screenWidth", handle_screen_width, arg_name="width", to_xml=screen_width_to_xml, required=True),
])


def make_audio_programme(referenceScreen=None, **kwargs):
    if referenceScreen is None:
        referenceScreen = default_screen
    return AudioProgramme(referenceScreen=referenceScreen, **kwargs)


loudness_handler = ElementParser(LoudnessMetadata, "loudnessMetadata", [
    Attribute(adm_name="loudnessMethod", arg_name="loudnessMethod", type=StringType),
    Attribute(adm_name="loudnessRecType", arg_name="loudnessRecType", type=StringType),
    Attribute(adm_name="loudnessCorrectionType", arg_name="loudnessCorrectionType", type=StringType),
    AttrElement(adm_name="integratedLoudness", arg_name="integratedLoudness", type=FloatType),
    AttrElement(adm_name="loudnessRange", arg_name="loudnessRange", type=FloatType),
    AttrElement(adm_name="maxTruePeak", arg_name="maxTruePeak", type=FloatType),
    AttrElement(adm_name="maxMomentary", arg_name="maxMomentary", type=FloatType),
    AttrElement(adm_name="maxShortTerm", arg_name="maxShortTerm", type=FloatType),
    AttrElement(adm_name="dialogueLoudness", arg_name="dialogueLoudness", type=FloatType),
])

programme_handler = ElementParser(make_audio_programme, "audioProgramme", [
    Attribute(adm_name="audioProgrammeID", arg_name="id", required=True),
    Attribute(adm_name="audioProgrammeName", arg_name="audioProgrammeName", required=True),
    Attribute(adm_name="audioProgrammeLanguage", arg_name="audioProgrammeLanguage"),
    Attribute(adm_name="start", arg_name="start", type=TimeType),
    Attribute(adm_name="end", arg_name="end", type=TimeType),
    Attribute(adm_name="maxDuckingDepth", arg_name="maxDuckingDepth", type=FloatType),
    RefList("audioContent"),
    screen_handler.as_handler("referenceScreen", default=default_screen),
    loudness_handler.as_list_handler("loudnessMetadata"),
])

content_handler = ElementParser(AudioContent, "audioContent", [
    Attribute(adm_name="audioContentID", arg_name="id", required=True),
    Attribute(adm_name="audioContentName", arg_name="audioContentName", required=True),
    Attribute(adm_name="audioContentLanguage", arg_name="audioContentLanguage"),
    AttrElement(adm_name="dialogue", arg_name="dialogue", type=IntType),
    RefList("audioObject"),
    loudness_handler.as_list_handler("loudnessMetadata"),
])

object_handler = ElementParser(AudioObject, "audioObject", [
    Attribute(adm_name="audioObjectID", arg_name="id", required=True),
    Attribute(adm_name="audioObjectName", arg_name="audioObjectName", required=True),
    Attribute(adm_name="start", arg_name="start", type=TimeType),
    Attribute(adm_name="duration", arg_name="duration", type=TimeType),
    Attribute(adm_name="dialogue", arg_name="dialogue", type=IntType),
    Attribute(adm_name="importance", arg_name="importance", type=IntType),
    Attribute(adm_name="interact", arg_name="interact", type=BoolType),
    Attribute(adm_name="disableDucking", arg_name="disableDucking", type=BoolType),
    RefList("audioPackFormat"),
    RefList("audioObject"),
    RefList("audioComplementaryObject"),
    ListElement(adm_name="audioTrackUIDRef", arg_name="audioTrackUIDRef", attr_name="audioTrackUIDs", type=TrackUIDRefType),
])

track_uid_handler = ElementParser(AudioTrackUID, "audioTrackUID", [
    Attribute(adm_name="UID", arg_name="id", required=True),
    Attribute(adm_name="sampleRate", arg_name="sampleRate", type=IntType),
    Attribute(adm_name="bitDepth", arg_name="bitDepth", type=IntType),
    RefElement("audioTrackFormat"),
    RefElement("audioPackFormat"),
])


def parse_adm_elements(adm, element, common_definitions=False):
    element_types = [
        ("//{ns}audioProgramme", programme_handler.parse, adm.addAudioProgramme),
        ("//{ns}audioContent", content_handler.parse, adm.addAudioContent),
        ("//{ns}audioObject", object_handler.parse, adm.addAudioObject),
        ("//{ns}audioChannelFormat", channel_format_handler.parse, adm.addAudioChannelFormat),
        ("//{ns}audioPackFormat", pack_format_handler.parse, adm.addAudioPackFormat),
        ("//{ns}audioStreamFormat", stream_format_handler.parse, adm.addAudioStreamFormat),
        ("//{ns}audioTrackFormat", track_format_handler.parse, adm.addAudioTrackFormat),
        ("//{ns}audioTrackUID", track_uid_handler.parse, adm.addAudioTrackUID),
    ]

    for path, parse_func, add_func in element_types:
        for sub_element in xpath(element, path):
            adm_element = parse_func(sub_element)

            if common_definitions:
                adm_element.is_common_definition = True

            add_func(adm_element)


def _sort_block_formats(channelFormats):
    def sort_key(bf):
        return (bf.rtime if bf.rtime is not None else Fraction(0),
                bf.duration if bf.duration is not None else Fraction(0))

    for channelFormat in channelFormats:
        block_formats = channelFormat.audioBlockFormats

        if any(sort_key(bf_a) > sort_key(bf_b)
               for bf_a, bf_b in zip(block_formats[:-1], block_formats[1:])):
            warnings.warn("out of order block formats in {id}".format(id=channelFormat.id))
            block_formats.sort(key=sort_key)


def _set_default_rtimes(channelFormats):
    """Default rtimes to 0 if a duration is provided.

    This is intended to fix the first block in object based content, where the
    rtime has sometimes been omitted. Errors with this data, like having
    multiple blocks with non-zero duration but no rtime will be caught in
    InterpretTimingMetadata.
    """
    for channelFormat in channelFormats:
        for bf in channelFormat.audioBlockFormats:
            if bf.rtime is None and bf.duration is not None:
                bf.rtime = Fraction(0)


def load_axml_doc(adm, element, lookup_references=True, fix_block_format_durations=False):
    """Load some axml into an ADM structure.

    This is a low-level function and doesn't deal with common definitions.

    Parameters:
        adm (ADM): ADM structure to add to
        element (lxml.etree._Element): parsed ADM XML
        lookup_references (bool): should we look up references?
        fix_block_format_durations (bool): should we attempt to fix up
            inaccuracies in audioBlockFormat durations?

            .. note::
               This is deprecated; use the functions in
               :mod:`ear.fileio.adm.timing_fixes` instead.
    """
    parse_adm_elements(adm, element)

    if lookup_references:
        adm.lazy_lookup_references()

    _set_default_rtimes(adm.audioChannelFormats)
    _sort_block_formats(adm.audioChannelFormats)

    if fix_block_format_durations:
        from . import timing_fixes
        warnings.warn("fix_block_format_durations is deprecated, use "
                      "the functions in ear.fileio.timing_fixes instead", DeprecationWarning)
        timing_fixes.fix_blockFormat_durations(adm)


def load_axml_string(adm, axmlstr, **kwargs):
    """Wrapper around :func:`load_axml_doc` which parses XML too.

    Parameters:
        adm (ADM): ADM structure to add to
        axmlstr (str): ADM XML string
        kwargs: see :func:`load_axml_doc`
    """
    element = lxml.etree.fromstring(axmlstr)
    load_axml_doc(adm, element, **kwargs)


def load_axml_file(adm, axmlfile, **kwargs):
    """Wrapper around :func:`load_axml_doc` which loads XML from a file.

    Parameters:
        adm (ADM): ADM structure to add to
        axmlfile (Union[str, File]): ADM XML file name or file object; see
            :func:`lxml.etree.parse`.
        kwargs: see :func:`load_axml_doc`
    """
    element = lxml.etree.parse(axmlfile)
    load_axml_doc(adm, element, **kwargs)


def parse_string(axmlstr, **kwargs):
    """Parse an ADM XML string, including loading common definitions.

    Parameters:
        axmlstr (str): ADM XML string
        kwargs: see :func:`load_axml_doc`
    Returns:
        ADM: ADM structure
    """
    adm = ADM()
    from .common_definitions import load_common_definitions
    load_common_definitions(adm)
    load_axml_string(adm, axmlstr, **kwargs)
    return adm


def parse_file(axmlfile, **kwargs):
    """Parse an ADM XML file, including loading common definitions.

    Parameters:
        axmlfile (Union[str, File]): ADM XML file name or file object; see
            :func:`lxml.etree.parse`.
        kwargs: see :func:`load_axml_doc`
    Returns:
        ADM: ADM structure
    """
    adm = ADM()
    from .common_definitions import load_common_definitions
    load_common_definitions(adm)
    load_axml_file(adm, axmlfile, **kwargs)
    return adm


@attrs
class AudioStreamFormatWrapper(object):
    """Wrapper around an audioStreamFormat which adds audioTrackFormat references."""

    wrapped = attrib()
    audioTrackFormats = attrib(default=Factory(list))

    def __getattr__(self, name):
        return getattr(self.wrapped, name)

    @classmethod
    def wrapped_audioStreamFormats(cls, adm):
        from collections import OrderedDict
        stream_formats = OrderedDict((id(stream_format), cls(stream_format))
                                     for stream_format in adm.audioStreamFormats)

        for track_format in adm.audioTrackFormats:
            if track_format.audioStreamFormat is not None:
                stream_format = track_format.audioStreamFormat
                stream_formats[id(stream_format)].audioTrackFormats.append(track_format)

        return list(stream_formats.values())


def adm_to_xml(adm: ADM) -> lxml.etree._Element:
    """Generate an XML element corresponding to an ADM structure.

    This skips elements marked with is_common_definition
    """
    audioStreamFormats = AudioStreamFormatWrapper.wrapped_audioStreamFormats(adm)

    element_types = [
        (programme_handler.to_xml, adm.audioProgrammes),
        (content_handler.to_xml, adm.audioContents),
        (object_handler.to_xml, adm.audioObjects),
        (channel_format_handler.to_xml, adm.audioChannelFormats),
        (pack_format_handler.to_xml, adm.audioPackFormats),
        (stream_format_handler.to_xml, audioStreamFormats),
        (track_format_handler.to_xml, adm.audioTrackFormats),
        (track_uid_handler.to_xml, adm.audioTrackUIDs),
    ]

    E = ElementMaker(namespace=default_ns, nsmap=default_nsmap)
    afx = E.audioFormatExtended()

    for to_xml, elements in element_types:
        for element in elements:
            if not element.is_common_definition:
                to_xml(afx, element)

    return E.ebuCoreMain(
        E.coreMetadata(
            E.format(
                afx)))
