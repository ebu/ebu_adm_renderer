import numpy as np
from ..common import CartesianPosition, PolarPosition, cart, azimuth, elevation, distance  # noqa: F401


def relative_angle(x, y):
    """Assuming y is clockwise from x, increment y by 360 until it's not less
    than x.

    Parameters:
        x (float): start angle in degrees.
        y (float): end angle in degrees.

    Returns:
        float: y shifted such that it represents the same angle but is greater
        than x.
    """
    while y - 360.0 >= x:
        y -= 360.0
    while y < x:
        y += 360.0
    return y


def inside_angle_range(x, start, end, tol=0.0):
    """Assuming end is clockwise from start, is the angle x inside [start,end]
    within some tolerance?

    Parameters:
        x (float): angle to test, in degrees
        start (float): start angle of range, in degrees
        end (float): end angle of range, in degrees
        tol (float): tolerance in degrees to check within

    Returns:
        bool
    """
    # end is clockwise from start; if end is start + 360, this rotation is
    # preserved; this makes sure that a range of (-180, 180) or (0, 360) means
    # any angle, while (-180, -180) or (0, 0) means a single angle, even though
    # -180/180 and 0/360 are nominally the same angle
    while end - 360.0 > start:
        end -= 360.0
    while end < start:
        end += 360.0

    # assume that x is clockwise from start - tol; if x is exactly
    # start-tol+360, this is resolved to start-tol, so that the comparison with
    # start-tol is >= rather than >
    start_tol = start - tol
    while x - 360.0 >= start_tol:
        x -= 360.0
    while x < start_tol:
        x += 360.0

    # x is greater than equal to start-tol, so we only need to compare against
    # the end.
    return x <= end + tol


def ngon_vertex_order(vertices):
    """Order the vertices of a convex, approximately planar polygon.

    Parameters:
        vertices (np.array of shape (n, 3)): Vertices to order

    Returns:
        integer np.array of shape (n,): Index into vertices, such that
        vertices[ret] puts vertices into the right order; this behaviour is
        similar to np.argsort.

    Examples:
        >>> ngon_vertex_order(np.array([[-1, 1, 0], [1.1, 1, 0],
        ...                             [-1, 1, 1], [1, 1, 1]]))
        array([1, 3, 2, 0])
    """
    centre = np.mean(vertices, axis=0)

    # Pick two vertices to form a plane (with the third point being the
    # origin); the vertices are ordered by the angles of points projected onto
    # this plane. The first is picked arbitrarily, the second is picked to
    # minimise the colinearity with the first.
    a = vertices[0] - centre
    b = min(vertices[1:] - centre, key=lambda vertex: np.abs(np.dot(vertex, a)))
    # These vectors are neither normalised or orthogonal, so the projection
    # onto them produces a linear transformation from the projection onto the
    # plane (relative to the origin); this is fine, as affine transformations
    # preserve straight lines.

    # find the angle of the projection of each vertex onto the plane
    vertices_rel_centre = vertices - centre[np.newaxis]
    vertex_angles = np.arctan2(np.dot(vertices_rel_centre, a),
                               np.dot(vertices_rel_centre, b))

    return np.argsort(vertex_angles)


def local_coordinate_system(az, el):
    """Vectors pointing along x, y and z, rotated so that +y points at cart(az, el, 1).

    Parameters:
        az (float): ADM format azimuth
        el (float): ADM format elevation

    Returns:
        ndarray of shape (3, 3)
    """
    return cart([az - 90.0, az, az],
                [0.0, el, el + 90.0],
                1.0)
