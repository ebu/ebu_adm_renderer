import lxml.etree
from lxml.builder import ElementMaker
from fractions import Fraction
import pytest
import re
from copy import deepcopy
from ..xml import parse_string, adm_to_xml, ParseError
from ..elements import AudioBlockFormatBinaural, CartesianZone, PolarZone
from ....common import CartesianPosition, PolarPosition, CartesianScreen, PolarScreen

ns = "urn:ebu:metadata-schema:ebuCore_2015"
nsmap = dict(adm=ns)
E = ElementMaker(namespace=ns, nsmap=nsmap)


# load base.xml as a starting point
def load_base():
    import pkg_resources
    fname = "test_adm_files/base.xml"
    with pkg_resources.resource_stream(__name__, fname) as xml_file:
        return lxml.etree.parse(xml_file)


base_xml = load_base()
base_adm = parse_string(lxml.etree.tostring(base_xml))


# xml modifications: these return a function that modifies an xml tree in some way

def remove_children(xpath_to_children):
    def f(xml):
        for el in xml.xpath(xpath_to_children, namespaces=nsmap):
            el.getparent().remove(el)
    return f


def add_children(xpath_to_parent, *new_children):
    def f(xml):
        parent = xml.xpath(xpath_to_parent, namespaces=nsmap)[0]
        parent.extend(new_children)
    return f


def set_attrs(xpath_to_el, **attrs):
    def f(xml):
        for element in xml.xpath(xpath_to_el, namespaces=nsmap):
            element.attrib.update(attrs)
    return f


def del_attrs(xpath_to_el, *attrs):
    def f(xml):
        for element in xml.xpath(xpath_to_el, namespaces=nsmap):
            for attr in attrs:
                del element.attrib[attr]
    return f


def base_with_mods(*mods):
    """A copy of the base xml, with some modifications applied"""
    xml = deepcopy(base_xml)

    for mod in mods:
        mod(xml)

    return xml


def get_acf(adm):
    """Get the first non-common-definition channel format."""
    for cf in adm.audioChannelFormats:
        if not cf.is_common_definition:
            return cf


def parsed_adm_after_mods(*mods):
    """Apply modifications to base, stringify it, and run it though the parser."""
    if mods:
        xml = base_with_mods(*mods)
        xml_str = lxml.etree.tostring(xml)
        adm = parse_string(xml_str)
        check_round_trip(adm)
        return adm
    else:
        return base_adm


def parsed_bf_after_mods(*mods):
    adm = parsed_adm_after_mods(*mods)
    return get_acf(adm).audioBlockFormats[0]


def parsed_prog_after_mods(*mods):
    adm = parsed_adm_after_mods(*mods)
    return adm.audioProgrammes[0]


bf_path = "//adm:audioBlockFormat"


def test_gain():
    assert parsed_bf_after_mods(add_children(bf_path, E.gain("0"))).gain == 0.0
    assert parsed_bf_after_mods(add_children(bf_path, E.gain("0.5"))).gain == 0.5
    assert parsed_bf_after_mods().gain == 1.0


def test_extent():
    assert parsed_bf_after_mods().width == 0.0
    assert parsed_bf_after_mods().height == 0.0
    assert parsed_bf_after_mods().depth == 0.0

    assert parsed_bf_after_mods(add_children(bf_path, E.width("0.5"))).width == 0.5
    assert parsed_bf_after_mods(add_children(bf_path, E.height("0.5"))).height == 0.5
    assert parsed_bf_after_mods(add_children(bf_path, E.depth("0.5"))).depth == 0.5


def test_channel_lock():
    assert parsed_bf_after_mods().channelLock is None

    block_format = parsed_bf_after_mods(add_children(bf_path, E.channelLock("1")))
    assert block_format.channelLock is not None
    assert block_format.channelLock.maxDistance is None

    block_format = parsed_bf_after_mods(add_children(bf_path, E.channelLock("1", maxDistance="0.5")))
    assert block_format.channelLock is not None
    assert block_format.channelLock.maxDistance == 0.5


