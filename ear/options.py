from attr import attrs, attrib
from functools import wraps
import warnings


@attrs
class Option(object):
    """Objects representing a single defaulted option to be passed to a
    function.

    Parameters:
        default (any type): default value for this option
        description (string): description for this option
    """
    default = attrib()
    description = attrib()

    def _get_default_yaml(self):
        return self.default


@attrs
class SubOptions(object):
    """Objects representing a group of options that will be delegated to some
    other function.

    Parameters:
        handler (OptionsHandler): options supported by the function that this
            option will be delegated to
        description (string): description for this option
    """
    handler = attrib()
    description = attrib()

    @property
    def default(self):
        return {}

    def _get_default_yaml(self):
        return self.handler._get_defaults_yaml()


class OptionsHandler(object):
    """Objects that represent a set of defaulted options that can be passed to
    a function.

    Parameters:
        **options: keys represent option names; values may be either Option or
            SubOptions instances
    """
    def __init__(self, **options):
        self.options = options

    def set_defaults(self, options):
        """add default values to options

        Parameters:
            options (dict): dictionary that defaults are to be added to
        """
        for key, option in self.options.items():
            if key not in options:
                options[key] = option.default

    def with_defaults(self, f):
        """Decorate f, such that the default options are added to the keyword arguments."""
        @wraps(f)
        def wrapper(*args, **kwargs):
            self.set_defaults(kwargs)
            return f(*args, **kwargs)
        return wrapper

    def _get_defaults_yaml(self):
        return {key: option._get_default_yaml() for (key, option) in self.options.items()}


def _merge_options_into_defaults(options, defaults):
    for key, option in options.items():
        if key in defaults:
            if isinstance(defaults[key], dict):
                _merge_options_into_defaults(option, defaults[key])
            else:
                defaults[key] = option
        else:
            warnings.warn("removing unknown option {}".format(key))


def dump_config(root_handler, options={}):
    """Dump a configuration to a yaml-formatted string, including the default
    options, and optionally user-set options

    Parameters:
        root_handler (OptionsHandler): handler to get defaults and descriptions from
        options (dict): user-provided options that override the defaults in root_handler
    """
    from .compatibility import dump_yaml_str

    defaults = root_handler._get_defaults_yaml()

    _merge_options_into_defaults(options, defaults)

    return dump_yaml_str(defaults)


def dump_config_with_comments(root_handler, options={}, indent=4):
    """for compatibility -- doesn't add comments or obey indent"""
    return dump_config(root_handler, options)


def test_merge():
    options_a = OptionsHandler(
        foo=Option(5, "foo"),
        bar=Option(6, "bar"),
    )
    options_b = OptionsHandler(
        a_opts=SubOptions(options_a, "options for a"),
        baz=Option(4, "baz"),
    )

    options = dict(
        a_opts=dict(
            foo=8)
    )

    defaults = options_b._get_defaults_yaml()
    _merge_options_into_defaults(options, defaults)
    assert defaults["a_opts"]["foo"] == 8
    assert defaults["a_opts"]["bar"] == 6
    assert defaults["baz"] == 4


def test_dump_renderer_options():
    from .core.renderer import Renderer

    assert isinstance(dump_config(Renderer.options), str)
