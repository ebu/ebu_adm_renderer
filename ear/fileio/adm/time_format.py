from fractions import Fraction
import re


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
    minutes, seconds = divmod(time, 60)
    hours, minutes = divmod(minutes, 60)

    # XXX: conversion using float here is less than ideal, but there doesn't
    # seem to be a better (easy) way; this should be accurate enough to
    # maintain ns resolution, but should be revised
    return "{hours:02d}:{minutes:02d}:{seconds:08.5f}".format(
        hours=hours, minutes=minutes, seconds=float(seconds))
