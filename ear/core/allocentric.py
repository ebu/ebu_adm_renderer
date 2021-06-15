import numpy as np
from .objectbased.conversion import point_polar_to_cart
from ..compatibility import load_yaml


def _load_allo_positions():
    import pkg_resources

    fname = "data/allo_positions.yaml"
    with pkg_resources.resource_stream(__name__, fname) as layouts_file:
        return load_yaml(layouts_file)


_allo_positions = _load_allo_positions()


def _screen_spk_position_to_cart(position):
    """Get the allocentric position for a polar screen loudspeaker position.

    Parameters:
        position (PolarPosition): Polar screen loudspeaker position
    Returns:
        array of 3 floats: equivalent allocentric position
    """
    # the y position of these loudspeakers must be identical, and they must be
    # either exactly at the front or the side
    pos_left = point_polar_to_cart(np.abs(position.azimuth), 0.0, 1.0)

    at_front = np.abs(pos_left[1] - 1) < 1e-10
    at_side = np.abs(pos_left[0] + 1) < 1e-10

    assert at_front or at_side

    if at_front:
        pos_left[1] = 1.0
    if at_side:
        pos_left[0] = -1.0

    return pos_left * [np.sign(position.azimuth), 1.0, 1.0]


def positions_for_layout(layout):
    layout_positions = _allo_positions[layout.name]

    def get_position(channel):
        if channel.name in ("M+SC", "M-SC"):
            return _screen_spk_position_to_cart(channel.polar_position)
        else:
            return layout_positions[channel.name]

    return np.array([get_position(channel)
                     for channel in layout.channels])


def get_excluded(channel_positions, is_excluded):
    is_excluded = np.copy(is_excluded)

    # Remove additional speakers to ensure the layout works well with
    # our panner
    for ex, c in zip(is_excluded, channel_positions):
        if ex and abs(c[0]) == 1.0 and abs(c[1]) != 1.0:
            for k, c2 in enumerate(channel_positions):
                if c2[1] == c[1] and c2[2] == c[2]:
                    is_excluded[k] = True

    # Don't do any exclusion if the previous steps result in a layout
    # with no speakers
    if np.all(is_excluded):
        is_excluded[:] = False

    return is_excluded
