from enum import Enum


class Type(Enum):
    """Represents the type of a matrix audioPackFormat."""
    DIRECT = 1
    ENCODE = 2
    DECODE = 4


def type_of(apf):
    """Get the type of a matrix audioPackFormat.

    Direct packs have both inputPackFormat and outputPackFormat, while encode
    packs just have inputPackFormat and decode packs just have
    outputPackFormat.

    These aren't the only attributes that cane be used to determine the type --
    it would be just as valid to look at the encode/decode relationship, but
    this is easiest, so validate the rest of the metadata against this.
    """
    if apf.inputPackFormat is not None and apf.outputPackFormat is not None:
        return Type.DIRECT
    elif apf.inputPackFormat is not None:
        return Type.ENCODE
    elif apf.outputPackFormat is not None:
        return Type.DECODE
    else:
        assert False, "matrix types have either input or output pack format refs"  # pragma: no cover


def input_pack_format(apf):
    """Get the input pack format for a matrix pack -- either the
    encodePackFormat or the inputPackFormat depending on the type."""
    if type_of(apf) == Type.DECODE:
        [encode_apf] = apf.encodePackFormats
        return encode_apf
    else:
        return apf.inputPackFormat
