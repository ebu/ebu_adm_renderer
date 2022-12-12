from __future__ import division
import numpy as np


def gen_rand_mt19937(seed, n):
    # given the current numpy code, this results in raw 32 bit values from mt19937;
    # the docs guarantee forward compatibility given a fixed seed so it should
    # remain the same
    return np.random.RandomState(seed).randint(0, 2**32, n, dtype=np.uint32)


def gen_rand_float(seed, n):
    return gen_rand_mt19937(seed, n) / 2**32


def design_decorrelator_basic(decorrelator_id, size=512):
    """Design an all-pass random-phase FIR filter.

    Parameters:
        decorrelator_id (int): Random seed, to obtain different filters.
        size (int): filter length.

    Returns:
        array of (size,): Filter coefficients.
    """
    rand = gen_rand_float(decorrelator_id, size//2 - 1)

    phase = np.zeros(size // 2 + 1)
    phase[1: size // 2] = 2 * np.pi * rand

    freq = np.exp(1j * phase)

    return np.fft.irfft(freq)


design_methods = dict(
    basic=design_decorrelator_basic,
)


def design_decorrelators(layout, method="basic", **options):
    """Design one filter for each channel in layout.

    Parameters:
        layout (layout.Layout): Layout to design for; channel names are used to
            allocate filters to channels.
        **options: options for design_decorrelator

    Returns:
        array of shape (filt_len, nchannels): Decorrelation filters.
    """
    sorted_channel_names = sorted(layout.channel_names)

    design = design_methods[method]
    decorrelators = [design(sorted_channel_names.index(name), **options.get(method + "_opts", {}))
                     for name in layout.channel_names]
    return np.array(decorrelators).T
