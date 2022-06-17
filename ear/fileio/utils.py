import logging
from .bw64 import Bw64Reader, Bw64Writer
from .adm.adm import ADM
from .adm.xml import load_axml_string
from .adm.common_definitions import load_common_definitions
from .adm.chna import load_chna_chunk


def openBw64(filename, mode='r', **kwargs):
    """Open a BW64 file for reading or writing.

    Parameters:
        filename (str): file name
        mode (str): ``r`` for read, or ``w`` for write
        kwargs: Extra arguments for Bw64Reader or Bw64Writer

    Returns:
        Bw64Reader or Bw64Writer: file object
    """
    if mode == 'r':
        fileHandle = open(filename, 'rb')
        try:
            return Bw64Reader(fileHandle, **kwargs)
        except:  # noqa: E722
            fileHandle.close()
            raise
    elif mode == 'w':
        fileHandle = open(filename, 'wb')
        try:
            return Bw64Writer(fileHandle, **kwargs)
        except:  # noqa: E722
            fileHandle.close()
            raise
    else:
        raise RuntimeError('unknown mode: ' + str(mode))


def openBw64Adm(filename, fix_block_format_durations=False):
    """Open a BW64 ADM file for reading. This automatically parses the ADM
    data, adds the common definitions, and adds information from the CHNA
    chunk. This can be accessed through the ``.adm`` attribute of the returned
    Bw64AdmReader.

    Parameters:
        filename (str): file name
        fix_block_format_durations (bool): attempt to fix rounding errors in
            audioBlockFormat durations

    Returns:
        Bw64AdmReader: file object
    """
    fileHandle = open(filename, 'rb')
    try:
        bw64FileHandle = Bw64Reader(fileHandle)
        return Bw64AdmReader(bw64FileHandle, fix_block_format_durations)
    except:  # noqa: E722
        fileHandle.close()
        raise


class Bw64AdmReader(object):
    """Utility for reading ADM data from a BW64 file; use :func:`.openBw64Adm`
    to create these.

    Attributes:
        adm (ADM): ADM data
    """

    def __init__(self, bw64FileHandle, fix_block_format_durations=False):
        self.logger = logging.getLogger(__name__)
        self._bw64 = bw64FileHandle
        self._fix_block_format_durations = fix_block_format_durations
        self.adm = self._parse_adm()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._bw64._buffer.close()

    @property
    def chna(self):
        """bw64.chunks.ChnaChunk: CHNA data"""
        return self._bw64.chna

    @property
    def sampleRate(self):
        """sample rate in Hz"""
        return self._bw64.sampleRate

    @property
    def channels(self):
        """number of channels"""
        return self._bw64.channels

    @property
    def bitdepth(self):
        """number of bits per sample"""
        return self._bw64.bitdepth

    @property
    def selected_items(self):
        """list of ear.core.metadata_input.RenderingItem: default list of
        rendering items"""
        from ..core.select_items import select_rendering_items
        return select_rendering_items(self.adm)

    def iter_sample_blocks(self, blockSize):
        """Read blocks of samples from the file.

        Parameters:
            blockSize(int): number of samples to read at a time

        Yields:
            np.ndarray of float: sample blocks of shape (nsamples, nchannels),
            where nsamples is <= blockSize, and nchannels is the number of
            channels
        """
        while(self._bw64.tell() != len(self._bw64)):
            yield self._bw64.read(blockSize)

    def _parse_adm(self):
        adm = ADM()
        load_common_definitions(adm)
        if self._bw64.axml is not None:
            self.logger.info("Parsing")
            load_axml_string(adm, self._bw64.axml, fix_block_format_durations=self._fix_block_format_durations)
            self.logger.info("Parsing done!")
        load_chna_chunk(adm, self._bw64.chna)
        return adm
