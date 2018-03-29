import numpy as np
import numpy.testing as npt
import pytest
from ..decorrelate import gen_rand_mt19937, design_decorrelator_basic, design_decorrelators
from ... import bs2051


def test_gen_rand_mt19937():
    # test data from C++11 standard
    seed = 5489
    i = 10000
    expected = 4123659995
    assert gen_rand_mt19937(seed, i)[i-1] == expected


def test_design_decorrelator():
    rand = gen_rand_mt19937(0, 1)[0] / float(2**32)
    expected = [1.0, np.exp(2j * rand * np.pi)]

    filt = design_decorrelator_basic(0)
    assert len(filt) == 512
    assert filt.dtype == float
    npt.assert_allclose(np.fft.fft(filt)[:2], expected)


@pytest.mark.parametrize("method_name, method_f", [
    ("basic", design_decorrelator_basic),
])
def test_design_decorrelators(method_name, method_f):
    layout = bs2051.get_layout("4+5+0").without_lfe
    filters = design_decorrelators(layout, method=method_name)

    # M+030 should get the second filter
    right_filter = filters[:, layout.channel_names.index("M+030")]
    npt.assert_allclose(right_filter, method_f(1))


def correlation_coefficient(a, b):
    cross_corr = np.fft.irfft(np.fft.rfft(a) * np.fft.rfft(b[::-1]))
    return cross_corr[np.argmax(np.abs(cross_corr))]


def correlation_coefficient_matrix(filters):
    @np.vectorize
    def corr_idx(a, b):
        return correlation_coefficient(filters[:, a], filters[:, b])

    A, B = np.ogrid[:filters.shape[1], :filters.shape[1]]
    return corr_idx(A, B)
