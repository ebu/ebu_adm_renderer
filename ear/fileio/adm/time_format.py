from decimal import Decimal
from fractions import Fraction
import re
import warnings


class FractionalTime(Fraction):
    """represents an ADM fractional time as a non-normalised fraction

    This is stored as a normalised Fraction, with an extra attribute
    (_format_multiplier) used to derive the numerator and denominator when
    it is formatted as an ADM time.

    This is done to keep compatibility with existing code (which expects
    Fractions), and because Fraction can not store non-normalised fractions (or
    at least, its methods assume that the stored numerator and denominator are
    normalised).

    If the constructor is used, the given denominator is stored (and must be an
    integer), so e.g. FractionalTime(2, 4) may be formatted as ``00:00:00.2S4``,
    while Fraction would normalise this to 1/2.

    Note that two FractionalTime instances which represent the same number but
    have different denominators (e.g. 1/2 and 2/4) are considered equal, even
    though they may be formatted differently. This again is to ensure
    compatibility with code that expects Fractions.

    See :func:`parse_time` and :func:`unparse_time` for how this is used with
    ADM XML.
    """

    __slots__ = "_format_multiplier"

    def __new__(cls, numerator=0, denominator=None):
        self = super(FractionalTime, cls).__new__(cls, numerator, denominator)

        if denominator is None:
            self._format_multiplier = 1
        else:
            if not isinstance(denominator, int):
                raise ValueError("denominator must be an integer")

            self._format_multiplier, remainder = divmod(denominator, self.denominator)
            # must be able to be represented with a denominator of denominator
            if remainder != 0:
                raise ValueError(
                    "FractionalTime must be a fraction with the given denominator"
                )

        return self

    @property
    def format_numerator(self) -> int:
        """numerator of the non-normalised fraction this represents"""
        return self.numerator * self._format_multiplier

    @property
    def format_denominator(self) -> int:
        """denominator of the non-normalised fraction this represents"""
        return self.denominator * self._format_multiplier

    @classmethod
    def from_fraction(
        cls, fraction: Fraction, format_denominator: int
    ) -> "FractionalTime":
        """construct with a value equal to an existing fraction, but use the
        given denominator when formatting"""
        return cls(fraction * format_denominator, format_denominator)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.format_numerator}, {self.format_denominator})"

    def __str__(self):
        if self.format_denominator == 1:
            return str(self.format_numerator)
        else:
            return f"{self.format_numerator}/{self.format_denominator}"


_TIME_RE = re.compile(
    r"""
    (?P<hour>\d{1,2})         # one or two hour digits
    :                         # :
    (?P<minute>\d{1,2})       # one or two minute digits
    :                         # :
    (?P<second>               # second decimal consisting of:
        (?P<whole_s>\d{1,2})  #   two digits
        \.                    #   a period
        (?P<num>\d+)          #   and at least one digit (decimal or numerator)
        (?:                   #   and optionally a fractional part containing:
            S                 #     S
            (?P<den>\d+)      #     and one or more digits (denominator)
        )?
    )
    \Z                        # end
""",
    re.VERBOSE,
)


def parse_time(time_string: str) -> Fraction:
    """parse an ADM-format time

    for decimal times the return value will be a Fraction in seconds. for
    fractional/sample times, the return value will be a :class:`FractionalTime`
    """
    match = _TIME_RE.match(time_string)
    if match is None:
        raise ValueError("Cannot parse time: {!r}".format(time_string))

    hour = int(match.group("hour"))
    minute = int(match.group("minute"))

    if match.group("den") is not None:  # fractional
        numerator = int(match.group("num"))
        denominator = int(match.group("den"))
        if not numerator < denominator:
            raise ValueError(
                f"in time {time_string!r}: numerator must be less than denominator"
            )
        second = int(match.group("whole_s")) + Fraction(numerator, denominator)

        time_frac = ((hour * 60) + minute) * 60 + second

        return FractionalTime.from_fraction(time_frac, denominator)
    else:  # decimal
        second = Fraction(match.group("second"))
        return ((hour * 60) + minute) * 60 + second


def parse_time_v1(time_string: str) -> Fraction:
    """parse ADM-format times, allowing only decimal times"""
    f = parse_time(time_string)
    if isinstance(f, FractionalTime):
        raise ValueError(
            f"in time {time_string!r}: fractional times are not supported before BS.2076-2"
        )
    return f


def _unparse_whole_part(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _unparse_fractional(time: Fraction) -> str:
    seconds, fraction = divmod(time, 1)

    if isinstance(time, FractionalTime):
        numerator = int(fraction * time.format_denominator)
        denominator = time.format_denominator
    else:
        numerator, denominator = fraction.numerator, fraction.denominator

    whole_part = _unparse_whole_part(int(seconds))
    return f"{whole_part}.{numerator}S{denominator}"


def _unparse_decimal(time: Decimal) -> str:
    seconds, decimal = divmod(time, 1)

    sign, digits, exponent = decimal.as_tuple()
    assert sign == 0
    if digits == (0,):
        decimal_digits = (0,)
    else:
        # calc number of zeros to add to front
        num_zeros = -exponent - len(digits)
        assert num_zeros >= 0
        decimal_digits = (0,) * num_zeros + digits
    decimal_digits_str = "".join(str(d) for d in decimal_digits)

    whole_part = _unparse_whole_part(int(seconds))
    return f"{whole_part}.{decimal_digits_str}"


def unparse_time(time: Fraction, allow_fractional=False) -> str:
    """format a time for use in an ADM document

    Parameters:
        time: time in seconds
        allow_fractional: allow use of the BS.2086-2 fractional/sample time format

    Returns:
        string like ``01:02:03.4`` (decimal format) or ``01:02:03.2S5`` (fractional format)

    if allow_fractional is true, then the fractional format is used for
    FractionalTime instances, or Fraction instances which cannot be exactly
    converted to decimal

    otherwise, decimal format is always used, and a warning is issued if it is
    not possible to convert the time exactly to decimal
    """
    if allow_fractional and isinstance(time, FractionalTime):
        return _unparse_fractional(time)
    else:
        decimal = Decimal(time.numerator) / Decimal(time.denominator)

        if decimal == time:
            return _unparse_decimal(decimal)
        else:
            if allow_fractional:
                return _unparse_fractional(time)
            else:
                warnings.warn(
                    f"loss of accuracy when converting fractional time {time} to decimal"
                )
                return _unparse_decimal(decimal)
