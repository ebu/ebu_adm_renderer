from attr import attrs, attrib, Factory
from attr.validators import instance_of, optional
import struct
from collections import namedtuple
from enum import IntEnum
from six import string_types

ChunkPosition = namedtuple('ChunkPosition', ['chunkId', 'size', 'data', 'end'])


class ChunkIndex(object):

    def __init__(self, size, position):
        self._size = size
        self._position = ChunkPosition(position,
                                       position + 4,
                                       position + 8,
                                       position + 8 + size)

    @property
    def size(self):
        return self._size

    @property
    def position(self):
        return self._position


class Format(IntEnum):
    PCM = 1
    WAVE_FORMAT_IEEE_FLOAT = 3
    WAVE_FORMAT_EXTENSIBLE = 65534


class FormatInfoChunk(object):
    """ Class representation of the FormatChunk

    This class can be either used to create a new format chunk or simplify
    reading and validation of a format chunk. Once created the object cannot be
    changed. You can only read the saved data. The order of the constructor
    arguments might seem a bit strange at first sight. The order corresponds to
    the order within a BW64 file. This makes it easier to create an object from
    the data read from a file. Cumbersome values like bytesPerSecond or
    blockAlignment can be omitted (thus set to `None`). But: if they are set,
    they have to be correct. Otherwise a ValueError is raised.

    To simplify the writing of files the FormatChunk (like every Chunk class in
    this module) has a asByteArray method. This method returns the correct byte
    array representation of the FormatChunk, which can be directly written to a
    file.
    """

    def __init__(self, formatTag=1, channelCount=1, sampleRate=48000,
                 bytesPerSecond=None, blockAlignment=None, bitsPerSample=16,
                 cbSize=None, extraData=None):
        self._formatTag = int(formatTag)
        self._channelCount = int(channelCount)
        self._sampleRate = int(sampleRate)
        self._bitsPerSample = int(bitsPerSample)
        self._cbSize = cbSize
        if(extraData):
            self._extraData = ExtraData(*extraData)
        else:
            self._extraData = None

        if(self.formatTag not in list(Format)):
            raise ValueError('format not supported: ' + str(self.formatTag))

        if self.cbSize:
            if cbSize != self.cbSize:
                raise ValueError(
                    'sanity check failed. \'cbSize\' is ' +
                    str(cbSize) + ' but should be ' +
                    str(self.cbSize)
                )

        if(self.formatTag == Format.WAVE_FORMAT_EXTENSIBLE):
            if not self.extraData:
                raise RuntimeError(
                    'missing extra data for WAVE_FORMAT_EXTENSIBLE')
            if self.extraData.subFormat not in list(Format):
                raise ValueError(
                    'subformat not supported: ' + str(self.formatTag))
            if formatTag != self.extraData.subFormat:
                raise ValueError(
                    'sanity check failed. \'formatTag\' and'
                    '\'extraData.subFormat\' do not match.'
                )

        if(self.channelCount < 1):
            raise ValueError('channelCount < 1')

        if(self.sampleRate < 1):
            raise ValueError('sampleRate < 1')

        if(self.bitsPerSample not in [16, 24, 32]):
            raise ValueError('bit depth not supported: ' +
                             str(self._bitsPerSample))

        if(bytesPerSecond):
            if(int(bytesPerSecond) != self.bytesPerSecond):
                raise ValueError(
                    'sanity check failed. \'bytesPerSecond\' is ' +
                    str(bytesPerSecond) + ' but should be ' +
                    str(self.bytesPerSecond)
                )

        if(blockAlignment):
            if(int(blockAlignment) != self.blockAlignment):
                raise ValueError(
                    'sanity check failed. \'blockAlignment\' is ' +
                    str(blockAlignment) + ' but should be ' +
                    str(self.blockAlignment)
                )
        if(cbSize):
            if(int(cbSize) != self.cbSize):
                raise ValueError(
                    'sanity check failed. \'cbSize\' is ' +
                    str(cbSize) + ' but should be ' +
                    str(self.cbSize)
                )

    @property
    def formatTag(self):
        if(self.extraData):
            return self.extraData.subFormat
        else:
            return self._formatTag

    @property
    def channelCount(self):
        return self._channelCount

    @property
    def sampleRate(self):
        return self._sampleRate

    @property
    def bytesPerSecond(self):
        return self.sampleRate * self.blockAlignment

    @property
    def blockAlignment(self):
        return int(self.channelCount * self.bitsPerSample / 8)

    @property
    def bitsPerSample(self):
        return self._bitsPerSample

    @property
    def cbSize(self):
        if(self.extraData):
            return len(self.extraData.asByteArray())
        else:
            return 0

    @property
    def extraData(self):
        return self._extraData

    def asByteArray(self):
        byteArrayData = struct.pack('<HHIIHH',
                                    self.formatTag,
                                    self.channelCount,
                                    self.sampleRate,
                                    self.bytesPerSecond,
                                    self.blockAlignment,
                                    self.bitsPerSample)
        if(self.cbSize):
            byteArrayData += struct.pack('<H', self.cbSize)
        if(self.extraData):
            byteArrayData += self.extraData.asByteArray()
        byteArraySize = struct.pack('<I', len(byteArrayData))
        byteArrayData = b'fmt ' + byteArraySize + byteArrayData
        return byteArrayData

    def __repr__(self):
        reprString = '[\n'
        reprString += '  formatTag: ' + str(self.formatTag) + '\n'
        reprString += '  channelCount: ' + str(self.channelCount) + '\n'
        reprString += '  sampleRate: ' + str(self.sampleRate) + '\n'
        reprString += '  bytesPerSecond: ' + str(self.bytesPerSecond) + '\n'
        reprString += '  blockAlignment: ' + str(self.blockAlignment) + '\n'
        reprString += '  bitsPerSample: ' + str(self.bitsPerSample) + '\n'
        if(self.cbSize):
            reprString += '  cbSize: ' + str(self.cbSize) + '\n'
        if(self.extraData):
            reprString += '  extraData: ' + str(self.extraData) + '\n'
        reprString += ']'
        return reprString