def test_jump_position():
    assert parsed_bf_after_mods().jumpPosition.flag is False
    assert parsed_bf_after_mods().jumpPosition.interpolationLength is None

    block_format = parsed_bf_after_mods(add_children(bf_path, E.jumpPosition("1")))
    assert block_format.jumpPosition.flag is True
    assert block_format.jumpPosition.interpolationLength is None

    block_format = parsed_bf_after_mods(add_children(bf_path, E.jumpPosition("1", interpolationLength="0.5")))
    assert block_format.jumpPosition.flag is True
    assert block_format.jumpPosition.interpolationLength == Fraction(1, 2)


def test_divergence():
    assert parsed_bf_after_mods().objectDivergence is None

    block_format = parsed_bf_after_mods(add_children(bf_path, E.objectDivergence("0.5")))
    assert block_format.objectDivergence.value == 0.5
    assert block_format.objectDivergence.azimuthRange is None
    assert block_format.objectDivergence.positionRange is None

    block_format = parsed_bf_after_mods(add_children(bf_path, E.objectDivergence("0.5", azimuthRange="30")))
    assert block_format.objectDivergence.value == 0.5
    assert block_format.objectDivergence.azimuthRange == 30.0
    assert block_format.objectDivergence.positionRange is None

    block_format = parsed_bf_after_mods(add_children(bf_path, E.objectDivergence("0.5", positionRange="0.5")))
    assert block_format.objectDivergence.value == 0.5
    assert block_format.objectDivergence.positionRange == 0.5
    assert block_format.objectDivergence.azimuthRange is None


def test_polar_position():
    block_format = parsed_bf_after_mods(remove_children("//adm:position"),
                                        add_children(bf_path,
                                                     E.position("10", coordinate="azimuth", screenEdgeLock="right"),
                                                     E.position("20", coordinate="elevation", screenEdgeLock="top"),
                                                     E.position("0.5", coordinate="distance")))

    assert block_format.position.azimuth == 10.0
    assert block_format.position.elevation == 20.0
    assert block_format.position.distance == 0.5
    assert block_format.position.screenEdgeLock.horizontal == "right"
    assert block_format.position.screenEdgeLock.vertical == "top"


def test_cart_position():
    block_format = parsed_bf_after_mods(remove_children("//adm:position"),
                                        add_children(bf_path,
                                                     E.position("0.2", coordinate="X"),
                                                     E.position("0.3", coordinate="Y"),
                                                     E.position("0.5", coordinate="Z")))

    assert block_format.position.X == 0.2
    assert block_format.position.Y == 0.3
    assert block_format.position.Z == 0.5


def test_exceptions():
    # error in element value converter
    with pytest.raises(ParseError) as excinfo:
        parsed_bf_after_mods(add_children(bf_path, E.gain("g")))
    expected = "error while parsing element gain on line [0-9]+: ValueError: could not convert string to float: '?g'?$"
    assert re.match(expected, str(excinfo.value)) is not None

    # error in attribute converter
    with pytest.raises(ParseError) as excinfo:
        parsed_bf_after_mods(set_attrs(bf_path, rtime="t"))
    expected = "error while parsing attr rtime of element audioBlockFormat on line [0-9]+: ValueError: Cannot parse time: 't'$"
    assert re.match(expected, str(excinfo.value)) is not None

    # missing items
    with pytest.raises(ParseError) as excinfo:
        parsed_bf_after_mods(del_attrs(bf_path, "audioBlockFormatID"))
    expected = "error while parsing element audioBlockFormat on line [0-9]+: ValueError: missing items: audioBlockFormatID$"
    assert re.match(expected, str(excinfo.value)) is not None

    # multiple elements
    with pytest.raises(ParseError) as excinfo:
        parsed_bf_after_mods(add_children(bf_path, E.gain("1.0"), E.gain("1.0")))
    expected = "error while parsing element gain on line [0-9]+: ValueError: multiple gain elements found$"
    assert re.match(expected, str(excinfo.value)) is not None


def test_cartesian():
    assert parsed_bf_after_mods().cartesian is False
    assert parsed_bf_after_mods(add_children(bf_path, E.cartesian("0"))).cartesian is False
    assert parsed_bf_after_mods(add_children(bf_path, E.cartesian("1"))).cartesian is True


