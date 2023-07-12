import pytest
from .json import json_to_value, value_to_json
from ear.core.metadata_input import AudioBlockFormatObjects, ObjectTypeMetadata
from fractions import Fraction


def _check_json_subset(d1, d2):
    """check that dictionaries in d1 are a subset of d2, and that all values
    are representable in json"""

    def is_type(t):
        return isinstance(d1, t) and isinstance(d2, t)

    if is_type(dict):
        for key in d1:
            assert key in d2
            _check_json_subset(d1[key], d2[key])
    elif is_type(list):
        assert len(d1) == len(d2)
        for v1, v2 in zip(d1, d2):
            _check_json_subset(v1, v2)
    elif is_type(bool) or is_type(int) or is_type(float) or is_type(str):
        assert d1 == d2
    elif d1 is None and d2 is None:
        pass
    else:
        assert False, "mismatching or unknown types"


@pytest.mark.parametrize("include_defaults", [False, True])
def test_json_OTM(include_defaults):
    otm = ObjectTypeMetadata(
        block_format=AudioBlockFormatObjects(
            rtime=Fraction(1, 2), position=dict(azimuth=0, elevation=0)
        )
    )
    otm_j = value_to_json(otm, include_defaults=include_defaults)
    expected = {
        "_type": "ObjectTypeMetadata",
        "block_format": {
            "_type": "AudioBlockFormatObjects",
            "position": {
                "_type": "ObjectPolarPosition",
                "azimuth": 0.0,
                "elevation": 0.0,
            },
            "rtime": {"_type": "Fraction", "denominator": 2, "numerator": 1},
        },
    }

    _check_json_subset(expected, otm_j)

    otm_j_otm = json_to_value(otm_j)

    assert otm_j_otm == otm