class ExtraData(object):
    """ExtraData of a FormatChunk """

    def __init__(self, validBitsPerSample, dwChannelMask, subFormat,
                 subFormatString):
        self._validBitsPerSample = int(validBitsPerSample)
        self._dwChannelMask = int(dwChannelMask)
        self._subFormat = int(subFormat)
        self._subFormatString = subFormatString

    @property
    def validBitsPerSample(self):
        return self._validBitsPerSample

    @validBitsPerSample.setter
    def setValidBitsPerSample(self, newValidBitsPerSample):
        self._newValidBitsPerSample = int(newValidBitsPerSample)

    @property
    def dwChannelMask(self):
        return self._dwChannelMask

    @dwChannelMask.setter
    def setDwChannelMask(self, newDwChannelMask):
        self._newDwChannelMask = int(newDwChannelMask)

    @property
    def subFormat(self):
        return self._subFormat

    @subFormat.setter
    def setSubFormat(self, newSubFormat):
        self._newSubFormat = int(newSubFormat)

    @property
    def subFormatString(self):
        return self._subFormatString

    @subFormatString.setter
    def setSubFormatString(self, newSubFormatString):
        self._newSubFormatString = str(newSubFormatString)

    def asByteArray(self):
        byteArrayData = struct.pack('<HIH14s',
                                    self.validBitsPerSample,
                                    self.dwChannelMask,
                                    self.subFormat,
                                    self.subFormatString)
        return byteArrayData

    def __repr__(self):
        reprString = '[ '
        reprString += str(self.validBitsPerSample) + ', '
        reprString += str(self.dwChannelMask) + ', '
        reprString += str(self.subFormat) + ', '
        reprString += str(self.subFormatString)
        reprString = ' ]'
        return reprString


