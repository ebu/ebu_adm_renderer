import pkg_resources
from ..compatibility import load_yaml
from .geom import PolarPosition
from .layout import Channel, Layout


def _dict_to_channel(d):
    position = PolarPosition(azimuth=d["position"]["az"],
                             elevation=d["position"]["el"],
                             distance=1.0)

    return Channel(
        name=d["name"],
        is_lfe=d.get("is_lfe", False),
        polar_position=position,
        polar_nominal_position=position,
        az_range=tuple(d.get("az_range", (position.azimuth, position.azimuth))),
        el_range=tuple(d.get("el_range", (position.elevation, position.elevation))),
    )


def _dict_to_layout(d):
    return Layout(
        name=d["name"],
        channels=list(map(_dict_to_channel, d["channels"])),
    )


def _load_layouts():
    fname = "data/2051_layouts.yaml"
    with pkg_resources.resource_stream(__name__, fname) as layouts_file:
        layouts_data = load_yaml(layouts_file)

        layouts = list(map(_dict_to_layout, layouts_data))

        for layout in layouts:
            errors = []
            layout.check_positions(callback=errors.append)
            assert errors == []

        layout_names = [layout.name for layout in layouts]
        layouts_dict = {layout.name: layout for layout in layouts}

        return layout_names, layouts_dict


layout_names, layouts = _load_layouts()


def get_layout(name):
    """Get data for a layout specified in BS.2051.

    Parameters:
        name (str): Full layout name, e.g. "4+5+0"

    Returns:
        Layout: object representing the layout; real speaker positions are set
        to the nominal positions.
    """
    if name not in layout_names:
        raise KeyError("Unknown layout name '{name}'.".format(name=name))

    return layouts[name]
