from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from ... import openBw64
from ..chunks import FormatInfoChunk, ChnaChunk, AudioID
import numpy as np


def test_rect_16bit(tmpdir):
    samples = ((np.arange(100) % 100 < 50) - 0.5) * 2
    samples = samples[None, :].T
    fmtInfo = FormatInfoChunk(formatTag=1,
                              channelCount=1,
                              sampleRate=48000,
                              bitsPerSample=16)
    filename = str(tmpdir / 'test_16bit.wav')

    with openBw64(filename, 'w', formatInfo=fmtInfo) as outfile:
        assert outfile.channels == 1
        assert outfile.sampleRate == 48000
        assert outfile.bitdepth == 16
        outfile.write(samples)

    with openBw64(filename) as infile:
        assert infile.channels == 1
        assert infile.sampleRate == 48000
        assert infile.bitdepth == 16
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext is None
        assert np.allclose(infile.read(100), samples, atol=1e-04)


def test_rect_24bit(tmpdir):
    samples = ((np.arange(100) % 100 < 50) - 0.5) * 2
    samples = np.ones(100)
    samples = samples[None, :].T
    fmtInfo = FormatInfoChunk(formatTag=1,
                              channelCount=1,
                              sampleRate=48000,
                              bitsPerSample=24)

    filename = str(tmpdir / 'test_24bit.wav')

    with openBw64(filename, 'w', formatInfo=fmtInfo) as outfile:
        assert outfile.channels == 1
        assert outfile.sampleRate == 48000
        assert outfile.bitdepth == 24
        outfile.write(samples)

    with openBw64(filename) as infile:
        assert infile.channels == 1
        assert infile.sampleRate == 48000
        assert infile.bitdepth == 24
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext is None
        assert np.allclose(infile.read(100), samples, atol=1e-04)


def test_rect_32bit(tmpdir):
    samples = ((np.arange(100) % 100 < 50) - 0.5) * 2
    samples = samples[None, :].T
    fmtInfo = FormatInfoChunk(formatTag=1,
                              channelCount=1,
                              sampleRate=48000,
                              bitsPerSample=32)
    filename = str(tmpdir / 'test_32bit.wav')

    with openBw64(filename, 'w', formatInfo=fmtInfo) as outfile:
        assert outfile.channels == 1
        assert outfile.sampleRate == 48000
        assert outfile.bitdepth == 32
        outfile.write(samples)

    with openBw64(filename) as infile:
        assert infile.channels == 1
        assert infile.sampleRate == 48000
        assert infile.bitdepth == 32
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext is None
        assert np.allclose(infile.read(100), samples, atol=1e-04)


def test_force_bw64(tmpdir):
    samples = ((np.arange(100) % 100 < 50) - 0.5) * 2
    samples = samples[None, :].T
    filename = str(tmpdir / 'test_bw64.wav')

    with openBw64(filename, 'w') as outfile:
        assert outfile.channels == 1
        assert outfile.sampleRate == 48000
        assert outfile.bitdepth == 16
        outfile.write(samples)

    with openBw64(filename) as infile:
        assert infile.channels == 1
        assert infile.sampleRate == 48000
        assert infile.bitdepth == 16
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext is None
        assert np.allclose(infile.read(100), samples, atol=1e-04)


def test_axml_1(tmpdir):
    samples = ((np.arange(100) % 100 < 50) - 0.5) * 2
    samples = samples[None, :].T
    filename = str(tmpdir / 'test_axml_1.wav')

    with openBw64(filename, 'w') as outfile:
        assert outfile.channels == 1
        assert outfile.sampleRate == 48000
        assert outfile.bitdepth == 16
        outfile.axml = b"FAKEXML"
        assert outfile.axml == b"FAKEXML"
        outfile.write(samples)

    with openBw64(filename) as infile:
        assert infile.channels == 1
        assert infile.sampleRate == 48000
        assert infile.bitdepth == 16
        assert infile.chna is None
        assert infile.axml == b"FAKEXML"
        assert infile.bext is None
        assert np.allclose(infile.read(100), samples, atol=1e-04)


