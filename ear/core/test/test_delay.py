import numpy as np
import numpy.testing as npt
import pytest
from ..delay import Delay


@pytest.mark.parametrize("delay", [0, 256, 511, 512, 513, 1024])
def test_delay(delay):
    nchannels = 4
    block_size = 512
    nsamples = block_size * 10

    input_samples = np.random.random((nsamples, nchannels))

    d = Delay(nchannels, delay)

    out_blocks = []
    for start in range(0, nsamples, block_size):
        out = d.process(input_samples[start:start+block_size])
        out_blocks.append(out)

    out = np.concatenate(out_blocks)

    expected_out = np.concatenate((np.zeros((delay, nchannels)), input_samples[:len(input_samples)-delay]))

    npt.assert_allclose(expected_out, out)
