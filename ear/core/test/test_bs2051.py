import pytest
from .. import bs2051
from ..geom import PolarPosition, relative_angle


def test_get_layout_data():
    layout = bs2051.get_layout("4+5+0")

    assert layout.channel_names[:2] == ["M+030", "M-030"]

    assert len(layout.channels) == 10

    assert layout.channels[0].polar_position == PolarPosition(30, 0, 1)
    assert layout.channels[1].polar_position == PolarPosition(-30, 0, 1)


def test_layout_names():
    assert "4+5+0" in bs2051.layout_names


def test_unknown_layout():
    with pytest.raises(KeyError) as excinfo:
        data, positions = bs2051.get_layout("wat")

    assert "wat" in str(excinfo.value)


def test_all_positions_in_range():
    """Check that the speaker positions of all layouts are within range."""
    for layout in bs2051.layouts.values():
        errors = []
        layout.check_positions(callback=errors.append)
        assert errors == []


def test_azimuth_ranges():
    """Test that most ranges are reasonably small; this detects ranges that
    have been inverted. Screen speakers and LFE channels are ignored.
    """
    for layout in bs2051.layouts.values():
        for channel in layout.channels:
            if not channel.is_lfe and "SC" not in channel.name:
                az_range = channel.az_range
                range_size = relative_angle(az_range[0], az_range[1]) - az_range[0]
                assert range_size <= 180


def test_symmetry():
    for layout in bs2051.layouts.values():
        # find symmetric pairs of speakers
        symmetric_pairs = {}
        for channel in layout.channels:
            for splitchar in "+-":
                if splitchar in channel.name:
                    ident = tuple(channel.name.split(splitchar))
                    symmetric_pairs.setdefault(ident, []).append(channel)
                    break
            else:
                assert "LFE" in channel.name and channel.is_lfe

        for pair in symmetric_pairs.values():
            if len(pair) == 1:
                # any non-paired speakers should be on the centre line
                assert pair[0].polar_position.azimuth in (0, -180, 180)
            elif len(pair) == 2:
                # all pairs should be have symmetrical positions and ranges
                a, b = pair

                assert a.polar_position.elevation == b.polar_position.elevation
                assert a.polar_position.azimuth == -b.polar_position.azimuth

                assert a.el_range == b.el_range
                assert a.az_range == (-b.az_range[1], -b.az_range[0])
            else:
                assert False