def test_diffuse():
    assert parsed_bf_after_mods().diffuse == 0.0
    assert parsed_bf_after_mods(add_children(bf_path, E.diffuse("0.5"))).diffuse == 0.5


def test_screenRef():
    assert parsed_bf_after_mods().screenRef is False
    assert parsed_bf_after_mods(add_children(bf_path, E.screenRef("0"))).screenRef is False
    assert parsed_bf_after_mods(add_children(bf_path, E.screenRef("1"))).screenRef is True


def test_importance():
    assert parsed_bf_after_mods().importance is 10
    assert parsed_bf_after_mods(add_children(bf_path, E.importance("5"))).importance == 5


def test_zone():
    assert parsed_bf_after_mods().zoneExclusion == []
    assert parsed_bf_after_mods(add_children(bf_path, E.zoneExclusion())).zoneExclusion == []
    assert (parsed_bf_after_mods(add_children(bf_path,
                                              E.zoneExclusion(E.zone(minX="-1.0",
                                                                     minY="-0.9",
                                                                     minZ="-0.8",
                                                                     maxX="0.8",
                                                                     maxY="0.9",
                                                                     maxZ="1.0"),
                                                              E.zone(minElevation="-20", maxElevation="20",
                                                                     minAzimuth="-30", maxAzimuth="30")))
                                 ).zoneExclusion == [CartesianZone(minX=-1.0,
                                                                   minY=-0.9,
                                                                   minZ=-0.8,
                                                                   maxX=0.8,
                                                                   maxY=0.9,
                                                                   maxZ=1.0),
                                                     PolarZone(minElevation=-20.0, maxElevation=20.0,
                                                               minAzimuth=-30.0, maxAzimuth=30.0)])


def test_directspeakers():
    def with_children(*children):
        return parsed_bf_after_mods(
            set_attrs("//adm:audioChannelFormat", typeDefinition="DirectSpeakers", typeLabel="001"),
            remove_children("//adm:position"),
            add_children(bf_path,
                         *children))

    # test values and screen edge attributes
    block_format = with_children(E.position("-29", coordinate="azimuth", screenEdgeLock="right"),
                                 E.position("15", coordinate="elevation", screenEdgeLock="top"),
                                 E.position("0.9", coordinate="distance"))
    assert block_format.position.azimuth == -29.0
    assert block_format.position.screenEdgeLock.horizontal == "right"
    assert block_format.position.elevation == 15.0
    assert block_format.position.screenEdgeLock.vertical == "top"
    assert block_format.position.distance == 0.9

    # distance defaults to 1
    block_format = with_children(E.position("-29", coordinate="azimuth"),
                                 E.position("15", coordinate="elevation"))
    assert block_format.position.distance == 1.0

    # test min and max
    block_format = with_children(E.position("-29", coordinate="azimuth"),
                                 E.position("-28", coordinate="azimuth", bound="max"),
                                 E.position("-30", coordinate="azimuth", bound="min"),
                                 E.position("15", coordinate="elevation"),
                                 E.position("16", coordinate="elevation", bound="max"),
                                 E.position("14", coordinate="elevation", bound="min"),
                                 E.position("0.9", coordinate="distance"),
                                 E.position("1.1", coordinate="distance", bound="max"),
                                 E.position("0.8", coordinate="distance", bound="min"))
    assert block_format.position.azimuth == -29.0
    assert block_format.position.bounded_azimuth.max == -28.0
    assert block_format.position.bounded_azimuth.min == -30.0
    assert block_format.position.elevation == 15.0
    assert block_format.position.bounded_elevation.max == 16.0
    assert block_format.position.bounded_elevation.min == 14.0
    assert block_format.position.distance == 0.9
    assert block_format.position.bounded_distance.max == 1.1
    assert block_format.position.bounded_distance.min == 0.8

    # test Cartesian
    block_format = with_children(
        E.position("0.1", coordinate="X"),
        E.position("0.2", coordinate="X", bound="max"),
        E.position("0.3", coordinate="X", bound="min"),
        E.position("0.4", coordinate="Y"),
        E.position("0.5", coordinate="Y", bound="max"),
        E.position("0.6", coordinate="Y", bound="min"),
        E.position("0.7", coordinate="Z"),
        E.position("0.8", coordinate="Z", bound="max"),
        E.position("0.9", coordinate="Z", bound="min"),
    )
    assert block_format.position.X == 0.1
    assert block_format.position.bounded_X.max == 0.2
    assert block_format.position.bounded_X.min == 0.3
    assert block_format.position.Y == 0.4
    assert block_format.position.bounded_Y.max == 0.5
    assert block_format.position.bounded_Y.min == 0.6
    assert block_format.position.Z == 0.7
    assert block_format.position.bounded_Z.max == 0.8
    assert block_format.position.bounded_Z.min == 0.9

    # test speaker label
    for labels in ([], ["U-030"], ["U-030", "U-SC"]):
        block_format = with_children(E.position("-29", coordinate="azimuth"),
                                     E.position("15", coordinate="elevation"),
                                     *map(E.speakerLabel, labels))
        assert block_format.speakerLabel == labels


