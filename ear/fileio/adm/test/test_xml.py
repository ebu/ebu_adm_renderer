import lxml.etree
from lxml.builder import ElementMaker
from fractions import Fraction
import pytest
import re
from copy import deepcopy
from ..xml import parse_string, adm_to_xml, ParseError
from ..exceptions import AdmError, AdmIDError
from ..elements import (
    AudioBlockFormatBinaural,
    CartesianZone,
    CartesianPositionOffset,
    PolarZone,
    PolarPositionOffset,
)
from ..elements.version import BS2076Version, NoVersion
from ....common import CartesianPosition, PolarPosition, CartesianScreen, PolarScreen

ns = "urn:ebu:metadata-schema:ebuCore_2015"
nsmap = dict(adm=ns)
E = ElementMaker(namespace=ns, nsmap=nsmap)


class BaseADM(object):
    """Base ADM to start tests from, with utilities for interacting with it."""

    def __init__(self, fname):
        import pkg_resources
        with pkg_resources.resource_stream(__name__, fname) as xml_file:
            self.xml = lxml.etree.parse(xml_file)

        self.adm = parse_string(lxml.etree.tostring(self.xml))

    def with_mods(self, *mods):
        """A copy of the base xml, with some modifications applied"""
        xml = deepcopy(self.xml)

        for mod in mods:
            mod(xml)

        return xml

    def adm_after_mods(self, *mods):
        """Apply modifications to base, stringify it, and run it though the parser."""
        if mods:
            xml = self.with_mods(*mods)
            xml_str = lxml.etree.tostring(xml)
            adm = parse_string(xml_str)
            check_round_trip(adm)
            return adm
        else:
            return self.adm

    def bf_after_mods(self, *mods):
        """Get the first block format after applying some modifications."""
        adm = self.adm_after_mods(*mods)
        return get_acf(adm).audioBlockFormats[0]

    def prog_after_mods(self, *mods):
        """Get the first programme after applying some modifications."""
        adm = self.adm_after_mods(*mods)
        return adm.audioProgrammes[0]


@pytest.fixture(scope="module")
def base():
    return BaseADM("test_adm_files/base.xml")


@pytest.fixture(scope="module")
def base_mat():
    return BaseADM("test_adm_files/matrix.xml")


# xml modifications: these return a function that modifies an xml tree in some way

def remove_children(xpath_to_children):
    def f(xml):
        elements = list(xml.xpath(xpath_to_children, namespaces=nsmap))
        assert elements
        for el in elements:
            el.getparent().remove(el)
    return f


def add_children(xpath_to_parent, *new_children):
    def f(xml):
        parent = xml.xpath(xpath_to_parent, namespaces=nsmap)[0]
        parent.extend(new_children)
    return f


def set_attrs(xpath_to_el, **attrs):
    def f(xml):
        elements = list(xml.xpath(xpath_to_el, namespaces=nsmap))
        assert elements
        for element in elements:
            element.attrib.update(attrs)
    return f


def del_attrs(xpath_to_el, *attrs):
    def f(xml):
        elements = list(xml.xpath(xpath_to_el, namespaces=nsmap))
        assert elements
        for element in elements:
            for attr in attrs:
                if attr in element.attrib:
                    del element.attrib[attr]
    return f


def set_version(version):
    afe_path = "//adm:audioFormatExtended"

    if isinstance(version, int):
        version = f"ITU-R_BS.2076-{version}"

    return set_attrs(afe_path, version=version)


def get_acf(adm):
    """Get the first non-common-definition channel format."""
    for cf in adm.audioChannelFormats:
        if not cf.is_common_definition:
            return cf


bf_path = "//adm:audioBlockFormat"


def test_version(base):
    assert isinstance(base.adm.version, NoVersion)

    adm = base.adm_after_mods(set_version("ITU-R_BS.2076-2"))
    assert adm.version == BS2076Version(2)

    # new versions are not supported -- historically BS.2076 has not been
    # forwards-compatible, so it's best to error out early.

    # for example:
    # - addition of audioObject gain/mute/positionOffset
    # - addition of gainUnit
    # - change of default azimuthRange for divergence

    # all of these will cause silent errors (i.e. unintended behaviour, not an
    # error message) if a document containing them is interpreted by software
    # that doesn't know about them, so let's not do that
    expected = "ADM version 'ITU-R_BS.2076-3' is not supported"
    with pytest.raises(NotImplementedError, match=expected):
        base.adm_after_mods(set_version("ITU-R_BS.2076-3"))

    # unknown
    expected = "ADM version 'ITU-R_BS.2076-2a' is not supported"
    with pytest.raises(NotImplementedError, match=expected):
        base.adm_after_mods(set_version("ITU-R_BS.2076-2a"))


