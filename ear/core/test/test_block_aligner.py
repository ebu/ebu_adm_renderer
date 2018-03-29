import pytest
import numpy as np
import numpy.testing as npt
from ..block_aligner import BlockAligner


@pytest.mark.parametrize("delays", [
    [0],
    [0, 1],
    [0, 1, 10],
    [0, 1, 13],
])
def test_BlockAligner(delays):
    """Test BlockAligner with one input stream with the given delay for each block in delays"""
    nch = 5
    bs = 10
    ns = 105

    ba = BlockAligner(nch)

    all_samples = np.random.rand(len(delays), ns, nch)
    max_delay = max(delays)

    def delayed_blocks(samples, delay):
        """Delayed sample blocks taken from samples, simulating a process fed
        from a fixed length file with some inherent delay, with a trailing
        max_delay sample block.
        """
        samples_delay = np.concatenate((np.zeros((delay, nch)),
                                        samples,
                                        np.zeros((max_delay, nch)),
                                        ))
        for start in range(0, ns, bs):
            end = min(start + bs, ns)
            yield samples_delay[start:end]

        yield samples_delay[end: end + max_delay]

    # start time of the next block for each input
    starts = [-delay for delay in delays]

    out_blocks = []
    for blocks in zip(*[delayed_blocks(samples, delay) for samples, delay in zip(all_samples, delays)]):
        for i, block in enumerate(blocks):
            ba.add(starts[i], block)
            starts[i] += len(block)
        out_blocks.append(ba.get())

    out_samples = np.concatenate(out_blocks)
    npt.assert_allclose(out_samples, np.sum(all_samples, axis=0))