def test_frequency():
    def cf_with_children(*children):
        adm = parsed_adm_after_mods(
            add_children("//adm:audioChannelFormat", *children))
        return get_acf(adm)

    # check defaults
    cf = cf_with_children()
    assert cf.frequency.lowPass is None and cf.frequency.highPass is None

    # both defined
    cf = cf_with_children(E.frequency("500", typeDefinition="lowPass"),
                          E.frequency("100", typeDefinition="highPass"))
    assert cf.frequency.lowPass == 500.0 and cf.frequency.highPass == 100.0

    # check type
    with pytest.raises(ParseError) as excinfo:
        cf_with_children(E.frequency("500", typeDefinition="fooPass"))
    expected = "error while parsing element frequency on line [0-9]+: ValueError: frequency type must be lowPass or highPass, not fooPass"
    assert re.match(expected, str(excinfo.value)) is not None

    # check repeated
    for type in "lowPass", "highPass":
        with pytest.raises(ParseError) as excinfo:
            cf_with_children(E.frequency("500", typeDefinition=type),
                             E.frequency("500", typeDefinition=type))
        expected = "error while parsing element frequency on line [0-9]+: ValueError: More than one {} frequency element specified.".format(type)
        assert re.match(expected, str(excinfo.value)) is not None


def test_binaural():
    block_format = parsed_bf_after_mods(
        set_attrs("//adm:audioChannelFormat", typeDefinition="Binaural", typeLabel="005"),
        remove_children("//adm:position"))

    assert isinstance(block_format, AudioBlockFormatBinaural)


def test_hoa():
    def with_children(*children):
        return parsed_bf_after_mods(
            set_attrs("//adm:audioChannelFormat", typeDefinition="HOA", typeLabel="004"),
            remove_children("//adm:position"),
            add_children(bf_path, *children))

    # normal usage
    block_format = with_children(E.order("1"), E.degree("-1"))
    assert block_format.equation is None
    assert block_format.order == 1
    assert block_format.degree == -1
    assert block_format.normalization == "SN3D"
    assert block_format.nfcRefDist is None
    assert block_format.screenRef is False

    # explicit defaults
    block_format = with_children(E.normalization("SN3D"), E.nfcRefDist("0.0"), E.screenRef("0"))
    assert block_format.normalization == "SN3D"
    assert block_format.nfcRefDist is None  # adm says that 0 is same as unspecified
    assert block_format.screenRef is False

    # specify everything
    block_format = with_children(E.equation("eqn"), E.normalization("N3D"), E.nfcRefDist("0.5"), E.screenRef("1"))
    assert block_format.equation == "eqn"
    assert block_format.normalization == "N3D"
    assert block_format.nfcRefDist == 0.5
    assert block_format.screenRef is True


