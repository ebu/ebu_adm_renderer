def write_bytes_to_stdout(b):
    """Write bytes (python 3) or string (python 2) to stdout."""
    from six import PY2
    import sys

    if PY2:
        return sys.stdout.write(b)
    else:
        return sys.stdout.buffer.write(b)


def load_yaml(stream):
    """load yaml from a file-like object; used to make it easier to cater to
    API changes in ruamel.yaml
    """
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe", pure=True)
    return yaml.load(stream)


def dump_yaml_str(yaml_obj):
    """stringify some yaml"""
    from ruamel.yaml import YAML
    from six import StringIO

    yaml = YAML(typ="safe", pure=True)
    f = StringIO()
    yaml.dump(yaml_obj, f)
    return f.getvalue()
