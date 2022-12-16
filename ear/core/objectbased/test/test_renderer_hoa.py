import numpy as np
from ...hoa_adapter import HOAFormat, HOAPointSourceAdapter
from ..renderer_hoa import OverlapSaveConvolverMatrix, design_decorrelators


def test_decorrelator_normalisation():
    """check that the decorrelation filters are correctly normalised, so that
    the output is the same for different output normalisations
    """
    fmt1 = HOAFormat(2, "N3D")
    fmt2 = HOAFormat(2, "SN3D")
    n, m = fmt1.orders_degrees

    panner1 = HOAPointSourceAdapter.build(fmt1)
    panner2 = HOAPointSourceAdapter.build(fmt2)

    conv_2_1 = fmt1.norm_fn(n, np.abs(m)) / fmt2.norm_fn(n, np.abs(m))

    dec1 = design_decorrelators(fmt1)
    dec2 = design_decorrelators(fmt2)

    out1 = np.einsum("ijk,j->ik", dec1, panner1.handle((0, 1, 0)))
    out2 = np.einsum("ijk,j->ik", dec2, panner2.handle((0, 1, 0))) * conv_2_1

    np.testing.assert_allclose(out1, out2)


def test_OverlapSaveConvolverMatrix():
    n_in, n_out = 3, 5

    filters = np.random.uniform(size=(1, n_in, n_out))
    conv = OverlapSaveConvolverMatrix(1, filters)

    samples_in = np.random.uniform(size=(1, n_in))
    samples_out = conv.filter_block(samples_in)

    np.testing.assert_allclose(samples_out[0], np.dot(samples_in[0], filters[0]))