def test_loudness(base):
    # test a couple of different method strings to make sure that multiple
    # elements are handled correctly
    test_methods = ["ITU-R BS.1770", "proprietary"]

    children = [
        E.loudnessMetadata(
            E.integratedLoudness("-24.0"),
            E.loudnessRange("12.5"),
            E.maxTruePeak("-5.2"),
            E.maxMomentary("-9.9"),
            E.maxShortTerm("-18.3"),
            E.dialogueLoudness("-10.2"),
            loudnessMethod=loudnessMethod,
            loudnessRecType="EBU R128",
            loudnessCorrectionType="file",
        )
        for loudnessMethod in test_methods
    ]

    def check_loudness(loudnessMetadatas):
        assert len(loudnessMetadatas) == len(test_methods)
        for loudnessMetadata, method in zip(loudnessMetadatas, test_methods):
            assert loudnessMetadata.loudnessMethod == method
            assert loudnessMetadata.loudnessRecType == "EBU R128"
            assert loudnessMetadata.loudnessCorrectionType == "file"
            assert loudnessMetadata.integratedLoudness == -24.0
            assert loudnessMetadata.loudnessRange == 12.5
            assert loudnessMetadata.maxTruePeak == -5.2
            assert loudnessMetadata.maxMomentary == -9.9
            assert loudnessMetadata.dialogueLoudness == -10.2

    # need to copy as lxml doesn't like elements appearing in more than one
    # place
    adm = base.adm_after_mods(
        add_children("//adm:audioContent", *deepcopy(children)),
        add_children("//adm:audioProgramme", *deepcopy(children)),
    )
    check_loudness(adm.audioProgrammes[0].loudnessMetadata)
    check_loudness(adm.audioContents[0].loudnessMetadata)


def test_gain(base):
    # linear
    assert base.bf_after_mods(add_children(bf_path, E.gain("0"))).gain == 0.0
    assert base.bf_after_mods(add_children(bf_path, E.gain("0.5"))).gain == 0.5
    assert (
        base.bf_after_mods(set_version(2), add_children(bf_path, E.gain("0.5", gainUnit="linear"))).gain
        == 0.5
    )

    # db
    assert (
        base.bf_after_mods(set_version(2), add_children(bf_path, E.gain("20", gainUnit="dB"))).gain
        == 10.0
    )
    expected = "gainUnit must be linear or dB, not 'DB'"
    with pytest.raises(ParseError, match=expected):
        base.bf_after_mods(set_version(2), add_children(bf_path, E.gain("20", gainUnit="DB")))

    # default
    assert base.bf_after_mods().gain == 1.0

    expected = "gainUnit is a BS.2076-2 feature"
    with pytest.raises(ParseError, match=expected):
        base.bf_after_mods(add_children(bf_path, E.gain("20", gainUnit="dB")))


def test_extent(base):
    assert base.bf_after_mods().width == 0.0
    assert base.bf_after_mods().height == 0.0
    assert base.bf_after_mods().depth == 0.0

    assert base.bf_after_mods(add_children(bf_path, E.width("0.5"))).width == 0.5
    assert base.bf_after_mods(add_children(bf_path, E.height("0.5"))).height == 0.5
    assert base.bf_after_mods(add_children(bf_path, E.depth("0.5"))).depth == 0.5


def test_channel_lock(base):
    assert base.bf_after_mods().channelLock is None

    block_format = base.bf_after_mods(add_children(bf_path, E.channelLock("1")))
    assert block_format.channelLock is not None
    assert block_format.channelLock.maxDistance is None

    block_format = base.bf_after_mods(add_children(bf_path, E.channelLock("1", maxDistance="0.5")))
    assert block_format.channelLock is not None
    assert block_format.channelLock.maxDistance == 0.5


def test_jump_position(base):
    assert base.bf_after_mods().jumpPosition.flag is False
    assert base.bf_after_mods().jumpPosition.interpolationLength is None

    block_format = base.bf_after_mods(add_children(bf_path, E.jumpPosition("1")))
    assert block_format.jumpPosition.flag is True
    assert block_format.jumpPosition.interpolationLength is None

    block_format = base.bf_after_mods(add_children(bf_path, E.jumpPosition("1", interpolationLength="0.5")))
    assert block_format.jumpPosition.flag is True
    assert block_format.jumpPosition.interpolationLength == Fraction(1, 2)


def test_divergence(base):
    assert base.bf_after_mods().objectDivergence is None

    block_format = base.bf_after_mods(add_children(bf_path, E.objectDivergence("0.5")))
    assert block_format.objectDivergence.value == 0.5
    assert block_format.objectDivergence.azimuthRange is None
    assert block_format.objectDivergence.positionRange is None

    block_format = base.bf_after_mods(add_children(bf_path, E.objectDivergence("0.5", azimuthRange="30")))
    assert block_format.objectDivergence.value == 0.5
    assert block_format.objectDivergence.azimuthRange == 30.0
    assert block_format.objectDivergence.positionRange is None

    block_format = base.bf_after_mods(add_children(bf_path, E.objectDivergence("0.5", positionRange="0.5")))
    assert block_format.objectDivergence.value == 0.5
    assert block_format.objectDivergence.positionRange == 0.5
    assert block_format.objectDivergence.azimuthRange is None


