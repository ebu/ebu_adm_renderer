def load_config(args):
    from ruamel import yaml
    if args.config is not None:
        return yaml.safe_load(args.config)
    else:
        return {}


def dump_config_command(args, config):
    from ..core import Renderer
    from .. import options
    import sys
    config_str = options.dump_config_with_comments(Renderer.options, options=config)

    if args.output is None or args.output == "-":
        sys.stdout.write(config_str)
    else:
        with open(args.output, "w") as f:
            f.write(config_str)
