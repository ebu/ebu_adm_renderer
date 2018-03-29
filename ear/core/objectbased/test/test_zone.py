import itertools
import numpy as np
import numpy.testing as npt

from ..zone import ZoneExclusionDownmix
from ... import bs2051


def exclusions_to_try(layout):
    nchannels = len(layout.channels)
    if nchannels <= 10:
        for excluded in itertools.product([0, 1], repeat=nchannels):
            excluded = np.array(excluded, dtype=bool)
            yield excluded
    else:
        yield np.zeros(nchannels, dtype=bool)
        yield np.ones(nchannels, dtype=bool)

        for i in range(nchannels):
            excluded = np.ones(nchannels, dtype=bool)
            excluded[i] = False
            yield excluded

        for excluded in np.random.randint(2, size=(1000, nchannels), dtype=bool):
            yield excluded


def test_zone_excl(any_layout):
    zep = ZoneExclusionDownmix(any_layout)

    for excluded in exclusions_to_try(any_layout):
        downmix = zep.downmix_for_excluded(excluded)

        # does not downmix to excluded channels
        if not np.all(excluded):
            excluded_cols = downmix[:, excluded]
            assert np.all(excluded_cols == 0)

        # all channels are rendered somewhere
        npt.assert_allclose(np.sum(downmix, axis=1), 1.0)


def check(layout, zep, from_channel, to_channels):
    idx_norm = layout.channel_names.index

    def idx_sym(name):
        return idx_norm(name) if name.endswith(("000", "180")) else idx_norm(name.replace("-", "+")
                                                                             if "-" in name
                                                                             else name.replace("+", "-"))

    for idx in idx_sym, idx_norm:
        groups = zep.channel_groups[idx(from_channel)]
        groups_set = [set(group) for group in groups]

        to_channels_idx = [{idx(channel) for channel in group} for group in to_channels]

        assert groups_set == to_channels_idx


def test_450():
    layout = bs2051.get_layout("4+5+0").without_lfe
    zep = ZoneExclusionDownmix(layout)

    check(layout, zep, "M+000", [
        ["M+000"],
        ["M+030", "M-030"],
        ["M+110", "M-110"],
        ["U+030", "U-030"],
        ["U+110", "U-110"],
    ])

    check(layout, zep, "M-030", [
        ["M-030"],
        ["M+000"],
        ["M+030"],
        ["M-110"],
        ["M+110"],
        ["U-030"],
        ["U+030"],
        ["U-110"],
        ["U+110"],
    ])

    check(layout, zep, "M-110", [
        ["M-110"],
        ["M+110"],
        ["M-030"],
        ["M+000"],
        ["M+030"],
        ["U-110"],
        ["U+110"],
        ["U-030"],
        ["U+030"],
    ])

    check(layout, zep, "M-110", [
        ["M-110"],
        ["M+110"],
        ["M-030"],
        ["M+000"],
        ["M+030"],
        ["U-110"],
        ["U+110"],
        ["U-030"],
        ["U+030"],
    ])

    check(layout, zep, "U-030", [
        ["U-030"],
        ["U+030"],
        ["U-110"],
        ["U+110"],
        ["M-030"],
        ["M+000"],
        ["M+030"],
        ["M-110"],
        ["M+110"],
    ])

    check(layout, zep, "U-110", [
        ["U-110"],
        ["U+110"],
        ["U-030"],
        ["U+030"],
        ["M-110"],
        ["M+110"],
        ["M-030"],
        ["M+000"],
        ["M+030"],
    ])


def test_9103():
    layout = bs2051.get_layout("9+10+3").without_lfe
    zep = ZoneExclusionDownmix(layout)

    # just check upper/lower behaviour -- all speakers should take precedence
    # over lower
    check(layout, zep, "M+000", [
        ['M+000'],
        ['M+030', 'M-030'],
        ['M+060', 'M-060'],
        ['M+090', 'M-090'],
        ['M+135', 'M-135'],
        ['M+180'],
        ['U+000'],
        ['U+045', 'U-045'],
        ['U+090', 'U-090'],
        ['U+135', 'U-135'],
        ['U+180'],
        ['T+000'],
        ['B+000'],
        ['B+045', 'B-045'],
    ])
