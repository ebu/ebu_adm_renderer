from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import numpy as np
import pytest
from ..utils import interleave, deinterleave, decode_pcm_samples, encode_pcm_samples


def test_interleave():
    x = [[0], [1], [2], [3], [4], [5]]
    x_interleaved = interleave(x)
    assert (x_interleaved == np.array([0, 1, 2, 3, 4, 5])).all()
    x = [[0, 1], [2, 3], [4, 5]]
    x_interleaved = interleave(x)
    assert (x_interleaved == np.array([0, 1, 2, 3, 4, 5])).all()


def test_deinterleave():
    x = [0, 1, 2, 3, 4, 5]
    x_deinterleaved = deinterleave(x, 1)
    assert (x_deinterleaved == np.array([[0], [1], [2], [3], [4], [5]])).all()
    x_deinterleaved = deinterleave(x, 2)
    assert (x_deinterleaved == np.array([[0, 1], [2, 3], [4, 5]])).all()
    assert (x_deinterleaved[:, 0] == np.array([0, 2, 4])).all()
    assert (x_deinterleaved[:, 1] == np.array([1, 3, 5])).all()


def test_decode_pcm_samples():
    samples = [0.0, 1.0, -1.0, 0.5, -0.5]

    with pytest.raises(RuntimeError) as excinfo:
        decode_pcm_samples(b'\x00\x7f\x81', 8)
    assert str(excinfo.value) == 'unsupported bitdepth'

    encoded16bit = b'\x00\x00\xff\x7f\x01\x80\xff\x3f\x01\xc0'
    decoded16bit = decode_pcm_samples(encoded16bit, 16)
    assert np.allclose(decoded16bit, samples, atol=1e-4)
    encoded24bit = b'\x00\x00\x00\xff\xff\x7f\x01\x00\x80\xff\xff\x3f\x01\x00\xc0'
    decoded24bit = decode_pcm_samples(encoded24bit, 24)
    assert np.allclose(decoded24bit, samples, atol=1e-4)
    encoded32bit = b'\x00\x00\x00\x00\xff\xff\xff\x7f\x01\x00\x00\x80\xff\xff\xff\x3f\x01\x00\x00\xc0'
    decoded32bit = decode_pcm_samples(encoded32bit, 32)
    assert np.allclose(decoded32bit, samples, atol=1e-4)


def test_encode_pcm_samples():
    samples = [0.0, 1.0, -1.0, 0.5, -0.5]

    with pytest.raises(RuntimeError) as excinfo:
        encode_pcm_samples(samples, 8)
    assert str(excinfo.value) == 'unsupported bitdepth'

    encoded16bit = encode_pcm_samples(samples, 16)
    assert encoded16bit == b'\x00\x00\xff\x7f\x01\x80\xff\x3f\x01\xc0'
    encoded24bit = encode_pcm_samples(samples, 24)
    assert encoded24bit == b'\x00\x00\x00\xff\xff\x7f\x01\x00\x80\xff\xff\x3f\x01\x00\xc0'
    encoded32bit = encode_pcm_samples(samples, 32)
    assert encoded32bit == b'\x00\x00\x00\x00\xff\xff\xff\x7f\x01\x00\x00\x80\xff\xff\xff\x3f\x01\x00\x00\xc0'
