from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import pytest
import os
from ... import openBw64, openBw64Adm
from ....test.test_integrate import bwf_file

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'test_wav_files',
)


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'rect_16bit.wav'),
)
def test_rect_16bit(datafiles):
    rect_16bit_path = os.path.join(str(datafiles), 'rect_16bit.wav')
    with openBw64(rect_16bit_path) as infile:
        assert infile.sampleRate == 44100
        assert infile.channels == 2
        assert infile.bitdepth == 16
        assert infile.formatInfo.sampleRate == 44100
        assert infile.formatInfo.channelCount == 2
        assert infile.formatInfo.bitsPerSample == 16
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext is None


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'rect_24bit.wav'),
)
def test_read_seek_tell(datafiles):
    rect_24bit_path = os.path.join(str(datafiles), 'rect_24bit.wav')
    with openBw64(rect_24bit_path) as infile:
        assert infile.read(10).size == 20
        assert infile.read(0).size == 0
        assert infile.tell() == 10
        infile.seek(20)
        assert infile.tell() == 20
        infile.seek(-100)
        assert infile.tell() == 0
        infile.seek(0, 2)
        assert infile.read(100).size == 0
        with pytest.raises(ValueError) as excinfo:
            infile.seek(0, 10)
        assert str(excinfo.value) == 'whence value 10 unsupported'


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'rect_32bit.wav'),
)
def test_rect_32bit(datafiles):
    rect_32bit_path = os.path.join(str(datafiles), 'rect_32bit.wav')
    with openBw64(rect_32bit_path) as infile:
        assert infile.sampleRate == 44100
        assert infile.channels == 2
        assert infile.bitdepth == 32
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext is None


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'rect_24bit_bext.wav'),
)
def test_rect_24bit_bext(datafiles):
    rect_24bit_bext_path = os.path.join(
        str(datafiles), 'rect_24bit_bext.wav')
    with openBw64(rect_24bit_bext_path) as infile:
        assert infile.sampleRate == 44100
        assert infile.channels == 2
        assert infile.bitdepth == 24
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext is not None


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'rect_24bit_rf64.wav'),
)
def test_rect_24bit_rf64(datafiles):
    rect_24bit_rf64_path = os.path.join(
        str(datafiles), 'rect_24bit_rf64.wav')
    with openBw64(rect_24bit_rf64_path) as infile:
        assert infile.sampleRate == 44100
        assert infile.channels == 2
        assert infile.bitdepth == 24
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext is None


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'empty_extradata.wav'),
)
def test_empty_extradata(datafiles):
    wav = os.path.join(str(datafiles), 'empty_extradata.wav')
    with openBw64(wav) as infile:
        assert infile.sampleRate == 48000
        assert infile.channels == 1
        assert infile.bitdepth == 16
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext is None


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'pcm_extradata.wav'),
)
def test_pcm_extradata(datafiles):
    wav = os.path.join(str(datafiles), 'pcm_extradata.wav')
    with openBw64(wav) as infile:
        assert infile.sampleRate == 48000
        assert infile.channels == 1
        assert infile.bitdepth == 16
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext is None


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'fmt_padding.wav'),
)
def test_fmt_padding(datafiles):
    wav = os.path.join(str(datafiles), 'fmt_padding.wav')
    with openBw64(wav) as infile:
        assert infile.sampleRate == 48000
        assert infile.channels == 1
        assert infile.bitdepth == 16
        assert infile.chna is None
        assert infile.axml is None
        assert infile.bext is None


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'rect_24bit_noriff.wav'),
)
def test_rect_24bit_noriff(datafiles):
    rect_24bit_noriff_path = os.path.join(
        str(datafiles), 'rect_24bit_noriff.wav')

    with pytest.raises(RuntimeError) as excinfo:
        with openBw64(rect_24bit_noriff_path):
            pass
    assert str(excinfo.value) == 'not a riff, rf64 or bw64 file'


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'rect_24bit_nowave.wav'),
)
def test_rect_24bit_nowave(datafiles):
    rect_24bit_nowave_path = os.path.join(
        str(datafiles), 'rect_24bit_nowave.wav')

    with pytest.raises(RuntimeError) as excinfo:
        with openBw64(rect_24bit_nowave_path):
            pass
    assert str(excinfo.value) == 'not a wave file'


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'rect_24bit_nods64.wav'),
)
def test_rect_24bit_nods64(datafiles):
    rect_24bit_nods64_path = os.path.join(
        str(datafiles), 'rect_24bit_nods64.wav')

    with pytest.raises(RuntimeError) as excinfo:
        with openBw64(rect_24bit_nods64_path):
            pass
    assert str(excinfo.value) == 'malformed rf64 or bw64 file: missing ds64 chunk'


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'rect_24bit_wrong_fmt_size.wav'),
)
def test_rect_24bit_wrong_fmt_size(datafiles):
    rect_24bit_wrong_fmt_size_path = os.path.join(
        str(datafiles), 'rect_24bit_wrong_fmt_size.wav')

    with pytest.raises(ValueError) as excinfo:
        with openBw64(rect_24bit_wrong_fmt_size_path):
            pass
    assert str(excinfo.value) == r"found chunk header with invalid ID b'ta\xcc\x04'"


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, '24bit_missing_padding.wav'),
)
def test_24bit_missing_padding(datafiles):
    path = os.path.join(
        str(datafiles), '24bit_missing_padding.wav')

    with pytest.warns(UserWarning, match="data chunk is missing padding byte"):
        with openBw64(path):
            pass


def test_openBw64Adm():
    with openBw64Adm(bwf_file) as infile:
        assert infile.sampleRate == 48000
        assert infile.channels == 4
        assert infile.bitdepth == 24
        assert infile.formatInfo.sampleRate == 48000
        assert infile.formatInfo.channelCount == 4
        assert infile.formatInfo.bitsPerSample == 24
        assert infile.chna is not None

        assert infile.adm is not None
        assert len(infile.adm.audioProgrammes) == 1  # loaded axml
        assert infile.adm.audioTrackUIDs[0].trackIndex == 1  # loaded chna


def test_openBw64Adm_plain_wav(tmpdir):
    """check that reading a plain wav results in .adm being None"""
    fname = tmpdir / "plain_wav.wav"

    with openBw64(fname, "w"):
        pass

    with openBw64Adm(fname) as f:
        assert f.adm is None


def test_openBw64Adm_no_chna(tmpdir):
    """check that parsing a BW64 with AXML but no CHNA raises an error"""
    fname = tmpdir / "no_chna.wav"

    with openBw64(fname, "w", axml=b"axml"):
        pass

    with pytest.raises(
        ValueError,
        match="if 'axml' chunk is present, 'chna' must be too",
    ):
        with openBw64Adm(fname):
            pass
