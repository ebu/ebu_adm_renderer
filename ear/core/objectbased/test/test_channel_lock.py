from ..gain_calc import EgoChannelLockHandler
from ... import bs2051


def test_priority():
    """check that the channel lock priority order is sensible"""
    layout = bs2051.get_layout("9+10+3").without_lfe
    handler = EgoChannelLockHandler(layout)

    priority_order = [
        "M+000",
        "M-030",
        "M+030",
        "M-060",
        "M+060",
        "M-090",
        "M+090",
        "M-135",
        "M+135",
        "M+180",
        "B+000",
        "B-045",
        "B+045",
        "U+000",
        "U-045",
        "U+045",
        "U-090",
        "U+090",
        "U-135",
        "U+135",
        "U+180",
        "T+000",
    ]

    for i, (name, priority) in enumerate(
        zip(layout.channel_names, handler.channel_priority)
    ):
        assert priority_order.index(name) == priority
