import numpy as np
import warnings
from ..hoa_adapter import HOAFormat, HOAPointSourceAdapter
from ..screen_edge_lock import ScreenEdgeLockHandler
from .panner import SpeakerLabelHandler, build_direct_speakers_panner


class DirectSpeakersPannerHOA(object):
    def __init__(self, fmt, additional_substitutions={}):
        self._panner = HOAPointSourceAdapter.build(fmt)
        self._label_handler = SpeakerLabelHandler(additional_substitutions)
        self._screen_edge_lock_handler = ScreenEdgeLockHandler(fmt.screen, fmt)

    def handle(self, type_metadata):
        if self._label_handler.is_lfe_channel(type_metadata):
            warnings.warn("discarding DirectSpeakers LFE channel")
            return np.zeros(self._panner.num_channels)

        position = self._screen_edge_lock_handler.handle_ds_position(
            type_metadata.block_format.position
        )

        return self._panner.handle(position.as_cartesian_array())


@build_direct_speakers_panner.register(HOAFormat)
def _build_direct_speakers_panner_hoa(layout, **options):
    return DirectSpeakersPannerHOA(layout, **options)
