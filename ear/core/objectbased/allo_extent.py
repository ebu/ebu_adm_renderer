import numpy as np

num_vs = 40
NEG130DBEXP_LIM = 6.5
NEG130DB_LIM = 10.0 ** -NEG130DBEXP_LIM


def _scale_size(v):
    return np.interp(min(v, 1.0),
                     [0.0, 0.2, 0.5, 0.75, 1.0],  # noqa
                     [0.0, 0.3, 1.0, 1.8,  2.8])  # noqa


def _s_eff(channel_positions, sx, sy, sz):
    if np.all(channel_positions[:, [1, 2]] == channel_positions[0, [1, 2]]):
        # Speakers in a left/right line
        return sx
    elif np.all(channel_positions[:, 2] == channel_positions[0, 2]):
        # Speakers in a horizontal plane
        size_sorted = sorted([sx, sy])
        return ((3.0 / 4.0) * size_sorted[1] +
                (1.0 / 4.0) * size_sorted[0])
    else:
        # Speakers in a cube
        size_sorted = sorted([sx, sy, sz])
        return ((6.0 / 9.0) * size_sorted[2] +
                (2.0 / 9.0) * size_sorted[1] +
                (1.0 / 9.0) * size_sorted[0])


def _p(s_eff):
    if s_eff <= 0.5:
        return 6.0
    else:
        s_max = 2.8
        return 6.0 - 4.0 * ((s_eff - 0.5) / (s_max - 0.5))


def _h(c, s, d_bound):
    if d_bound >= 2.0*s and d_bound >= 0.4:
        n = max(2.0*s, 0.4)
        nnn = n*n*n
        return np.power(nnn / (0.16*2.0*s), 1.0/3.0)
    else:
        a = d_bound/0.4
        b = d_bound/2.0 * (a * a)
        return np.power(b, 1.0/3.0)


def _d_bound(dim, xo, yo, zo):
    if dim == 1:
        return min(xo + 1, 1 - xo)
    elif dim == 2:
        return min(xo + 1, 1 - xo, yo + 1, 1 - yo)
    else:
        return min(xo + 1, 1 - xo, yo + 1, 1 - yo, zo + 1, 1 - zo)


def _mu(dim, sx, sy, sz, xo, yo, zo):
    d_bound = _d_bound(dim, xo, yo, zo)

    if dim == 1:
        n = _h(xo, sx, d_bound)
        return n*n*n
    elif dim == 2:
        n = _h(xo, sx, d_bound) * _h(yo, sy, d_bound)
        return np.power(n, 1.5)
    else:
        return _h(xo, sx, d_bound) * _h(yo, sy, d_bound) * _h(zo, sz, d_bound)


def _calc_w(xo, yo, zo, sx, sy, sz, xs, ys, zs):
    xt = -np.minimum(np.power(1.5 * (xs - xo) / (2.0*sx), 4.0), np.ones(xs.shape)*NEG130DBEXP_LIM)
    wx = np.power(10, xt)

    yt = -np.minimum(np.power(1.5 * (ys - yo) / (2.0*sy), 4.0), np.ones(ys.shape)*NEG130DBEXP_LIM)
    wy = np.power(10, yt)

    zt = -np.minimum(np.power(1.5 * (zs - zo) / sz, 4.0), np.ones(zs.shape)*NEG130DBEXP_LIM)
    wz = np.power(10, zt) * np.cos(zs*np.pi*(3.0/7.0))

    return wx, wy, wz


def _dim(channel_positions):
    return np.sum(np.any(channel_positions != channel_positions[0], axis=0))


def _calc_f(p, w, g_point):
    f = np.sum(np.power(g_point * w, p), axis=1)

    f[f < NEG130DB_LIM] = 0.0

    return f


