import logging
from .bw64 import Bw64Reader, Bw64Writer
from .adm.adm import ADM
from .adm.xml import load_axml_string
from .adm.common_definitions import load_common_definitions
from .adm.chna import load_chna_chunk


def openBw64(filename, mode='r', **kwargs):
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
    fileHandle = open(filename, 'rb')
    try:
        bw64FileHandle = Bw64Reader(fileHandle)
        return Bw64AdmReader(bw64FileHandle, fix_block_format_durations)
    except:  # noqa: E722
        fileHandle.close()
        raise


class Bw64AdmReader(object):

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
        return self._bw64.chna

    @property
    def sampleRate(self):
        return self._bw64.sampleRate

    @property
    def channels(self):
        return self._bw64.channels

    @property
    def bitdepth(self):
        return self._bw64.bitdepth

    @property
    def selected_items(self):
        from ..core.select_items import select_rendering_items
        return select_rendering_items(self.adm)

    def iter_sample_blocks(self, blockSize):
        """Read samples blockwise until next ChangeSet and yield it."""
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
