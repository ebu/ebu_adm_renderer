import io
import re
import struct
import warnings
from .chunks import ChunkIndex, FormatInfoChunk, DataSize64Chunk, ChnaChunk, AudioID
from .utils import deinterleave, decode_pcm_samples


# the original RIFF spec[0] says:
#
#   A FOURCC is represented as a sequence of one to four ASCII alphanumeric
#   characters, padded on the right with blank characters (ASCII character
#   value 32) as required, with no embedded blanks.
#
# these are checked because a bad ID is usually the first indication of
# misalignment
#
# [0]: Multimedia Programming Interface and Data Specifications 1.0, 1991
CHUNK_ID_RE = re.compile(b"[a-zA-Z0-9]+ *")


class Bw64Reader(object):
    """Read a WAVE/RF64/BW64 file.

    Only PCM data (16bit, 24bit, 32bit) is currently supported. The class
    provides easy access to the axml, chna, bext chunks. The most important
    format information (samplerate, sample rate, bit rate, ...) can be directly
    accessed as properties.
    """

    def __init__(self, buffer):
        self._buffer = buffer
        self._chunks = {}

        self._buffer.seek(0, io.SEEK_END)
        self._file_len = self._buffer.tell()
        self._buffer.seek(0)

        self._read_riff_chunk()
        self._ds64 = None
        if(self.fileFormat in [b'RF64', b'BW64']):
            self._read_ds64_chunk()
        self._read_chunks()
        self._check_chunks()
        self._read_fmt_chunk()
        self._read_chna_chunk()
        self.seek(0)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._buffer.close()

    @property
    def axml(self):
        """bytes or None: data contained in axml chunk"""
        if(b'axml' in self._chunks):
            last_position = self._buffer.tell()
            self._buffer.seek(self._chunks[b'axml'].position.data)
            axml = self._buffer.read(self._chunks[b'axml'].size)
            self._buffer.seek(last_position)
            return axml
        else:
            return None

    @property
    def bext(self):
        """bytes or None: data contained in bext chunk"""
        if(b'bext' in self._chunks):
            last_position = self._buffer.tell()
            self._buffer.seek(self._chunks[b'bext'].position.data)
            bext = self._buffer.read(self._chunks[b'bext'].size)
            self._buffer.seek(last_position)
            return bext
        else:
            return None

    @property
    def chna(self):
        """chunks.ChnaChunk or None: CHNA data"""
        return self._chna

    @property
    def sampleRate(self):
        """sample rate in Hz"""
        return self._formatInfo.sampleRate

    @property
    def channels(self):
        """number of channels"""
        return self._formatInfo.channelCount

    @property
    def bitdepth(self):
        """number of bits per sample"""
        return self._formatInfo.bitsPerSample

    @property
    def formatInfo(self):
        return self._formatInfo

    def seek(self, offset, whence=0):
        frameOffset = offset * self._formatInfo.blockAlignment
        chunkIndex = self._chunks[b'data']
        if(whence == 0):
            dataChunkOffset = chunkIndex.position.data
        elif(whence == 1):
            dataChunkOffset = self._buffer.tell()
        elif(whence == 2):
            dataChunkOffset = chunkIndex.position.end
        else:
            raise ValueError('whence value ' + str(whence) + ' unsupported')

        if(dataChunkOffset + frameOffset < chunkIndex.position.data):
            self._buffer.seek(chunkIndex.position.data)
        elif(dataChunkOffset + frameOffset > chunkIndex.position.end):
            self._buffer.seek(chunkIndex.end)
        else:
            self._buffer.seek(dataChunkOffset + frameOffset)

    def read(self, numberOfFrames):
        """read up to numberOfFrames samples

        Returns:
            np.ndarray of float: sample blocks of shape (nsamples, nchannels),
            where nsamples is <= numberOfFrames, and nchannels is the number of
            channels
        """
        if(self.tell() + numberOfFrames > len(self)):
            numberOfFrames = len(self) - self.tell()
        rawData = self._buffer.read(
            numberOfFrames * self._formatInfo.blockAlignment)
        samplesDecoded = decode_pcm_samples(rawData, self.bitdepth)
        return deinterleave(samplesDecoded, self.channels)

    def tell(self):
        """Get the sample number of the next sample returned by read."""
        return ((self._buffer.tell() - self._chunks[b'data'].position.data) //
                self._formatInfo.blockAlignment)

    def iter_sample_blocks(self, blockSize):
        """Read blocks of samples from the file.

        Parameters:
            blockSize(int): number of samples to read at a time

        Yields:
            np.ndarray of float: sample blocks of shape (nsamples, nchannels),
            where nsamples is <= blockSize, and nchannels is the number of
            channels
        """
        while self.tell() != len(self):
            yield self.read(blockSize)

    def __len__(self):
        """ Returns number of frames """
        if (self._ds64):
            return self._ds64.dataSize // self._formatInfo.blockAlignment
        else:
            return self._chunks[b'data'].size // self._formatInfo.blockAlignment

    def _read_riff_chunk(self):
        chunkId, chunkSize = struct.unpack('<4sI', self._buffer.read(8))
        self.fileFormat = chunkId
        self._riffSize = chunkSize
        if self.fileFormat not in [b'RIFF', b'RF64', b'BW64']:
            raise RuntimeError('not a riff, rf64 or bw64 file')
        """
        # standard conform files should set the chunkSize to -1. But e. g.
        # Reaper writes the actual size if the output format option "Force
        # RF64" is selected. Hence we do not check this.
        if self.fileFormat in [b'RF64', b'BW64']:
            if self._riffSize != int("0xFFFFFFFF", 0):
                raise RuntimeError(
                    'malformed rf64 or bw64 file: chunkSize != -1')
        """
        riffType = struct.unpack('<4s', self._buffer.read(4))[0]
        if riffType != b'WAVE':
            raise RuntimeError('not a wave file')

    def _read_ds64_chunk(self):
        chunkId, chunkSize = struct.unpack('<4sI', self._buffer.read(8))
        if chunkId != b'ds64':
            raise RuntimeError(
                'malformed rf64 or bw64 file: missing ds64 chunk')
        chunkData = self._buffer.read(chunkSize)

        fixedPartFmt = '<3QI'
        fixedPartSize = struct.calcsize(fixedPartFmt)
        tableEntryFmt = '<4sQ'
        TableEntrySize = struct.calcsize(tableEntryFmt)

        fixedPart, tablePart = chunkData[:fixedPartSize], chunkData[fixedPartSize:]

        riffSize, dataSize, dummy, tableLength = struct.unpack(fixedPartFmt, fixedPart)
        self._ds64 = DataSize64Chunk(riffSize, dataSize, dummy)

        for tableId in range(tableLength):
            tableStart = tableId * TableEntrySize
            tableEntryPart = tablePart[tableStart: tableStart + TableEntrySize]

            chunkId, chunkSize = struct.unpack(tableEntryFmt, tableEntryPart)
            self._ds64.addTableEntry(chunkId, chunkSize)

    def _read_chunk_header(self):
        data = self._buffer.read(8)
        if len(data) != 8:  # EOF
            return None
        chunkId, chunkSize = struct.unpack('<4sI', data)

        if CHUNK_ID_RE.fullmatch(chunkId) is None:
            raise ValueError(f"found chunk header with invalid ID {chunkId}")

        # correct chunkSize for rf64 and bw64 files
        if self.fileFormat in [b'RF64', b'BW64']:
            if chunkId == b'data':
                chunkSize = self._ds64.dataSize
            elif chunkId in self._ds64.table:
                chunkSize = self._ds64.table[chunkId]
        return (chunkId, chunkSize)

    def _read_chunks(self):
        while True:
            chunkHeader = self._read_chunk_header()
            if not chunkHeader:
                return
            chunkId = chunkHeader[0]
            chunkSize = chunkHeader[1]
            self._chunks[chunkId] = ChunkIndex(
                chunkSize, self._buffer.tell() - 8)
            # always skip an even number of bytes
            self._buffer.seek(chunkSize + (chunkSize & 1), 1)

            chunk_end = self._buffer.tell()
            if chunk_end > self._file_len:
                if (chunkSize & 1) and chunkId == b'data' and chunk_end == self._file_len + 1:
                    warnings.warn("data chunk is missing padding byte")
                else:
                    raise ValueError(
                        f"{chunkId} chunk ends after the end of the file: "
                        f"header says {chunk_end} but file ends at {self._file_len}")

    def _check_chunks(self):
        required_chunks = [b'fmt ', b'data']

        for chunk in required_chunks:
            if chunk not in self._chunks:
                raise ValueError(f'required chunk "{chunk.decode("ascii")}" not found')

    def _read_fmt_chunk(self):
        last_position = self._buffer.tell()
        self._buffer.seek(self._chunks[b'fmt '].position.data)
        bytes_left = self._chunks[b'fmt '].size
        base_size = 16

        if bytes_left < base_size:
            raise ValueError('illegal format chunk size')

        fields = struct.unpack('<HHIIHH', self._buffer.read(base_size))
        bytes_left -= base_size

        if bytes_left > 2:
            cbSize = struct.unpack('<H', self._buffer.read(2))[0]
            bytes_left -= 2
            fields += (cbSize,)
        else:
            cbSize = 0

        if cbSize > bytes_left:
            raise ValueError('fmt chunk not big enough for cbSize')

        if cbSize == 0:
            pass
        elif cbSize == 22:
            fields += (struct.unpack('<HIH14s', self._buffer.read(22)),)
            bytes_left -= 22
        else:
            raise ValueError(f'invalid cbSize, expected 0 or 22, got {cbSize}')

        self._formatInfo = FormatInfoChunk(*fields)
        self._buffer.seek(last_position)

    def get_chunk_data(self, chunk_name):
        """Read and return the binary data of a named chunk."""
        self._buffer.seek(self._chunks[chunk_name].position.data)
        return self._buffer.read(self._chunks[chunk_name].size)

    def _read_chna_chunk(self):
        self._chna = None
        if(b'chna' not in self._chunks):
            return
        last_position = self._buffer.tell()
        self._buffer.seek(self._chunks[b'chna'].position.data)
        numTracks, numUIDs = struct.unpack('<HH', self._buffer.read(4))
        audioIDs = []
        for audioID in range(numUIDs):
            trackIndex, trackUID, trackFormat, packFormat = struct.unpack('<H12s14s11sx', self._buffer.read(40))

            # remove padding for audioChannelFormat reference
            if trackFormat.startswith(b"AC_"):
                if trackFormat[-3:] != b"_00":
                    warnings.warn(f"CHNA trackRef is expected to have format AC_xxxxxxxx_00, "
                                  f"but is {trackFormat.decode('utf8')!r}")
                trackFormat = trackFormat[:-3]

            nullPackFormat = b"\0\0\0\0\0\0\0\0\0\0\0"
            audioIDs.append(AudioID(
                trackIndex=trackIndex,
                audioTrackUID=trackUID.decode("utf-8"),
                audioTrackFormatIDRef=trackFormat.decode("utf-8"),
                audioPackFormatIDRef=(None if packFormat == nullPackFormat
                                      else packFormat.decode("utf-8")),
            ))
        self._chna = ChnaChunk(audioIDs)

        if self._chna.numTracks != numTracks:
            raise ValueError(
                "numTracks in CHNA ({numTracks}) does not match the number of referenced tracks ({chna.numTracks})".format(
                    chna=self._chna, numTracks=numTracks))
        assert self._chna.numUIDs == numUIDs

        self._buffer.seek(last_position)