def test_polar_position(base):
    block_format = base.bf_after_mods(remove_children("//adm:position"),
                                      add_children(bf_path,
                                                   E.position("10", coordinate="azimuth", screenEdgeLock="right"),
                                                   E.position("20", coordinate="elevation", screenEdgeLock="top"),
                                                   E.position("0.5", coordinate="distance")))

    assert block_format.position.azimuth == 10.0
    assert block_format.position.elevation == 20.0
    assert block_format.position.distance == 0.5
    assert block_format.position.screenEdgeLock.horizontal == "right"
    assert block_format.position.screenEdgeLock.vertical == "top"


def test_polar_position_default_distance(base):
    block_format = base.bf_after_mods(remove_children("//adm:position"),
                                      add_children(bf_path,
                                                   E.position("10", coordinate="azimuth"),
                                                   E.position("20", coordinate="elevation")))

    assert block_format.position.azimuth == 10.0
    assert block_format.position.elevation == 20.0
    assert block_format.position.distance == 1.0


def test_invalid_screen_edge_lock(base):
    expected = "invalid screenEdgeLock value top for coordinate azimuth"
    with pytest.raises(ParseError, match=expected):
        base.bf_after_mods(remove_children("//adm:position"),
                           add_children(bf_path,
                                        E.position("10", coordinate="azimuth", screenEdgeLock="top"),
                                        E.position("20", coordinate="elevation", screenEdgeLock="top")))


def test_wrong_coordinates(base):
    expected = ("Found coordinates {(azimuth,X|X,azimuth)}, but expected either "
                "{azimuth,elevation,distance}, {azimuth,elevation}, {X,Y,Z} or {X,Y}.")
    with pytest.raises(ParseError, match=expected):
        base.bf_after_mods(remove_children("//adm:position"),
                           add_children(bf_path,
                                        E.position("10", coordinate="azimuth"),
                                        E.position("0", coordinate="X")))


def test_cart_position(base):
    block_format = base.bf_after_mods(remove_children("//adm:position"),
                                      add_children(bf_path,
                                                   E.position("0.2", coordinate="X"),
                                                   E.position("0.3", coordinate="Y"),
                                                   E.position("0.5", coordinate="Z")))

    assert block_format.position.X == 0.2
    assert block_format.position.Y == 0.3
    assert block_format.position.Z == 0.5


def test_cart_position_default_Z(base):
    block_format = base.bf_after_mods(remove_children("//adm:position"),
                                      add_children(bf_path,
                                                   E.position("0.2", coordinate="X"),
                                                   E.position("0.3", coordinate="Y")))

    assert block_format.position.X == 0.2
    assert block_format.position.Y == 0.3
    assert block_format.position.Z == 0.0


def test_exceptions(base):
    # error in element value converter
    with pytest.raises(ParseError) as excinfo:
        base.bf_after_mods(add_children(bf_path, E.gain("g")))
    expected = "error while parsing element gain on line [0-9]+: ValueError: could not convert string to float: '?g'?$"
    assert re.match(expected, str(excinfo.value)) is not None

    # error in attribute converter
    with pytest.raises(ParseError) as excinfo:
        base.bf_after_mods(set_attrs(bf_path, rtime="t"))
    expected = "error while parsing attr rtime of element audioBlockFormat on line [0-9]+: ValueError: Cannot parse time: 't'$"
    assert re.match(expected, str(excinfo.value)) is not None

    # missing items
    with pytest.raises(ParseError) as excinfo:
        base.bf_after_mods(del_attrs(bf_path, "audioBlockFormatID"))
    expected = "error while parsing element audioBlockFormat on line [0-9]+: ValueError: missing items: audioBlockFormatID$"
    assert re.match(expected, str(excinfo.value)) is not None

    # multiple elements
    with pytest.raises(ParseError) as excinfo:
        base.bf_after_mods(add_children(bf_path, E.gain("1.0"), E.gain("1.0")))
    expected = "error while parsing element gain on line [0-9]+: ValueError: multiple gain elements found$"
    assert re.match(expected, str(excinfo.value)) is not None


def test_cartesian(base):
    assert base.bf_after_mods().cartesian is False
    assert base.bf_after_mods(add_children(bf_path, E.cartesian("0"))).cartesian is False
    assert base.bf_after_mods(add_children(bf_path, E.cartesian("1"))).cartesian is True


def test_diffuse(base):
    assert base.bf_after_mods().diffuse == 0.0
    assert base.bf_after_mods(add_children(bf_path, E.diffuse("0.5"))).diffuse == 0.5


def test_screenRef(base):
    assert base.bf_after_mods().screenRef is False
    assert base.bf_after_mods(add_children(bf_path, E.screenRef("0"))).screenRef is False
    assert base.bf_after_mods(add_children(bf_path, E.screenRef("1"))).screenRef is True


def test_importance(base):
    assert base.bf_after_mods().importance == 10
    assert base.bf_after_mods(add_children(bf_path, E.importance("5"))).importance == 5


