from attr import attrib, attrs
from attr.validators import instance_of, optional
from typing import Union


@attrs(slots=True, frozen=True)
class BS2076Version:
    """representation of a BS.2076 version number"""

    version = attrib(default=1, validator=instance_of(int))

    def __str__(self):
        return f"ITU-R_BS.2076-{self.version}"


@attrs(slots=True, frozen=True)
class UnknownVersion:
    """representation of a non-BS.2076 version string"""

    version = attrib(validator=instance_of(str))

    def __str__(self):
        return self.version


@attrs(slots=True, frozen=True)
class NoVersion:
    """A version could have been provided, but wasn't."""


Version = Union[BS2076Version, UnknownVersion, NoVersion, None]
"""ADM version specifier

there are 4 possible cases:

`<audioFormatExtended version="ITU-R_BS.2076-2">` -> `BS2076Version(2)`
`<audioFormatExtended version="foo">` -> `UnknownVersion("foo")`
`<audioFormatExtended>` -> `NoVersion()`
CHNA only mode (no AXML or no audioFormatExtended) -> `None`
"""


version_validator = optional(instance_of((BS2076Version, UnknownVersion, NoVersion)))


def version_at_least(a: Union[Version, int], b: Union[Version, int]) -> bool:
    """is a at least b?

    integers will be converted to BS2076Version objects; only returns true if a
    and b are both BS2076Version.
    """
    if isinstance(a, int):
        a = BS2076Version(a)
    if isinstance(b, int):
        b = BS2076Version(b)

    if isinstance(a, BS2076Version) and isinstance(b, BS2076Version):
        return a.version >= b.version
    else:
        return False


def parse_version(version: Union[str, None]) -> Version:
    import re

    if version is None:
        return NoVersion()

    bs2076_re = r"ITU-R_BS\.2076-([0-9]+)"
    match = re.fullmatch(bs2076_re, version)

    if match is not None:
        return BS2076Version(int(match.group(1)))
    else:
        return UnknownVersion(version)
