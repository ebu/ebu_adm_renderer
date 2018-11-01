import struct
import numpy as np
from .chunks import ChunkIndex, FormatInfoChunk, DataSize64Chunk
from .utils import interleave, encode_pcm_samples


class Bw64Writer(object):

    def __init__(self, buffer, formatInfo=FormatInfoChunk(), chna=None,
                 axml=None, bext=None, forceBw64=False):
        """Write / create a new bw64 file to buffer.

        File format will be setup according to the specified formatinfo. Only
        PCM data (16bit, 24bit, 32bit) is currently supported.

        If axml data is given on construction, it will be written to the BW64
        file immediatly. If this is not possible on construction, one can use
        `set_axml` to set the axml data. In this case, it will be written
        _after_ the `data` chunk when the file is closed.

        After creation, sample data can be written to the `data` using `write`.
        The file will be finalized by calling `close()`.

        Note
        ----
        If you forget to `close()` the output object, the resulting file will
        be corrupted.

        Parameters
        ----------
        buffer: file - like object
        formatinfo: FormatInfoChunk
            Target format of the BW64 file.
        axml: str
            Content for the axml chunk.
        """
        self._buffer = buffer
        self._chunks = {}
        self._dataBytesWritten = 0
        self._formatInfo = formatInfo
        self._chnaChunkWritten = False
        self._chna = chna
        self._axmlChunkWritten = False
        self._axml = axml
        self._bextChunkWritten = False
        self._bext = bext
        self._forceBw64 = forceBw64

        self._buffer.seek(0)
        self._write_riff_chunk()
        self._write_junk_chunk()
        self._write_fmt_chunk()
        if(chna):
            self._write_chna_chunk()
        if(axml):
            self._write_axml_chunk()
        if(bext):
            self._write_bext_chunk()
        self._write_data_chunk_header()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
        self._buffer.close()

    @property
    def channels(self):
        return self._formatInfo.channelCount

    @property
    def sampleRate(self):
        return self._formatInfo.sampleRate

    @property
    def bitdepth(self):
        return self._formatInfo.bitsPerSample

    @property
    def chna(self):
        return self._chna

    @chna.setter
    def chna(self, chna):
        self._chna = chna

    @property
    def axml(self):
        return self._axml

    @axml.setter
    def axml(self, axml):
        self._axml = axml

    @property
    def bext(self):
        return self._bext

    @bext.setter
    def bext(self, bext):
        self._bext = bext

    def write(self, samples):
        """Append sample data to the BW64 data chunk.

        Parameters
        ----------
        samples: array - like, dtype float
            Array of audio samples, columns correspond to channels
            Expects float sample values in the range(-1, 1).
        """
        assert np.array(samples).shape[1] == self.channels

        samplesInterleaved = interleave(samples)
        samplesEncoded = encode_pcm_samples(samplesInterleaved, self.bitdepth)
        self._buffer.write(samplesEncoded)
        self._dataBytesWritten += len(samplesEncoded)

    def close(self):
        """Close and finalize the BW64 output.

        This means that the final chunk sizes will be written to the buffer.

        If you forget to call this function, the resulting file will be
        corrupted. Thus, it might be a good idea to use this with a
        contextmanager.
        """
        if not self._chnaChunkWritten and self._chna:
            self._write_chna_chunk()
        if not self._axmlChunkWritten and self._axml:
            self._write_axml_chunk()
        if not self._bextChunkWritten and self._bext:
            self._write_bext_chunk()

        riffChunkSize = self._calc_riff_chunk_size()
        if(riffChunkSize >= 2**32) or self._forceBw64:
            self._update_bw64_chunk()
            self._overwrite_junk_with_ds64_chunk()
        else:
            self._update_riff_chunk_size()
            self._update_data_chunk_size()

    def _write_riff_chunk(self):
        self._buffer.write(b'RIFF')
        self._buffer.write(b'\xff\xff\xff\xff')
        self._buffer.write(b'WAVE')

    def _write_data_chunk_header(self):
        self._chunks[b'data'] = ChunkIndex(-1, self._buffer.tell())
        self._buffer.write(b'data')
        self._buffer.write(b'\xff\xff\xff\xff')

    def _write_fmt_chunk(self):
        fmtChunkData = self._formatInfo.asByteArray()
        self._chunks[b'fmt '] = ChunkIndex(
            len(fmtChunkData), self._buffer.tell())
        self._buffer.write(fmtChunkData)

    def _calc_riff_chunk_size(self):
        last_position = self._buffer.tell()
        self._buffer.seek(0, 2)
        riffChunkSize = self._buffer.tell() - 8
        self._buffer.seek(last_position)
        return riffChunkSize

    def _update_riff_chunk_size(self):
        riffChunkSize = self._calc_riff_chunk_size()
        last_position = self._buffer.tell()
        self._buffer.seek(4)
        self._buffer.write(struct.pack('<I', riffChunkSize))
        self._buffer.seek(last_position)

    def _update_data_chunk_size(self):
        last_position = self._buffer.tell()
        self._buffer.seek(self._chunks[b'data'].position.size)
        self._buffer.write(struct.pack('<I', self._dataBytesWritten))
        self._buffer.seek(last_position)

    def _update_bw64_chunk(self):
        last_position = self._buffer.tell()
        self._buffer.seek(0)
        self._buffer.write(b'BW64')
        self._buffer.seek(last_position)

    def _write_junk_chunk(self):
        junkChunkData = struct.pack('<3QI', 0, 0, 0, 0)
        junkChunkSize = len(junkChunkData)
        self._chunks[b'JUNK'] = ChunkIndex(
            len(junkChunkData), self._buffer.tell())
        self._buffer.write(b'JUNK')
        self._buffer.write(struct.pack('<I', junkChunkSize))
        self._buffer.write(junkChunkData)

    def _overwrite_junk_with_ds64_chunk(self):
        self._buffer.seek(self._chunks[b'JUNK'].position.chunkId)
        ds64Chunk = DataSize64Chunk(
            self._calc_riff_chunk_size(), self._dataBytesWritten)
        ds64ChunkData = ds64Chunk.asByteArray()
        if (len(ds64ChunkData) - 8) != self._chunks[b'JUNK'].size:
            raise RuntimeError("space reserved by JUNK chunk not sufficient")
        self._chunks.pop(b'JUNK')
        self._chunks[b'ds64'] = ChunkIndex(
            len(ds64ChunkData), self._buffer.tell())
        self._buffer.write(ds64ChunkData)

    def _write_chna_chunk(self):
        chnaChunkData = self._chna.asByteArray()
        self._chunks[b'chna'] = ChunkIndex(
            len(chnaChunkData), self._buffer.tell())
        self._buffer.write(chnaChunkData)
        self._chnaChunkWritten = True

    def _write_axml_chunk(self):
        self._chunks[b'axml'] = ChunkIndex(
            len(self._axml), self._buffer.tell())
        self._buffer.write(b'axml')
        self._buffer.write(struct.pack('<I', len(self._axml)))
        self._buffer.write(self._axml)

        # pad to an even number of bytes; this is not in BS.2088 but is
        # commonly implemented in wav readers
        if len(self._axml) & 1:
            self._buffer.write(b'\0')

        self._axmlChunkWritten = True

    def _write_bext_chunk(self):
        bextChunkData = self._bext
        self._chunks[b'bext'] = ChunkIndex(
            len(bextChunkData), self._buffer.tell())
        self._buffer.write(b'bext')
        self._buffer.write(struct.pack('<I', len(bextChunkData)))
        self._buffer.write(bextChunkData)
        self._bextChunkWritten = True