def test_zone(base):
    assert base.bf_after_mods().zoneExclusion == []
    assert base.bf_after_mods(add_children(bf_path, E.zoneExclusion())).zoneExclusion == []
    assert (base.bf_after_mods(add_children(bf_path,
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


def test_directspeakers(base):
    def with_children(*children):
        return base.bf_after_mods(
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

    # default distance
    block_format = with_children(E.position("-29", coordinate="azimuth"),
                                 E.position("15", coordinate="elevation"))
    assert block_format.position.azimuth == -29.0
    assert block_format.position.elevation == 15.0
    assert block_format.position.distance == 1.0

    # distance defaults to 1
    block_format = with_children(E.position("-29", coordinate="azimuth"),
                                 E.position("15", coordinate="elevation"))
    assert block_format.position.distance == 1.0

    # gain
    block_format = with_children(E.position("0", coordinate="azimuth"),
                                 E.position("0", coordinate="elevation"),
                                 E.gain("0.5"))
    assert block_format.gain == 0.5

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

    # default Z
    block_format = with_children(
        E.position("0.1", coordinate="X"),
        E.position("0.4", coordinate="Y"),
    )
    assert block_format.position.X == 0.1
    assert block_format.position.Y == 0.4
    assert block_format.position.Z == 0.0

    # test speaker label
    for labels in ([], ["U-030"], ["U-030", "U-SC"]):
        block_format = with_children(E.position("-29", coordinate="azimuth"),
                                     E.position("15", coordinate="elevation"),
                                     *map(E.speakerLabel, labels))
        assert block_format.speakerLabel == labels


def test_frequency(base):
    def cf_with_children(*children):
        adm = base.adm_after_mods(
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


def test_binaural(base):
    to_binaural = (
        set_attrs(
            "//adm:audioChannelFormat", typeDefinition="Binaural", typeLabel="005"
        ),
        remove_children("//adm:position"),
    )

    block_format = base.bf_after_mods(*to_binaural)
    assert isinstance(block_format, AudioBlockFormatBinaural)
    assert block_format.gain == 1.0

    block_format = base.bf_after_mods(
        *to_binaural, add_children(bf_path, E.gain("0.5"))
    )
    assert block_format.gain == 0.5


def test_hoa(base):
    def with_children(*children):
        return base.bf_after_mods(
            set_attrs("//adm:audioChannelFormat", typeDefinition="HOA", typeLabel="004"),
            remove_children("//adm:position"),
            add_children(bf_path, *children))

    assert with_children(E.gain("0.5")).gain == 0.5

    # normal usage
    block_format = with_children(E.order("1"), E.degree("-1"))
    assert block_format.equation is None
    assert block_format.order == 1
    assert block_format.degree == -1
    assert block_format.normalization is None
    assert block_format.nfcRefDist is None
    assert block_format.screenRef is None

    # explicit defaults
    block_format = with_children(E.normalization("SN3D"), E.nfcRefDist("0.0"), E.screenRef("0"))
    assert block_format.normalization == "SN3D"
    assert block_format.nfcRefDist == 0.0
    assert block_format.screenRef is False

    # specify everything
    block_format = with_children(E.equation("eqn"), E.normalization("N3D"), E.nfcRefDist("0.5"), E.screenRef("1"))
    assert block_format.equation == "eqn"
    assert block_format.normalization == "N3D"
    assert block_format.nfcRefDist == 0.5
    assert block_format.screenRef is True


def test_hoa_pack(base):
    def with_children(*children):
        return base.adm_after_mods(
            set_attrs("//adm:audioPackFormat", typeDefinition="HOA", typeLabel="004"),
            add_children("//adm:audioPackFormat", *children))["AP_00031001"]

    pack = with_children()
    assert pack.normalization is None
    assert pack.nfcRefDist is None
    assert pack.screenRef is None

    pack = with_children(E.normalization("N3D"), E.nfcRefDist("1.0"), E.screenRef("1"))
    assert pack.normalization == "N3D"
    assert pack.nfcRefDist == 1.0
    assert pack.screenRef is True


def test_matrix_structure(base_mat):
    acf = base_mat.adm.lookup_element("AC_00021003")
    [bf] = acf.audioBlockFormats
    assert [c.gain for c in bf.matrix] == [1.0, 0.7071, 0.7071]
    assert [c.inputChannelFormat.id for c in bf.matrix] == ["AC_00010001", "AC_00010003", "AC_00010005"]

    acf = base_mat.adm.lookup_element("AC_00021004")
    [bf] = acf.audioBlockFormats
    assert [c.gain for c in bf.matrix] == [1.0, 0.7071, 0.7071]
    assert [c.inputChannelFormat.id for c in bf.matrix] == ["AC_00010002", "AC_00010003", "AC_00010006"]

    acf = base_mat.adm.lookup_element("AC_00021103")
    [bf] = acf.audioBlockFormats
    assert bf.outputChannelFormat.id == "AC_00010001"

    apf_encode = base_mat.adm.lookup_element("AP_00021002")
    assert len(apf_encode.audioChannelFormats) == 2
    assert apf_encode.inputPackFormat.id == "AP_00010003"

    apf_decode = base_mat.adm.lookup_element("AP_00021102")
    assert len(apf_decode.audioChannelFormats) == 2
    assert apf_decode.outputPackFormat.id == "AP_00010002"
    [epf] = apf_decode.encodePackFormats
    assert epf.id == "AP_00021002"


def test_matrix_encode_decode_relationship(base_mat):
    for to_remove in "//adm:encodePackFormatIDRef", "//adm:decodePackFormatIDRef":
        adm = base_mat.adm_after_mods(remove_children(to_remove))

        apf_decode = adm.lookup_element("AP_00021102")
        [epf] = apf_decode.encodePackFormats
        assert epf.id == "AP_00021002"


def test_matrix_params(base_mat):
    adm = base_mat.adm_after_mods(
        del_attrs("//adm:coefficient", "gain"),
        set_attrs("//*[@audioChannelFormatID='AC_00021003']//adm:coefficient[1]", gain="1.0"),
        set_attrs("//*[@audioChannelFormatID='AC_00021003']//adm:coefficient[2]", phase="90.0"),
        set_attrs("//*[@audioChannelFormatID='AC_00021003']//adm:coefficient[3]", delay="10.5"),
        set_attrs("//*[@audioChannelFormatID='AC_00021004']//adm:coefficient[1]", gainVar="gain"),
        set_attrs("//*[@audioChannelFormatID='AC_00021004']//adm:coefficient[2]", phaseVar="phase"),
        set_attrs("//*[@audioChannelFormatID='AC_00021004']//adm:coefficient[3]", delayVar="delay"),
    )

    acf = adm.lookup_element("AC_00021003")
    [bf] = acf.audioBlockFormats
    assert [c.gain for c in bf.matrix] == [1.0, None, None]
    assert [c.phase for c in bf.matrix] == [None, 90.0, None]
    assert [c.delay for c in bf.matrix] == [None, None, 10.5]

    acf = adm.lookup_element("AC_00021004")
    [bf] = acf.audioBlockFormats
    assert [c.gainVar for c in bf.matrix] == ["gain", None, None]
    assert [c.phaseVar for c in bf.matrix] == [None, "phase", None]
    assert [c.delayVar for c in bf.matrix] == [None, None, "delay"]


def test_matrix_gain_db(base_mat):
    adm = base_mat.adm_after_mods(
        set_version(2),
        del_attrs("//adm:coefficient", "gain", "gainUnit"),
        set_attrs(
            "//*[@audioChannelFormatID='AC_00021003']//adm:coefficient[1]",
            gain="20.0",
            gainUnit="dB",
        ),
        set_attrs(
            "//*[@audioChannelFormatID='AC_00021003']//adm:coefficient[2]",
            gain="2.0",
            gainUnit="linear",
        ),
    )

    acf = adm.lookup_element("AC_00021003")
    [bf] = acf.audioBlockFormats
    assert [c.gain for c in bf.matrix] == [10.0, 2.0, None]

    expected = "gainUnit must not be specified without gain"
    with pytest.raises(ParseError, match=expected):
        base_mat.adm_after_mods(
            set_version(2),
            del_attrs("//adm:coefficient", "gain", "gainUnit"),
            set_attrs(
                "//*[@audioChannelFormatID='AC_00021003']//adm:coefficient[1]",
                gainUnit="dB",
            ),
        )

    expected = "gainUnit must be linear or dB, not 'DB'"
    with pytest.raises(ParseError, match=expected):
        base_mat.adm_after_mods(
            set_version(2),
            del_attrs("//adm:coefficient", "gain", "gainUnit"),
            set_attrs(
                "//*[@audioChannelFormatID='AC_00021003']//adm:coefficient[1]",
                gain="1.0",
                gainUnit="DB",
            ),
        )

    expected = "gainUnit is a BS.2076-2 feature"
    with pytest.raises(ParseError, match=expected):
        base_mat.adm_after_mods(
            set_version(1),
            del_attrs("//adm:coefficient", "gain", "gainUnit"),
            set_attrs(
                "//*[@audioChannelFormatID='AC_00021003']//adm:coefficient[1]",
                gain="20.0",
                gainUnit="dB",
            ),
        )


def test_matrix_outputChannelIDRef(base_mat):
    adm = base_mat.adm_after_mods(
        remove_children("//adm:audioBlockFormat/adm:outputChannelFormatIDRef"),
        add_children("//*[@audioChannelFormatID='AC_00021103']/adm:audioBlockFormat",
                     E.outputChannelIDRef("AC_00010001")),
    )

    acf = adm.lookup_element("AC_00021103")
    [bf] = acf.audioBlockFormats
    assert bf.outputChannelFormat.id == "AC_00010001"


def test_matrix_outputChannelIDRef_and_outputChannelFormatIDRef(base_mat):
    with pytest.raises(ParseError) as excinfo:
        base_mat.adm_after_mods(
            add_children("//*[@audioChannelFormatID='AC_00021103']/adm:audioBlockFormat",
                         E.outputChannelIDRef("AC_00010001")),
        )

    assert "multiple outputChannelFormat elements found" in str(excinfo.value)


def test_referenceScreen(base):
    assert base.prog_after_mods().referenceScreen == PolarScreen(
        aspectRatio=1.78,
        centrePosition=PolarPosition(
            azimuth=0.0,
            elevation=0.0,
            distance=1.0),
        widthAzimuth=58.0,
    )

    # Cartesian representation
    assert (base.prog_after_mods(add_children("//adm:audioProgramme",
                                              E.audioProgrammeReferenceScreen(E.screenWidth(X="1.5"),
                                                                              E.screenCentrePosition(
                                                                                  X="0.0",
                                                                                  Y="1.0",
                                                                                  Z="0.0"),
                                                                              aspectRatio="2.5",
                                                                              ))
                                 ).referenceScreen ==
            CartesianScreen(aspectRatio=2.5,
                            centrePosition=CartesianPosition(
                                X=0.0,
                                Y=1.0,
                                Z=0.0),
                            widthX=1.5))

    # Polar representation
    assert (base.prog_after_mods(add_children("//adm:audioProgramme",
                                              E.audioProgrammeReferenceScreen(E.screenWidth(azimuth="45.0"),
                                                                              E.screenCentrePosition(
                                                                                  azimuth="0.0",
                                                                                  elevation="0.0",
                                                                                  distance="1.0"),
                                                                              aspectRatio="2.5",
                                                                              ))
                                 ).referenceScreen ==
            PolarScreen(aspectRatio=2.5,
                        centrePosition=PolarPosition(
                            azimuth=0.0,
                            elevation=0.0,
                            distance=1.0),
                        widthAzimuth=45.0))

    # mixed types
    with pytest.raises(ParseError) as excinfo:
        base.prog_after_mods(add_children("//adm:audioProgramme",
                                          E.audioProgrammeReferenceScreen(E.screenWidth(azimuth="45.0"),
                                                                          E.screenCentrePosition(
                                                                              X="0.0",
                                                                              Y="1.0",
                                                                              Z="0.0"),
                                                                          aspectRatio="2.5",
                                                                          )))
    expected = ("error while parsing element screenCentrePosition on line [0-9]+: ValueError: "
                "Expected polar screen data, got cartesian.$")
    assert re.match(expected, str(excinfo.value)) is not None

    # missing keys in position
    with pytest.raises(ParseError) as excinfo:
        base.prog_after_mods(add_children("//adm:audioProgramme",
                                          E.audioProgrammeReferenceScreen(E.screenWidth(azimuth="45.0"),
                                                                          E.screenCentrePosition(
                                                                              X="0.0",
                                                                              Y="1.0",
                                                                              Q="0.0"),
                                                                          aspectRatio="2.5",
                                                                          )))
    expected = ("error while parsing element screenCentrePosition on line [0-9]+: "
                "ValueError: Do not know how to parse a screenCentrePosition with keys Q, X, Y.$")
    assert re.match(expected, str(excinfo.value)) is not None

    # missing key in width
    with pytest.raises(ParseError) as excinfo:
        base.prog_after_mods(add_children("//adm:audioProgramme",
                                          E.audioProgrammeReferenceScreen(E.screenWidth(az="45.0"),
                                                                          E.screenCentrePosition(
                                                                              X="0.0",
                                                                              Y="1.0",
                                                                              Z="0.0"),
                                                                          aspectRatio="2.5",
                                                                          )))
    expected = ("error while parsing element screenWidth on line [0-9]+: "
                "ValueError: Do not know how to parse a screenWidth with keys az.$")
    assert re.match(expected, str(excinfo.value)) is not None


def test_silent_tracks(base):
    adm = base.adm_after_mods(
        add_children("//adm:audioObject", E.audioTrackUIDRef("ATU_00000000")),
    )
    [ao] = adm.audioObjects

    real_atu, silent_atu = ao.audioTrackUIDs

    assert real_atu is adm.audioTrackUIDs[0]
    assert silent_atu is None


def test_audioObject_gain(base):
    [ao] = base.adm.audioObjects
    assert ao.gain == 1.0

    adm = base.adm_after_mods(
        set_version(2),
        add_children("//adm:audioObject", E.gain("0.5")),
    )
    [ao] = adm.audioObjects
    assert ao.gain == 0.5

    expected = "gain in audioObject is a BS.2076-2 feature"
    with pytest.raises(ParseError, match=expected):
        base.adm_after_mods(
            add_children("//adm:audioObject", E.gain("0.5")),
        )


def test_audioObject_mute(base):
    [ao] = base.adm.audioObjects
    assert ao.mute is False

    adm = base.adm_after_mods(
        set_version(2),
        add_children("//adm:audioObject", E.mute("1")),
    )
    [ao] = adm.audioObjects
    assert ao.mute is True

    expected = "mute in audioObject is a BS.2076-2 feature"
    with pytest.raises(ParseError, match=expected):
        base.adm_after_mods(
            add_children("//adm:audioObject", E.mute("0")),
        )


def test_audioObject_positionOffset(base):
    [ao] = base.adm.audioObjects
    assert ao.positionOffset is None

    # full polar
    adm = base.adm_after_mods(
        set_version(2),
        add_children(
            "//adm:audioObject",
            E.positionOffset("10", coordinate="azimuth"),
            E.positionOffset("20", coordinate="elevation"),
            E.positionOffset("3", coordinate="distance"),
        ),
    )
    [ao] = adm.audioObjects
    assert ao.positionOffset == PolarPositionOffset(
        azimuth=10.0, elevation=20.0, distance=3.0
    )

    # partial polar
    adm = base.adm_after_mods(
        set_version(2),
        add_children("//adm:audioObject", E.positionOffset("20", coordinate="azimuth")),
    )
    [ao] = adm.audioObjects
    assert ao.positionOffset.azimuth == 20.0

    # cartesian
    adm = base.adm_after_mods(
        set_version(2),
        add_children(
            "//adm:audioObject",
            E.positionOffset("0.1", coordinate="X"),
            E.positionOffset("0.2", coordinate="Y"),
            E.positionOffset("0.3", coordinate="Z"),
        ),
    )
    [ao] = adm.audioObjects
    assert ao.positionOffset == CartesianPositionOffset(X=0.1, Y=0.2, Z=0.3)

    expected = "positionOffset in audioObject is a BS.2076-2 feature"
    with pytest.raises(ParseError, match=expected):
        base.adm_after_mods(
            add_children(
                "//adm:audioObject", E.positionOffset("20", coordinate="azimuth")
            ),
        )

    expected = "Found positionOffset coordinates {X,azimuth}, but expected {azimuth,elevation,distance} or {X,Y,Z}."
    with pytest.raises(ParseError, match=expected):
        base.adm_after_mods(
            set_version(2),
            add_children(
                "//adm:audioObject",
                E.positionOffset("20", coordinate="azimuth"),
                E.positionOffset("0.5", coordinate="X"),
            ),
        )

    expected = "duplicate azimuth coordinates specified"
    with pytest.raises(ParseError, match=expected):
        base.adm_after_mods(
            set_version(2),
            add_children(
                "//adm:audioObject",
                E.positionOffset("20", coordinate="azimuth"),
                E.positionOffset("20", coordinate="azimuth"),
            ),
        )

    expected = "missing coordinate attr"
    with pytest.raises(ParseError, match=expected):
        base.adm_after_mods(
            set_version(2),
            add_children(
                "//adm:audioObject",
                E.positionOffset("20"),
            ),
        )


def test_audioObject_alternativeValueSet_positionOffset(base):
    adm = base.adm_after_mods(
        set_version(2),
        add_children(
            "//adm:audioObject",
            # empty
            E.alternativeValueSet(
                alternativeValueSetID="AVS_1001_0001",
            ),
            # full
            E.alternativeValueSet(
                E.gain("0.5"),
                E.mute("1"),
                E.positionOffset("10.0", coordinate="azimuth"),
                E.positionOffset("20.0", coordinate="elevation"),
                E.positionOffset("0.25", coordinate="distance"),
                alternativeValueSetID="AVS_1001_0002",
            ),
        ),
    )
    [ao] = adm.audioObjects
    [avs_default, avs_full] = ao.alternativeValueSets

    assert avs_default.id == "AVS_1001_0001"
    assert avs_default.gain is None
    assert avs_default.mute is None
    assert avs_default.positionOffset is None

    assert avs_full.id == "AVS_1001_0002"
    assert avs_full.gain == 0.5
    assert avs_full.mute is True
    assert avs_full.positionOffset == PolarPositionOffset(
        azimuth=10.0, elevation=20.0, distance=0.25
    )

    expected = "alternativeValueSet in audioObject is a BS.2076-2 feature"
    with pytest.raises(ParseError, match=expected):
        base.adm_after_mods(
            add_children(
                "//adm:audioObject",
                E.alternativeValueSet(
                    alternativeValueSetID="AVS_1001_0001",
                ),
            )
        )


def test_audioObject_alternativeValueSet_references(base):
    adm = base.adm_after_mods(
        set_version(2),
        add_children(
            "//adm:audioObject",
            E.alternativeValueSet(
                alternativeValueSetID="AVS_1001_0001",
            ),
        ),
        add_children(
            "//adm:audioProgramme",
            E.alternativeValueSetIDRef("AVS_1001_0001"),
        ),
        add_children(
            "//adm:audioContent",
            E.alternativeValueSetIDRef("AVS_1001_0001"),
        ),
    )

    [ao] = adm.audioObjects
    [avs] = ao.alternativeValueSets

    [ap] = adm.audioProgrammes
    [ap_avs_ref] = ap.alternativeValueSets
    assert ap_avs_ref is avs

    [ac] = adm.audioContents
    [ac_avs_ref] = ac.alternativeValueSets
    assert ac_avs_ref is avs


def test_audioObject_alternativeValueSet_only_dash2(base):
    expected = "alternativeValueSetIDRef in audioProgramme is a BS.2076-2 feature"
    with pytest.raises(ParseError, match=expected):
        base.adm_after_mods(
            add_children(
                "//adm:audioProgramme", E.alternativeValueSetIDRef("AVS_1001_0001")
            )
        )


def test_audioObject_alternativeValueSet_duplicate(base):
    expected = "duplicate objects with id=AVS_1001_0001"
    with pytest.raises(AdmIDError, match=expected):
        base.adm_after_mods(
            set_version(2),
            add_children(
                "//adm:audioObject",
                E.alternativeValueSet(
                    alternativeValueSetID="AVS_1001_0001",
                ),
                E.alternativeValueSet(
                    alternativeValueSetID="AVS_1001_0001",
                ),
            ),
        )


def test_audioObject_alternativeValueSet_unknown(base):
    expected = "unknown alternativeValueSet AVS_1001_0002"
    with pytest.raises(KeyError, match=expected):
        base.adm_after_mods(
            set_version(2),
            add_children(
                "//adm:audioObject",
                E.alternativeValueSet(
                    alternativeValueSetID="AVS_1001_0001",
                ),
            ),
            add_children(
                "//adm:audioContent",
                E.alternativeValueSetIDRef("AVS_1001_0002"),
            ),
        )


def test_track_stream_ref(base):
    """Check that the track->stream ref is established by a reference in either direction."""
    with pytest.warns(UserWarning, match=("audioTrackFormat AT_00011001_01 has no audioStreamFormatIDRef; "
                                          "this may be incompatible with some software")):
        adm = base.adm_after_mods(
            remove_children("//adm:audioTrackFormat/adm:audioStreamFormatIDRef"),
        )
    assert adm["AT_00011001_01"].audioStreamFormat is adm["AS_00011001"]

    with pytest.warns(UserWarning, match=("audioStreamFormat AS_00011001 has no audioTrackFormatIDRef; "
                                          "this may be incompatible with some software")):
        adm = base.adm_after_mods(
            remove_children("//adm:audioStreamFormat/adm:audioTrackFormatIDRef"),
        )
        assert adm["AT_00011001_01"].audioStreamFormat is adm["AS_00011001"]

    expected = "audioTrackFormat AT_00011001_01 is linked to more than one audioStreamFormat"
    with pytest.raises(AdmError, match=expected):
        base.adm_after_mods(add_children("//adm:audioFormatExtended",
                                         E.audioStreamFormat(
                                             E.audioChannelFormatIDRef("AC_00031001"),
                                             E.audioTrackFormatIDRef("AT_00011001_01"),
                                             audioStreamFormatID="AS_00011002",
                                             audioStreamFormatName="PCM_Noise2",
                                             formatDefinition="PCM", formatLabel="0001")))


def test_atu_acf_ref(base):
    mods = (
        remove_children("//adm:audioTrackUID/adm:audioTrackFormatIDRef"),
        add_children("//adm:audioTrackUID", E.audioChannelFormatIDRef("AC_00031001")),
    )
    adm = base.adm_after_mods(
        set_version(2),
        *mods,
    )

    assert adm["ATU_00000001"].audioChannelFormat is adm["AC_00031001"]
    assert adm["ATU_00000001"].audioTrackFormat is None

    expected = "audioChannelFormatIDRef in audioTrackUID is a BS.2076-2 feature"
    with pytest.raises(ParseError, match=expected):
        adm = base.adm_after_mods(*mods)


def test_set_default_rtimes(base):
    """Check that the audioBlockFormats with a duration but no rtime are given an rtime,
    and a warning is issued.
    """
    with pytest.warns(
        UserWarning,
        match=(
            "added missing rtime to AB_00031001_00000001; BS.2127-0 states "
            "that rtime and duration should both be present or absent"
        ),
    ):
        bf = base.bf_after_mods(del_attrs(bf_path, "rtime"))
        assert bf.rtime == Fraction(0)


def as_dict(inst):
    """Turn an adm element into a dict to be used for comparison.

    Object references are turned into the IDs of the objects being referred
    to, and ID references are ignored; parent reference is ignored.
    """
    d = {}
    from attr import fields
    for field in fields(type(inst)):
        if field.name.endswith("Ref"): continue

        value = getattr(inst, field.name)

        if field.name == "audioBlockFormats":
            value = list(map(as_dict, value))
        if hasattr(value, "id"):
            value = value.id
        elif isinstance(value, list):
            value = [item.id if hasattr(item, "id") else item for item in value]

        d[field.name] = value

    return d


def check_round_trip(adm):
    import attr

    xml = adm_to_xml(adm)
    xml_str = lxml.etree.tostring(xml, pretty_print=True)
    parsed_adm = parse_string(xml_str)

    assert len(list(parsed_adm.elements)) == len(list(adm.elements))

    for element_orig, element_parsed in zip(
            sorted(adm.elements, key=lambda el: el.id),
            sorted(parsed_adm.elements, key=lambda el: el.id)):

        assert as_dict(element_orig) == as_dict(element_parsed)

    assert attr.asdict(parsed_adm) == attr.asdict(adm)


def test_round_trip_base(base):
    check_round_trip(base.adm)


def test_round_trip_matrix(base_mat):
    check_round_trip(base_mat.adm)
