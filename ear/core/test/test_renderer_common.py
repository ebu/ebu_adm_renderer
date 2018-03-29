from fractions import Fraction
import numpy as np
import numpy.testing as npt
from ..renderer_common import FixedGains, InterpGains


def test_FixedGains():
    g = FixedGains(
        start_sample=Fraction(0.5),
        end_sample=Fraction(10.5),
        gains=np.array([0.5]),
    )

    sample_no = np.arange(11)
    expected_gains = np.ones((11, 1)) * 0.5
    expected_gains[(sample_no <= 0) | (sample_no > 10), :] = 0.0

    input_samples = np.random.normal(size=11)
    output_samples = np.random.normal(size=(11, 1))
    expected = output_samples + input_samples[:, np.newaxis] * expected_gains

    g.process(0, input_samples, output_samples)

    npt.assert_allclose(output_samples, expected)


def test_InterpGains():
    g = InterpGains(
        start_sample=Fraction(0.5),
        end_sample=Fraction(10.5),
        gains_start=np.array([1, 0]),
        gains_end=np.array([0, 1]),
    )

    sample_no = np.arange(11)
    p = np.interp(sample_no, (0.5, 10.5), (0, 1))
    expected_gains = np.stack((1-p, p), 1)
    expected_gains[(sample_no <= 0) | (sample_no > 10), :] = 0.0

    input_samples = np.random.normal(size=11)
    output_samples = np.random.normal(size=(11, 2))
    expected = output_samples + input_samples[:, np.newaxis] * expected_gains

    g.process(0, input_samples, output_samples)

    npt.assert_allclose(output_samples, expected)
