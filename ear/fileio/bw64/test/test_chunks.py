from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import pytest
import os
from ..chunks import FormatInfoChunk, DataSize64Chunk


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'test_wav_files',
)


def test_format_info():
    with pytest.raises(ValueError) as excinfo:
        FormatInfoChunk(2)
    assert str(excinfo.value) == 'format not supported: 2'

    with pytest.raises(ValueError) as excinfo:
        FormatInfoChunk(channelCount=0)
    assert str(excinfo.value) == 'channelCount < 1'

    with pytest.raises(ValueError) as excinfo:
        FormatInfoChunk(sampleRate=0)
    assert str(excinfo.value) == 'sampleRate < 1'

    with pytest.raises(ValueError) as excinfo:
        FormatInfoChunk(bitsPerSample=8)
    assert str(excinfo.value) == 'bit depth not supported: 8'

    fmtInfo = FormatInfoChunk()
    assert fmtInfo.bytesPerSecond == 96000
    assert fmtInfo.blockAlignment == 2
    fmtInfoByteArray = (
        b'\x66\x6d\x74\x20\x10\x00\x00\x00\x01\x00\x01\x00'
        b'\x80\xbb\x00\x00\x00\x77\x01\x00\x02\x00\x10\x00')
    assert fmtInfo.asByteArray() == fmtInfoByteArray


def test_ds64():
    ds64 = DataSize64Chunk(1, 2, 3)
    ds64.addTableEntry(b'axml', 5)
    tableAsByteArray = (
        b'ds64\x28\x00\x00\x00'  # header
        b'\x01\x00\x00\x00\x00\x00\x00\x00'  # riffSize
        b'\x02\x00\x00\x00\x00\x00\x00\x00'  # dataSize
        b'\x03\x00\x00\x00\x00\x00\x00\x00'  # dummy
        b'\x01\x00\x00\x00'  # tableLength
        b'axml\x05\x00\x00\x00\x00\x00\x00\x00'  # table entry
    )
    assert ds64.asByteArray() == tableAsByteArray
