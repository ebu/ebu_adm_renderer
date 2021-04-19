import numpy as np
from attr import attrs, attrib


def has_shape(*shape):
    """Attrs validator that checks that a numpy array has the given shape.

    Parameters:
        *shape: shape to match against; any elements that are None are ignored
        and may be any length.

    Returns:
        function: Validation function as rquired by the attr.attrib validator
        argument.

    Example:
        >>> @attrs
        ... class Test(object):
        ...     x = attrib(validator=has_shape(None, 2))
        >>> Test(np.array([[1,2]]))
        Test(x=array([[1, 2]]))
        >>> Test(np.array([]))
        Traceback (most recent call last):
            ...
        ValueError: ("'x' must be of shape (None, 2) which array([]...
    """
    def f(inst, attr, value):
        if (len(value.shape) != len(shape) or
                any(dim_b is not None and dim_a != dim_b
                    for dim_a, dim_b in zip(value.shape, shape))):
            raise ValueError(
                "'{name}' must be of shape {shape} which {value!r} isn't."
                .format(name=attr.name, shape=shape, value=value),
                attr, shape, value,
            )
    return f


def as_array(**kwargs):
    """Make an attrs conversion function that calls np.asarray with the
    provided arguments.

    Example:
        >>> @attrs
        ... class Test(object):
        ...     x = attrib(converter=as_array(dtype=float))
        >>> Test([1])
        Test(x=array([1.]))
    """
    def f(x):
        return np.asarray(x, **kwargs)
    return f


def safe_norm_position(position):
    """
    Parameters:
        position (array of shape (3,)): Position to normalise.

    Returns:
        array of shape (3,): normalised position
    """
    norm = np.linalg.norm(position)
    if norm < 1e-10:
        return np.array([0.0, 1.0, 0.0])
    else:
        return position / norm


def interp_sorted(x, xp, yp):
    """same as np.interp, but checks that xp is sorted"""
    xp = np.array(xp)
    assert np.all(xp[:-1] <= xp[1:]), "unsorted xp values in call to interp"
    return np.interp(x, xp, yp)
