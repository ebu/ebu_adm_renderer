import numpy as np
import pytest
from ...fileio.adm.elements import AudioChannelFormat, MatrixCoefficient, TypeDefinition
from ..metadata_input import SilentTrackSpec, DirectTrackSpec, MatrixCoefficientTrackSpec, MixTrackSpec
from ..track_processor import TrackProcessor, MultiTrackProcessor


def test_silent():
    input_samples = np.random.random((100, 10))

    p = TrackProcessor(SilentTrackSpec())

    assert np.all(p.process(48000, input_samples) == np.zeros(100))


def test_direct():
    input_samples = np.random.random((100, 10))

    p = TrackProcessor(DirectTrackSpec(1))

    assert np.all(p.process(48000, input_samples) == input_samples[:, 1])


def test_mix():
    input_samples = np.random.random((100, 10))

    p = TrackProcessor(MixTrackSpec([DirectTrackSpec(0), DirectTrackSpec(1)]))

    assert np.all(p.process(48000, input_samples) == np.sum(input_samples[:, [0, 1]], axis=1))


@pytest.mark.parametrize("gain,expected_gain",
                         [(None, 1.0),
                          (0.5, 0.5),
                          ])
def test_matrix_coeff(gain, expected_gain):
    input_samples = np.random.random((100, 10))

    input_cf = AudioChannelFormat(audioChannelFormatName="acf", type=TypeDefinition.DirectSpeakers)
    coeff = MatrixCoefficient(inputChannelFormat=input_cf, gain=gain)

    p = TrackProcessor(MatrixCoefficientTrackSpec(DirectTrackSpec(0), coeff))

    assert np.all(p.process(48000, input_samples) == input_samples[:, 0] * expected_gain)


@pytest.mark.parametrize("sample_rate,delay,expected_delay",
                         [
                             # normal cases
                             (48000, None, 0),
                             (48000, 0.0, 0),
                             (48000, 0.5, 24),
                             # check that rounding is towards 0
                             (1000, 0.5, 0),
                             (1000, 1.5, 1),
                         ])
def test_matrix_coeff_delay(sample_rate, delay, expected_delay):
    input_samples = np.random.random((100, 10))

    input_cf = AudioChannelFormat(audioChannelFormatName="acf", type=TypeDefinition.DirectSpeakers)
    coeff = MatrixCoefficient(inputChannelFormat=input_cf, delay=delay)

    p = TrackProcessor(MatrixCoefficientTrackSpec(DirectTrackSpec(0), coeff))

    expected = np.zeros(len(input_samples))
    expected[expected_delay:] = input_samples[:len(input_samples) - expected_delay, 0]

    processed = np.concatenate((p.process(sample_rate, input_samples[:50]),
                                p.process(sample_rate, input_samples[50:])))

    assert np.all(processed == expected)


def test_simplify_sum_silence():
    input_samples = np.random.random((100, 10))

    p = TrackProcessor(MixTrackSpec([SilentTrackSpec()]))

    assert np.all(p.process(48000, input_samples) == np.zeros(100))


def test_simplify_sum_one():
    input_samples = np.random.random((100, 10))

    p = TrackProcessor(MixTrackSpec([DirectTrackSpec(0), SilentTrackSpec()]))

    assert np.all(p.process(48000, input_samples) == input_samples[:, 0])


def test_simplify_matrix():
    input_samples = np.random.random((100, 10))

    input_cf = AudioChannelFormat(audioChannelFormatName="acf", type=TypeDefinition.DirectSpeakers)
    coeff = MatrixCoefficient(inputChannelFormat=input_cf, gain=0.5)

    p = TrackProcessor(MatrixCoefficientTrackSpec(SilentTrackSpec(), coeff))

    assert np.all(p.process(48000, input_samples) == np.zeros(100))


def test_multi_track_spec_processor():
    input_samples = np.random.random((100, 10))

    p = MultiTrackProcessor([DirectTrackSpec(0), DirectTrackSpec(1)])

    assert np.all(p.process(48000, input_samples) == input_samples[:, [0, 1]])
