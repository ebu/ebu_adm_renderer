import numpy as np


def render_subwoofers(sub_positions, speaker_position):
    """Generate upmix coefficients from a loudspeaker to up to 2 subwoofers.

    Parameters:
        sub_positions (ndarray of (n, 3)): subwoofer positions
        speaker_position (ndarray of (3,)): loudspeaker position
    Returns:
        ndarray of (n,): upmix coefficient for each subwoofer.
    """
    if len(sub_positions) == 0:
        return np.array([])
    elif len(sub_positions) == 1:
        return np.array([1.0])
    elif len(sub_positions) == 2:
        a, b = sub_positions

        # projection the position onto the vector between a and b, scaled to 1 at b
        vec = b - a
        vec /= np.linalg.norm(vec) ** 2

        p_b = np.clip(np.dot(vec, speaker_position - a), 0, 1)
        p_a = 1.0 - p_b

        return np.array([p_a, p_b])
    else:
        raise AssertionError("Invalid number of subwoofers: {}".format(len(sub_positions)))


def subwoofer_upmix_matrix(layout):
    """Generate an upmix matrix that maps from channels in layout.without_lfe
    to channels in layout, using render_subwoofers to generate downmix
    coefficients for LFE channels.

    Parameters:
        layout (..layout.Layout): layout with lfe channels to upmix to

    Returns:
        ndarray: upmix matrix M, such that if g is a vector of gains for each
            channel in layout.without_lfe, M.dot(g) is a vector of gains for
            each channel in layout
    """
    layout_no_sub = layout.without_lfe

    sub_idx = [i for i, channel in enumerate(layout.channels) if channel.is_lfe]
    sub_positions = layout.positions[sub_idx]

    upmix = np.zeros((len(layout.channels), len(layout_no_sub.channels)))

    for in_idx, channel in enumerate(layout_no_sub.channels):
        out_idx = layout.channels.index(channel)
        upmix[out_idx, in_idx] = 1.0
        upmix[sub_idx, in_idx] = render_subwoofers(sub_positions, channel.position)

    return upmix


def lfe_downmix_matrix(layout):
    """Generate a downmix matrix that sums channels in layout.without_lfe into
    the lfe channels in layout.

    Parameters:
        layout (..layout.Layout): layout with lfe channels to upmix to

    Returns:
        ndarray: downmix matrix M, such that if g is a vector of gains for each
            channel in layout.without_lfe, M.dot(g) is a vector of gains for
            each channel in layout
    """
    layout_no_lfe = layout.without_lfe

    downmix = np.zeros((len(layout.channels), len(layout_no_lfe.channels)))

    lfe_positions = layout.positions[layout.is_lfe]

    for idx, channel in enumerate(layout_no_lfe.channels):
        downmix[layout.is_lfe, idx] = render_subwoofers(lfe_positions, channel.position)

    return downmix