def test_referenceScreen():
    assert parsed_prog_after_mods().referenceScreen == PolarScreen(
        aspectRatio=1.78,
        centrePosition=PolarPosition(
            azimuth=0.0,
            elevation=0.0,
            distance=1.0),
        widthAzimuth=58.0,
    )

    # Cartesian representation
    assert (parsed_prog_after_mods(add_children("//adm:audioProgramme",
                                                E.audioProgrammeReferenceScreen(E.aspectRatio("2.5"),
                                                                                E.screenWidth(X="1.5"),
                                                                                E.screenCentrePosition(
                                                                                    X="0.0",
                                                                                    Y="1.0",
                                                                                    Z="0.0")))
                                   ).referenceScreen ==
            CartesianScreen(aspectRatio=2.5,
                            centrePosition=CartesianPosition(
                                X=0.0,
                                Y=1.0,
                                Z=0.0),
                            widthX=1.5))

    # Polar representation
    assert (parsed_prog_after_mods(add_children("//adm:audioProgramme",
                                                E.audioProgrammeReferenceScreen(E.aspectRatio("2.5"),
                                                                                E.screenWidth(azimuth="45.0"),
                                                                                E.screenCentrePosition(
                                                                                    azimuth="0.0",
                                                                                    elevation="0.0",
                                                                                    distance="1.0")))
                                   ).referenceScreen ==
            PolarScreen(aspectRatio=2.5,
                        centrePosition=PolarPosition(
                            azimuth=0.0,
                            elevation=0.0,
                            distance=1.0),
                        widthAzimuth=45.0))

    # mixed types
    with pytest.raises(ParseError) as excinfo:
        parsed_prog_after_mods(add_children("//adm:audioProgramme",
                                            E.audioProgrammeReferenceScreen(E.aspectRatio("2.5"),
                                                                            E.screenWidth(azimuth="45.0"),
                                                                            E.screenCentrePosition(
                                                                                X="0.0",
                                                                                Y="1.0",
                                                                                Z="0.0"))))
    expected = ("error while parsing element screenCentrePosition on line [0-9]+: ValueError: "
                "Expected polar screen data, got cartesian.$")
    assert re.match(expected, str(excinfo.value)) is not None

    # missing keys in position
    with pytest.raises(ParseError) as excinfo:
        parsed_prog_after_mods(add_children("//adm:audioProgramme",
                                            E.audioProgrammeReferenceScreen(E.aspectRatio("2.5"),
                                                                            E.screenWidth(azimuth="45.0"),
                                                                            E.screenCentrePosition(
                                                                                X="0.0",
                                                                                Y="1.0",
                                                                                Q="0.0"))))
    expected = ("error while parsing element screenCentrePosition on line [0-9]+: "
                "ValueError: Do not know how to parse a screenCentrePosition with keys Q, X, Y.$")
    assert re.match(expected, str(excinfo.value)) is not None

    # missing key in width
    with pytest.raises(ParseError) as excinfo:
        parsed_prog_after_mods(add_children("//adm:audioProgramme",
                                            E.audioProgrammeReferenceScreen(E.aspectRatio("2.5"),
                                                                            E.screenWidth(az="45.0"),
                                                                            E.screenCentrePosition(
                                                                                X="0.0",
                                                                                Y="1.0",
                                                                                Z="0.0"))))
    expected = ("error while parsing element screenWidth on line [0-9]+: "
                "ValueError: Do not know how to parse a screenWidth with keys az.$")
    assert re.match(expected, str(excinfo.value)) is not None


def as_dict(inst):
    """Turn an adm element into a dict to be used for comparison.

    Object references are turned into the IDs of the objects being referred
    to, and ID references are ignored; parent reference is ignored.
    """
    d = {}
    from attr import fields
    for field in fields(type(inst)):
        if field.name.endswith("Ref"): continue
        if field.name == "adm_parent": continue

        value = getattr(inst, field.name)

        if field.name == "audioBlockFormats":
            value = list(map(as_dict, value))
        if hasattr(value, "id"):
            value = value.id
        elif isinstance(value, list) and len(value) and hasattr(value[0], "id"):
            value = [item.id for item in value]

        d[field.name] = value

    return d


def check_round_trip(adm):
    xml = adm_to_xml(adm)
    xml_str = lxml.etree.tostring(xml, pretty_print=True)
    parsed_adm = parse_string(xml_str)

    assert len(list(parsed_adm.elements)) == len(list(adm.elements))

    for element_orig, element_parsed in zip(
            sorted(adm.elements, key=lambda el: el.id),
            sorted(parsed_adm.elements, key=lambda el: el.id)):

        assert as_dict(element_orig) == as_dict(element_parsed)


def test_round_trip_base():
    check_round_trip(base_adm)