def _find_plane_z(z, channel_positions):
    z_bounds_lo = None
    z_bounds_hi = None
    for s_x, s_y, s_z in channel_positions:
        if s_z <= z:
            if z_bounds_lo is None:
                z_bounds_lo = s_z
            else:
                z_bounds_lo = max(z_bounds_lo, s_z)

        if s_z >= z:
            if z_bounds_hi is None:
                z_bounds_hi = s_z
            else:
                z_bounds_hi = min(z_bounds_hi, s_z)

    return z_bounds_lo, z_bounds_hi


def _find_row_y(y, plane_z, channel_positions):
    y_bounds_lo = None
    y_bounds_hi = None
    for s_x, s_y, s_z in channel_positions:
        if s_z == plane_z:
            if s_y <= y:
                if y_bounds_lo is None:
                    y_bounds_lo = s_y
                else:
                    y_bounds_lo = max(y_bounds_lo, s_y)

            if s_y >= y:
                if y_bounds_hi is None:
                    y_bounds_hi = s_y
                else:
                    y_bounds_hi = min(y_bounds_hi, s_y)

    return y_bounds_lo, y_bounds_hi


def _find_column_x(x, row_y, plane_z, channel_positions):
    x_bounds_lo = None
    x_bounds_hi = None
    for s_x, s_y, s_z in channel_positions:
        if s_z == plane_z and s_y == row_y:
            if s_x <= x:
                if x_bounds_lo is None:
                    x_bounds_lo = s_x
                else:
                    x_bounds_lo = max(x_bounds_lo, s_x)

            if s_x >= x:
                if x_bounds_hi is None:
                    x_bounds_hi = s_x
                else:
                    x_bounds_hi = min(x_bounds_hi, s_x)

    return x_bounds_lo, x_bounds_hi


def _calc_g_point_separated(channel_positions, xs, ys, zs):
    ret_x = []
    ret_y = []
    ret_z = []
    for pos_x, pos_y, pos_z in channel_positions:
        # Z
        gz = []
        for z in zs:
            z_bounds_lo, z_bounds_hi = _find_plane_z(z, channel_positions)
            if z_bounds_lo is None:
                if pos_z != z_bounds_hi:
                    g = 0.0
                else:
                    g = 1.0
            elif z_bounds_hi is None:
                if pos_z != z_bounds_lo:
                    g = 0.0
                else:
                    g = 1.0
            elif z_bounds_lo <= pos_z <= z_bounds_hi:
                if z_bounds_lo == z_bounds_hi:
                    g = 1.0
                elif z_bounds_lo == pos_z:
                    g = np.cos((z - z_bounds_lo) / (z_bounds_hi - z_bounds_lo) * np.pi / 2.0)
                else:
                    g = np.sin((z - z_bounds_lo) / (z_bounds_hi - z_bounds_lo) * np.pi / 2.0)
            else:
                g = 0.0
            gz.append(g)
        gz = np.array(gz)

        # Y
        gy = []
        for y in ys:
            y_bounds_lo, y_bounds_hi = _find_row_y(y, pos_z, channel_positions)
            if y_bounds_lo is None:
                if pos_y != y_bounds_hi:
                    g = 0.0
                else:
                    g = 1.0
            elif y_bounds_hi is None:
                if pos_y != y_bounds_lo:
                    g = 0.0
                else:
                    g = 1.0
            elif y_bounds_lo <= pos_y <= y_bounds_hi:
                if y_bounds_lo == y_bounds_hi:
                    g = 1.0
                elif y_bounds_lo == pos_y:
                    g = np.cos((y - y_bounds_lo) / (y_bounds_hi - y_bounds_lo) * np.pi / 2.0)
                else:
                    g = np.sin((y - y_bounds_lo) / (y_bounds_hi - y_bounds_lo) * np.pi / 2.0)
            else:
                g = 0.0
            gy.append(g)
        gy = np.array(gy)

        # X
        gx = []
        for x in xs:
            x_bounds_lo, x_bounds_hi = _find_column_x(x, pos_y, pos_z, channel_positions)
            if x_bounds_lo is None:
                if pos_x != x_bounds_hi:
                    g = 0.0
                else:
                    g = 1.0
            elif x_bounds_hi is None:
                if pos_x != x_bounds_lo:
                    g = 0.0
                else:
                    g = 1.0
            elif x_bounds_lo <= pos_x <= x_bounds_hi:
                if x_bounds_lo == x_bounds_hi:
                    g = 1.0
                elif x_bounds_lo == pos_x:
                    g = np.cos((x - x_bounds_lo) / (x_bounds_hi - x_bounds_lo) * np.pi / 2.0)
                else:
                    g = np.sin((x - x_bounds_lo) / (x_bounds_hi - x_bounds_lo) * np.pi / 2.0)
            else:
                g = 0.0
            gx.append(g)
        gx = np.array(gx)

        ret_x.append(gx)
        ret_y.append(gy)
        ret_z.append(gz)

    return np.array(ret_x), np.array(ret_y), np.array(ret_z)


