from ..elements.version import (
    BS2076Version,
    UnknownVersion,
    parse_version,
    version_at_least,
)


def test_parse_version():
    assert parse_version("ITU-R_BS.2076-2") == BS2076Version(2)
    assert parse_version("ITU-R_BS.2076-1a") == UnknownVersion("ITU-R_BS.2076-1a")


def test_str():
    assert str(BS2076Version(2)) == "ITU-R_BS.2076-2"
    assert str(UnknownVersion("ITU-R_BS.2076-1a")) == "ITU-R_BS.2076-1a"


def test_version_at_least():
    def identity(x):
        return x

    for t1 in identity, BS2076Version:
        for t2 in identity, BS2076Version:
            assert version_at_least(t1(2), t2(2))
            assert not version_at_least(t1(1), t2(2))

    for t2 in identity, BS2076Version:
        assert not version_at_least(None, t2(2))
        assert not version_at_least(UnknownVersion("foo"), t2(2))
