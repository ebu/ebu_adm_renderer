import numpy as np
import numpy.testing as npt
import pytest
from ..convolver import OverlapSaveConvolver, VariableBlockSizeAdapter


@pytest.mark.parametrize("nchannels", [1, 3])
def test_convolve(nchannels):
    bs = 512
    nchannels = 3
    f = np.random.rand(1500, nchannels)
    in_blocks = [np.random.rand(bs, nchannels) for i in range(100)]

    c = OverlapSaveConvolver(bs, nchannels, f)
    out_blocks = [c.filter_block(block) for block in in_blocks]

    in_all = np.concatenate(in_blocks)
    out_all = np.concatenate(out_blocks)

    out_all_expected = np.stack([np.convolve(in_chan, f_chan, mode="full")[:len(out_all)]
                                 for in_chan, f_chan in zip(in_all.T, f.T)],
                                axis=1)

    npt.assert_allclose(out_all_expected, out_all)


def test_variable_block_size():
    block_size = 100
    nchannels = 3

    def process(samples):
        assert samples.shape == (block_size, nchannels)
        return samples.copy()

    adapter = VariableBlockSizeAdapter(block_size, nchannels, process)

    assert adapter.delay(5) == block_size + 5

    input_blocks = []
    output_blocks = []
    for input_size in list(range(300)) + list(range(10)):
        input_block = np.random.rand(input_size, nchannels)
        output_block = adapter.process(input_block)
        assert output_block.shape == input_block.shape

        input_blocks.append(input_block)
        output_blocks.append(output_block)

    all_input = np.concatenate(input_blocks)
    all_output = np.concatenate(output_blocks)

    expected_output = np.concatenate((np.zeros((block_size, nchannels)), all_input[:len(all_input) - block_size]))

    npt.assert_allclose(expected_output, all_output)