def _calc_Nz(channel_positions):
    if len(set(list(channel_positions[:, 2]))) >= 3:
        return num_vs
    return num_vs // 2


def get_gains(channel_positions, position, size_x, size_y, size_z):
    xo, yo, zo = position
    Nx = num_vs
    Ny = num_vs
    Nz = _calc_Nz(channel_positions)
    xs = np.linspace(-1.0, 1.0, Nx)
    ys = np.linspace(-1.0, 1.0, Ny)
    if len(set(list(channel_positions[:, 2]))) >= 3:
        zs = np.linspace(-1.0, 1.0, Nz)
    else:
        zs = np.linspace(0.0, 1.0, Nz)
        zo = max(0.0, zo)

    sx = max(_scale_size(size_x), 2.0 / (Nx-1))
    sy = max(_scale_size(size_y), 2.0 / (Ny-1))
    sz = max(_scale_size(size_z), 2.0 / (Nz-1))
    s_eff = _s_eff(channel_positions, sx, sy, sz)
    p = _p(s_eff)
    dim = _dim(channel_positions)

    mu = _mu(dim, sx, sy, sz, xo, yo, zo)
    wx, wy, wz = _calc_w(xo, yo, zo, sx, sy, sz, xs, ys, zs)

    g_point_x, g_point_y, g_point_z = _calc_g_point_separated(channel_positions, xs, ys, zs)
    fx = _calc_f(p, wx, g_point_x)
    fy = _calc_f(p, wy, g_point_y)
    fz = _calc_f(p, wz, g_point_z)

    g_inside = fx * fy * fz

    def safe_norm(vec):
        length = np.linalg.norm(vec)
        if length > 1e-16:
            return vec / length
        else:
            return np.zeros_like(vec)

    g_inside_norm = safe_norm(g_inside)

    b_floor = np.power(g_point_z[:, 0] * wz[0], p)
    b_ceil = np.power(g_point_z[:, -1] * wz[-1], p)
    b_left = np.power(g_point_x[:, 0] * wx[0], p)
    b_right = np.power(g_point_x[:, -1] * wx[-1], p)
    b_front = np.power(g_point_y[:, 0] * wy[0], p)
    b_back = np.power(g_point_y[:, -1] * wy[-1], p)

    g_bound = (b_left * fy * fz
               + b_right * fy * fz
               + fx * b_front * fz
               + fx * b_back * fz
               + fx * fy * b_ceil
               + fx * fy * b_floor)

    g_size = np.power(g_bound + (mu * g_inside_norm), 1.0 / p)
    g_size_norm = safe_norm(g_size)

    s_fade = 0.2
    if s_eff < s_fade:
        alpha = np.cos((s_eff * np.pi) / (s_fade * 2.0))
        beta = np.sin((s_eff * np.pi) / (s_fade * 2.0))
    else:
        alpha = 0.0
        beta = 1.0

    g_point = np.array(_calc_g_point_separated(channel_positions, [xo], [yo], [zo])).prod(axis=0).flatten()
    g_total = (alpha * g_point) + (beta * g_size_norm)
    g_total_norm = safe_norm(g_total)

    return g_total_norm