def test_axml_2(tmpdir):
    samples = ((np.arange(100) % 100 < 50) - 0.5) * 2
    samples = samples[None, :].T
    filename = str(tmpdir / 'test_axml_2.wav')

    with openBw64(filename, 'w', axml=b"FAKEXML") as outfile:
        assert outfile.channels == 1
        assert outfile.sampleRate == 48000
        assert outfile.bitdepth == 16
        assert outfile.axml == b"FAKEXML"
        outfile.write(samples)

    with openBw64(filename) as infile:
        assert infile.channels == 1
        assert infile.sampleRate == 48000
        assert infile.bitdepth == 16
        assert infile.chna is None
        assert infile.axml == b"FAKEXML"
        assert infile.bext is None
        assert np.allclose(infile.read(100), samples, atol=1e-04)


def test_chna_1(tmpdir):
    samples = ((np.arange(100) % 100 < 50) - 0.5) * 2
    samples = samples[None, :].T
    filename = str(tmpdir / 'test_chna_1.wav')

    chna = ChnaChunk()
    audioID = AudioID(1, 'ATU_00000001', 'AT_00010001_01', 'AP_00010003')
    chna.appendAudioID(audioID)

    with openBw64(filename, 'w') as outfile:
        assert outfile.channels == 1
        assert outfile.sampleRate == 48000
        assert outfile.bitdepth == 16
        outfile.chna = chna
        assert outfile.chna == chna
        outfile.write(samples)

    with openBw64(filename) as infile:
        assert infile.channels == 1
        assert infile.sampleRate == 48000
        assert infile.bitdepth == 16
        assert infile.chna == chna
        assert infile.axml is None
        assert infile.bext is None
        assert np.allclose(infile.read(100), samples, atol=1e-04)


def test_chna_2(tmpdir):
    samples = ((np.arange(100) % 100 < 50) - 0.5) * 2
    samples = samples[None, :].T
    filename = str(tmpdir / 'test_chna_2.wav')

    chna = ChnaChunk()
    audioID = AudioID(1, 'ATU_00000001', 'AT_00010001_01', 'AP_00010003')
    chna.appendAudioID(audioID)

    with openBw64(filename, 'w', chna=chna) as outfile:
        assert outfile.channels == 1
        assert outfile.sampleRate == 48000
        assert outfile.bitdepth == 16
        assert outfile.chna == chna
        outfile.write(samples)

    with openBw64(filename) as infile:
        assert infile.channels == 1
        assert infile.sampleRate == 48000
        assert infile.bitdepth == 16
        assert infile.chna == chna
        assert infile.axml is None
        assert infile.bext is None
        assert np.allclose(infile.read(100), samples, atol=1e-04)


def test_bext_1(tmpdir):
    samples = ((np.arange(100) % 100 < 50) - 0.5) * 2
    samples = samples[None, :].T
    filename = str(tmpdir / 'test_bext_1.wav')

    bext = b'FAKEBEXT'

    with openBw64(filename, 'w') as outfile:
        assert outfile.channels == 1
        assert outfile.sampleRate == 48000
        assert outfile.bitdepth == 16
        outfile.bext = bext
        assert outfile.bext == bext
        outfile.write(samples)

    with openBw64(filename) as infile:
        assert infile.channels == 1
        assert infile.sampleRate == 48000
        assert infile.bitdepth == 16
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext == bext
        assert np.allclose(infile.read(100), samples, atol=1e-04)


def test_bext_2(tmpdir):
    samples = ((np.arange(100) % 100 < 50) - 0.5) * 2
    samples = samples[None, :].T
    filename = str(tmpdir / 'test_bext_2.wav')

    bext = b'FAKEBEXT'

    with openBw64(filename, 'w', bext=bext) as outfile:
        assert outfile.channels == 1
        assert outfile.sampleRate == 48000
        assert outfile.bitdepth == 16
        assert outfile.bext == bext
        outfile.write(samples)

    with openBw64(filename) as infile:
        assert infile.channels == 1
        assert infile.sampleRate == 48000
        assert infile.bitdepth == 16
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext == bext
        assert np.allclose(infile.read(100), samples, atol=1e-04)
