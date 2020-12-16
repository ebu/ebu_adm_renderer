from collections import namedtuple
from fractions import Fraction
import numpy as np
import numpy.testing as npt
import pytest
from ..renderer_common import BlockProcessingChannel, FixedGains, InterpGains
from ..metadata_input import MetadataSourceIter


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


@pytest.mark.parametrize("block_size", [5, 6, 10, 20, 60])
def test_block_processing_channel(block_size):
    # BlockProcessingChannel transforms metadata blocks into processing blocks;
    # use a fake metadata block type which just holds the processing block.
    DummyBlock = namedtuple("DummyBlock", "block")

    # Check gap at start, between blocks, and at end. Try both FixedGains and
    # InterpGains, since the behaviour with bad sample ranges may be different.
    # The actual interpolation behaviour of these is tested above.
    blocks = [
        DummyBlock(
            FixedGains(
                start_sample=Fraction(10),
                end_sample=Fraction(20),
                gains=np.array([0.1]),
            )
        ),
        DummyBlock(
            FixedGains(
                start_sample=Fraction(20),
                end_sample=Fraction(30),
                gains=np.array([0.2]),
            )
        ),
        DummyBlock(
            InterpGains(
                start_sample=Fraction(40),
                end_sample=Fraction(50),
                gains_start=np.array([0.3]),
                gains_end=np.array([0.3]),
            )
        ),
    ]
    expected_gains = np.repeat([0.0, 0.1, 0.2, 0.0, 0.3, 0.0], 10)
    n_samples = 60
    fs = 48000

    num_interpret_calls = 0

    def interpret(block_fs, block):
        nonlocal num_interpret_calls
        num_interpret_calls += 1

        assert block_fs == fs

        return [block.block]

    channel = BlockProcessingChannel(MetadataSourceIter(blocks), interpret)

    input_samples = 1.0 + np.random.random_sample(n_samples)
    expected_output = (expected_gains * input_samples)[:, np.newaxis]

    output_samples = np.zeros((n_samples, 1))
    for start in range(0, n_samples, block_size):
        end = start + block_size
        channel.process(fs, start, input_samples[start:end], output_samples[start:end])

    assert num_interpret_calls == 3
    npt.assert_allclose(output_samples, expected_output)
