from ..time_format import parse_time, unparse_time
from fractions import Fraction
import pytest


@pytest.mark.parametrize(
    "time,expected",
    [
        (Fraction(1), "00:00:01.0"),
        (Fraction("1.5"), "00:00:01.5"),
        (Fraction("1.05"), "00:00:01.05"),
        (Fraction("0.5"), "00:00:00.5"),
        (Fraction("0.05"), "00:00:00.05"),
        (Fraction("1e-9"), "00:00:00.000000001"),
        (Fraction("3723.4"), "01:02:03.4"),
    ],
)
def test_unparse_parse_time(time, expected):
    unparsed = unparse_time(time)
    assert unparsed == expected
    parsed = parse_time(unparsed)

    assert parsed == time


def test_inaccuracy_warning():
    with pytest.warns(
        UserWarning,
        match="^loss of accuracy when converting fractional time 1/3 to decimal$",
    ):
        unparse_time(Fraction(1, 3))
