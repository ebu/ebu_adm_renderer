import numpy as np
import pytest
import subprocess
import sys
from ...test.test_integrate import bwf_file
from ...fileio import openBw64


def test_dump_axml(tmpdir):
    filename = str(tmpdir / 'test_axml.wav')

    axml = b"AXML"

    from ...fileio import openBw64
    with openBw64(filename, 'w', axml=axml) as outfile:
        outfile.write(np.zeros((1000, 1)))

    assert subprocess.check_output(["ear-utils", "-d", "dump_axml", filename]) == axml


def test_dump_chna(tmpdir):
    filename = str(tmpdir / 'test_chna.wav')

    from ...fileio.bw64.chunks import ChnaChunk, AudioID

    chna = ChnaChunk()
    audioID = AudioID(1, u'ATU_00000001', u'AT_00010001_01', u'AP_00010003')
    chna.appendAudioID(audioID)

    with openBw64(filename, 'w', chna=chna) as outfile:
        outfile.write(np.zeros((1000, 1)))

    expected = str(audioID) + "\n"
    output = subprocess.check_output(["ear-utils", "-d", "dump_chna", filename]).decode("utf8")
    assert output == expected

    expected = chna.asByteArray()[8:]  # strip marker and size
    output = subprocess.check_output(["ear-utils", "-d", "dump_chna", "--binary", filename])
    assert output == expected


def test_replace_axml_basic(tmpdir):
    filename_in = str(tmpdir / 'test_replace_axml_in.wav')
    filename_axml = str(tmpdir / 'test_replace_axml_new_axml.xml')
    filename_out = str(tmpdir / 'test_replace_axml_out.wav')

    axml_in = b'axml'
    axml_out = b'axml2'

    with open(filename_axml, 'wb') as f:
        f.write(axml_out)

    with openBw64(filename_in, 'w', axml=axml_in) as outfile:
        outfile.write(np.zeros((1000, 1)))

    assert subprocess.check_call(["ear-utils", "-d", "replace_axml", "-a", filename_axml,
                                  filename_in, filename_out]) == 0

    with openBw64(filename_out, 'r') as infile:
        assert infile.axml == axml_out


def test_replace_axml_regenerate(tmpdir):
    filename_axml = str(tmpdir / 'test_replace_axml_new_axml.xml')
    filename_out = str(tmpdir / 'test_replace_axml_out.wav')

    with openBw64(bwf_file, 'r') as f:
        axml_a = f.axml
        assert f.chna.audioIDs[-1].trackIndex == 4

    axml_out = axml_a.replace(b"ATU_00000005", b"ATU_00000006")

    with open(filename_axml, 'wb') as f:
        f.write(axml_out)

    assert subprocess.check_call(["ear-utils", "-d", "replace_axml", "-a", filename_axml, "--gen-chna",
                                  bwf_file, filename_out]) == 0

    with openBw64(filename_out, 'r') as f:
        assert f.axml == axml_out
        assert f.chna.audioIDs[-1].trackIndex == 6


@pytest.mark.xfail(
    sys.version_info < (3, 6),
    reason="output may vary on platforms where dictionaries are not ordered",
)
def test_regenerate(tmpdir):
    bwf_out = str(tmpdir / "test_regenerate_out.wav")

    args = [
        "ear-utils",
        "-d",
        "regenerate",
        "--enable-block-duration-fix",
        bwf_file,
        bwf_out,
    ]
    assert subprocess.check_call(args) == 0

    assert open(bwf_out, "rb").read() == open(bwf_file, "rb").read()


@pytest.mark.xfail(
    sys.version_info < (3, 6),
    reason="output may vary on platforms where dictionaries are not ordered",
)
def test_regenerate_version(tmpdir):
    bwf_out = str(tmpdir / "test_regenerate_v2_out.wav")
    bwf_expected = str(tmpdir / "test_regenerate_out_expected.wav")

    with openBw64(bwf_file, "r") as f_in:
        # consider saving the whole axml if there are more changes
        axml = f_in.axml.replace(
            b"<audioFormatExtended", b'<audioFormatExtended version="ITU-R_BS.2076-2"'
        )

        with openBw64(
            bwf_expected,
            "w",
            formatInfo=f_in.formatInfo,
            axml=axml,
            chna=f_in.chna,
        ) as f_out:
            for block in f_in.iter_sample_blocks(1024):
                f_out.write(block)

    args = [
        "ear-utils",
        "-d",
        "regenerate",
        "--enable-block-duration-fix",
        "--set-version=2",
        bwf_file,
        bwf_out,
    ]
    assert subprocess.check_call(args) == 0

    assert open(bwf_out, "rb").read() == open(bwf_expected, "rb").read()


@pytest.mark.xfail(
    sys.version_info < (3, 6),
    reason="output may vary on platforms where dictionaries are not ordered",
)
def test_rewrite(tmpdir):
    bwf_out = str(tmpdir / "test_rewrite_out.wav")

    args = [
        "ear-utils",
        "-d",
        "rewrite",
        bwf_file,
        bwf_out,
    ]
    assert subprocess.check_call(args) == 0

    assert open(bwf_out, "rb").read() == open(bwf_file, "rb").read()