class DataSize64Chunk(object):
    """ Class representation of the ds64Chunk

    This class can be either used to create a new ds64 chunk or simplify
    reading and validation of a ds64 chunk. The tableLength and table arguments
    are optional, but if they are set they have to be consitent. Otherwise the
    sanity check will raise a ValueError.

    To simplify the writing of files the DataSize64Chunk (like every chunk
    class in this module) has a asByteArray method. This method returns the
    correct byte array representation of the ds64Chunk, which can be
    directly written to a file.
    """

    def __init__(self, riffSize=0, dataSize=0, dummy=0, table=None):
        self._riffSize = int(riffSize)
        self._dataSize = int(dataSize)
        self._dummy = int(dummy)
        self._table = table if table is not None else {}

    @property
    def riffSize(self):
        return self._riffSize

    @riffSize.setter
    def setRiffSize(self, newRiffSize):
        self._riffSize = int(newRiffSize)

    @property
    def dataSize(self):
        return self._dataSize

    @dataSize.setter
    def setDataSize(self, newDataSize):
        self._dataSize = int(newDataSize)

    @property
    def dummy(self):
        return self._dummy

    @dummy.setter
    def setDummy(self, newDummy):
        self._dummy = int(newDummy)

    @property
    def tableLength(self):
        return len(self.table)

    @property
    def table(self):
        return self._table

    @table.setter
    def setTable(self, table):
        self._table = table

    def addTableEntry(self, chunkId, chunkSize):
        assert len(chunkId) == 4
        self._table[chunkId] = int(chunkSize)

    def asByteArray(self):
        fixed_part = struct.pack('<3QI', self.riffSize, self.dataSize,
                                 self.dummy, len(self.table))
        table_parts = [struct.pack('<4sQ', chunkId, chunkSize)
                       for chunkId, chunkSize in self.table.items()]

        chunk_data = fixed_part + b''.join(table_parts)

        chunk_header = struct.pack('<4sI', b'ds64', len(chunk_data))

        return chunk_header + chunk_data


@attrs
class ChnaChunk(object):
    """Class representation of the ChannelAllocationChunk

    Attributes:
        audioIDs (list of AudioID): CHNA entries
    """
    audioIDs = attrib(validator=instance_of(list), default=Factory(list))

    @property
    def numTracks(self):
        return len(set(x.trackIndex for x in self.audioIDs))

    @property
    def numUIDs(self):
        return len(self.audioIDs)

    @property
    def audioIDMap(self):
        return {audioID.audioTrackUID: audioID for audioID in self.audioIDs}

    def appendAudioID(self, newAudioID):
        self.audioIDs.append(newAudioID)

    def asByteArray(self):
        """Get the binary representation of this chunk data."""
        fixed_part = struct.pack('<HH', self.numTracks, self.numUIDs)
        table_part = b''.join(audioID.asByteArray() for audioID in self.audioIDs)

        chunk_data = fixed_part + table_part

        chunk_header = struct.pack('<4sI', b'chna', len(chunk_data))

        return chunk_header + chunk_data


@attrs
class AudioID(object):
    """Class representation of a chna audioIDs list entry.

    Attributes:
        trackIndex(int): 1-based index of the track in the sample data
        audioTrackUID(str): audioTrackUID of the track
        audioTrackFormatIDRef(str): audioTrackFormatID of the track
        audioPackFormatIDRef(str or None): optional audioPackFormatID of the
            track
    """
    trackIndex = attrib(validator=instance_of(int))
    audioTrackUID = attrib(validator=instance_of(string_types))
    audioTrackFormatIDRef = attrib(validator=instance_of(string_types))
    audioPackFormatIDRef = attrib(validator=optional(instance_of(string_types)))

    def asByteArray(self):
        pack_format_bin = (self.audioPackFormatIDRef.encode('utf-8')
                           if self.audioPackFormatIDRef is not None
                           else b"\0\0\0\0\0\0\0\0\0\0\0")
        return struct.pack('<H12s14s11sx',
                           self.trackIndex,
                           self.audioTrackUID.encode('utf-8'),
                           self.audioTrackFormatIDRef.encode('utf-8'),
                           pack_format_bin)
