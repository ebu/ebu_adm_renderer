from decimal import Decimal
from fractions import Fraction
import re
import warnings


_TIME_RE = re.compile(r"""
    (?P<hour>\d{1,2})    # one or two hour digits
    :                    # :
    (?P<minute>\d{1,2})  # one or two minute digits
    :                    # :
    (?P<second>          # second decimal consisting of:
        \d{1,2}          #   two digits
        (?:              #   then optionally
            \.           #     a dot
            \d*          #     and any number of digits
        )
    )
    \Z                   # end
""", re.VERBOSE)


def parse_time(time_string):
    match = _TIME_RE.match(time_string)
    if match is None:
        raise ValueError("Cannot parse time: {!r}".format(time_string))

    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    second = Fraction(match.group("second"))

    return ((hour * 60) + minute) * 60 + second


def unparse_time(time):
    seconds, fraction = divmod(time, 1)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    decimal = Decimal(fraction.numerator) / Decimal(fraction.denominator)
    if decimal != fraction:
        warnings.warn(
            "loss of accuracy when converting fractional time {time} to decimal".format(
                time=time,
            )
        )

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

    return "{hours:02d}:{minutes:02d}:{seconds:02d}.{decimal}".format(
        hours=hours, minutes=minutes, seconds=seconds, decimal=decimal_digits_str,
    )
