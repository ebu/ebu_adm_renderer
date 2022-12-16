from functools import partial


def _load_unweighted_cartesian(fname):
    import numpy as np
    import pkg_resources

    with pkg_resources.resource_stream(__name__, fname) as points_file:
        return np.loadtxt(points_file, skiprows=2)


_t_designs = {
    3: partial(_load_unweighted_cartesian, "data/N003_M6_Octa.dat"),
    5: partial(_load_unweighted_cartesian, "data/N005_M12_Ico.dat"),
    7: partial(_load_unweighted_cartesian, "data/N007_M24_Octa.dat"),
    9: partial(_load_unweighted_cartesian, "data/N009_M48_Octa.dat"),
    11: partial(_load_unweighted_cartesian, "data/N011_M70_C5.dat"),
    13: partial(_load_unweighted_cartesian, "data/N013_M94_Inv.dat"),
}


def get_t_design(N):
    if N in _t_designs:
        return _t_designs[N]()
    else:
        raise KeyError(f"t-design of order {N} not found")
