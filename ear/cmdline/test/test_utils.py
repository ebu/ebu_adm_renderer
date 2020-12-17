import numpy as np
import pytest
import subprocess
import sys
from ...test.test_integrate import bwf_file


def test_dump_axml(tmpdir):
    filename = str(tmpdir / 'test_axml.wav')

    axml = b"AXML"

    from ...fileio import openBw64
    with openBw64(filename, 'w', axml=axml) as outfile:
        outfile.write(np.zeros((1000, 1)))

    assert subprocess.check_output(["ear-utils", "dump_axml", filename]) == axml


def test_dump_chna(tmpdir):
    filename = str(tmpdir / 'test_chna.wav')

    from ...fileio import openBw64
    from ...fileio.bw64.chunks import ChnaChunk, AudioID

    chna = ChnaChunk()
    audioID = AudioID(1, u'ATU_00000001', u'AT_00010001_01', u'AP_00010003')
    chna.appendAudioID(audioID)

    with openBw64(filename, 'w', chna=chna) as outfile:
        outfile.write(np.zeros((1000, 1)))

    expected = str(audioID) + "\n"
    output = subprocess.check_output(["ear-utils", "dump_chna", filename]).decode("utf8")
    assert output == expected

    expected = chna.asByteArray()[8:]  # strip marker and size
    output = subprocess.check_output(["ear-utils", "dump_chna", "--binary", filename])
    assert output == expected


def test_replace_axml_basic(tmpdir):
    filename_in = str(tmpdir / 'test_replace_axml_in.wav')
    filename_axml = str(tmpdir / 'test_replace_axml_new_axml.xml')
    filename_out = str(tmpdir / 'test_replace_axml_out.wav')

    from ...fileio import openBw64

    axml_in = b'axml'
    axml_out = b'axml2'

    with open(filename_axml, 'wb') as f:
        f.write(axml_out)

    with openBw64(filename_in, 'w', axml=axml_in) as outfile:
        outfile.write(np.zeros((1000, 1)))

    assert subprocess.check_call(["ear-utils", "replace_axml", "-a", filename_axml,
                                  filename_in, filename_out]) == 0

    with openBw64(filename_out, 'r') as infile:
        assert infile.axml == axml_out


def test_replace_axml_regenerate(tmpdir):
    filename_axml = str(tmpdir / 'test_replace_axml_new_axml.xml')
    filename_out = str(tmpdir / 'test_replace_axml_out.wav')

    from ...fileio import openBw64
    with openBw64(bwf_file, 'r') as f:
        axml_a = f.axml
        assert f.chna.audioIDs[-1].trackIndex == 4

    axml_out = axml_a.replace(b"ATU_00000005", b"ATU_00000006")

    with open(filename_axml, 'wb') as f:
        f.write(axml_out)

    assert subprocess.check_call(["ear-utils", "replace_axml", "-a", filename_axml, "--gen-chna",
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
        "regenerate",
        "--enable-block-duration-fix",
        bwf_file,
        bwf_out,
    ]
    assert subprocess.check_call(args) == 0

    assert open(bwf_out, "rb").read() == open(bwf_file, "rb").read()
