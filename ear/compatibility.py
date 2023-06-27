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
    API changes in the yaml library
    """
    import yaml

    return yaml.load(stream, Loader=yaml.Loader)


def dump_yaml_str(yaml_obj):
    """stringify some yaml"""
    import yaml

    return yaml.dump(yaml_obj)


def test_yaml():
    from io import StringIO

    obj = {"some": "yaml"}

    yaml_str = dump_yaml_str(obj)

    f = StringIO(yaml_str)
    parsed_obj = load_yaml(f)

    assert parsed_obj == obj
