import sys
from six import PY2


def write_bytes_to_stdout(b):
    """Write bytes (python 3) or string (python 2) to stdout."""
    if PY2:
        return sys.stdout.write(b)
    else:
        return sys.stdout.buffer.write(b)
