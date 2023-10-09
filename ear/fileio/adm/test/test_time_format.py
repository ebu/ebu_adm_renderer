from ..time_format import parse_time, unparse_time, FractionalTime
from fractions import Fraction
import pytest


def time_equal(a, b):
    if isinstance(a, FractionalTime) is not isinstance(b, FractionalTime):
        return False
    if isinstance(a, FractionalTime):
        return a == b and a.format_denominator == b.format_denominator
    else:
        return a == b


@pytest.mark.parametrize(
    "time_str,match",
    [
        ("1.0", "Cannot parse time"),
        ("0:0:0.", "Cannot parse time"),
        ("0:0:0", "Cannot parse time"),
        ("00:00:00.2S1", "numerator must be less than denominator"),
        ("00:00:00.0S0", "numerator must be less than denominator"),
        ("00:00:00.-1S0", "Cannot parse time"),
    ],
)
def test_parse_invalid(time_str, match):
    with pytest.raises(ValueError, match=match):
        parse_time(time_str)


@pytest.mark.parametrize(
    "time_str,expected",
    [
        # decimal -> Fraction
        ("00:00:00.5", Fraction(1, 2)),
        # fraction -> FractionalTime
        ("00:00:00.1S2", FractionalTime(1, 2)),
        # fraction not normalised
        ("00:00:00.2S6", FractionalTime(2, 6)),
        # test all places
        ("01:02:03.4", Fraction("3723.4")),
        ("01:02:03.2S5", FractionalTime("3723.4")),
        # decimals in right position
        ("00:00:00.000000001", Fraction("1e-9")),
    ],
)
def test_parse_time(time_str, expected):
    parsed = parse_time(time_str)
    assert time_equal(parsed, expected)


@pytest.mark.parametrize(
    "time,allow_fractional,expected",
    [
        # Fraction representable as decimal is always decimal
        (Fraction(1, 2), False, "00:00:00.5"),
        (Fraction(1, 2), True, "00:00:00.5"),
        # FractionalTime representable as decimal is decimal without warnings
        # when fractional is disabled
        (FractionalTime(2, 4), False, "00:00:00.5"),
        # FractionalTime representable as decimal is fractional when enabled
        (FractionalTime(2, 4), True, "00:00:00.2S4"),
        # FractionalTime not representable as decimal is fractional without warning when enabled
        (FractionalTime(1, 3), True, "00:00:00.1S3"),
        # Fraction not representable as decimal is fractional without warning when enabled
        (Fraction(1, 3), True, "00:00:00.1S3"),
        # test all places
        (Fraction("3723.4"), False, "01:02:03.4"),
        (FractionalTime("3723.4"), True, "01:02:03.2S5"),
        # decimals in right position
        (Fraction("1"), False, "00:00:01.0"),
        (Fraction("1e-9"), False, "00:00:00.000000001"),
    ],
)
def test_unparse_time(time, allow_fractional, expected):
    assert unparse_time(time, allow_fractional) == expected


def test_inaccuracy_warning():
    with pytest.warns(
        UserWarning,
        match="^loss of accuracy when converting fractional time 1/3 to decimal$",
    ):
        unparse_time(Fraction(1, 3))

    with pytest.warns(
        UserWarning,
        match="^loss of accuracy when converting fractional time 1/3 to decimal$",
    ):
        unparse_time(FractionalTime(1, 3))


class TestFractionalTime:
    def test_construct_from_fraction(self):
        f = Fraction(1, 2)
        ft = FractionalTime(f)

        assert isinstance(ft, FractionalTime)
        assert ft == f
        assert f == ft
        assert ft.format_numerator == 1
        assert ft.format_denominator == 2

    def test_construct_from_two_ints(self):
        f = Fraction(1, 2)
        ft = FractionalTime(2, 4)

        assert isinstance(ft, FractionalTime)
        assert ft == f
        assert f == ft
        assert ft.format_numerator == 2
        assert ft.format_denominator == 4

    def test_construct_error(self):
        with pytest.raises(ValueError):
            FractionalTime(2, Fraction(4))

    def test_from_fraction(self):
        f = Fraction(1, 2)
        ft = FractionalTime.from_fraction(f, 4)

        assert isinstance(ft, FractionalTime)
        assert ft == f
        assert ft.format_numerator == 2
        assert ft.format_denominator == 4

    def test_fractional_numerator(self):
        ft = FractionalTime(Fraction(2, 1), 2)

        assert isinstance(ft, FractionalTime)
        assert ft == Fraction(1, 1)
        assert ft.format_numerator == 2
        assert ft.format_denominator == 2

    def test_equality(self):
        # see FractionalTime docs
        assert FractionalTime(1, 2) == FractionalTime(2, 4)

    def test_bad_denominator(self):
        with pytest.raises(ValueError):
            # would be 1/4, which can't be x/2
            FractionalTime(Fraction(1, 2), 2)

        with pytest.raises(ValueError):
            FractionalTime.from_fraction(Fraction(1, 4), 2)

    def test_str(self):
        assert str(FractionalTime(2, 6)) == "2/6"
        assert str(FractionalTime(1)) == "1"
        assert str(FractionalTime(2, 2)) == "2/2"

    def test_repr(self):
        assert repr(FractionalTime(2, 6)) == "FractionalTime(2, 6)"
