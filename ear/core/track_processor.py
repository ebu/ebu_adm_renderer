from __future__ import division
from attr import evolve
import numpy as np
import math
from multipledispatch import Dispatcher
from .delay import Delay
from .metadata_input import TrackSpec, DirectTrackSpec, SilentTrackSpec, MatrixCoefficientTrackSpec, MixTrackSpec


class TrackProcessorBase(object):
    """Base class for processors which can be used to obtain samples for a
    single track spec given multi-track input samples (from a WAV file for
    example).

    Use :func:`TrackProcessor` to create these.
    """
    def __init__(self, track_spec):
        """
        Parameters:
            track_spec (TrackSpec): Track spec to render.
        """

    def process(self, sample_rate, input_samples):
        """Get the samples for one track spec.

        Parameters:
            sample_rate (int): sample rate of input/output samples in Hz
            input_samples (array of (n, c) floats): c channels of n input samples

        Returns:
            array of (n,) floats: n samples for track_spec.
        """
        raise NotImplementedError("called base class")  # pragma: no cover


def TrackProcessor(track_spec):
    """Build a processor to render a single track spec.

    Parameters:
        track_spec (TrackSpec): Track spec to render.

    Returns:
        TrackProcessorBase: processor to obtain samples for track_spec
    """
    return _track_spec_processor(_simplify_track_spec(track_spec))


class MultiTrackProcessor(TrackProcessorBase):
    """A processor that renders multiple track specs into a single array given
    multi-track input samples (from a WAV file for example).
    """

    def __init__(self, track_specs):
        """
        Parameters:
            track_specs (list of TrackSpec): Track spec for each output channel.
        """
        self.processors = [TrackProcessor(track) for track in track_specs]

    def process(self, sample_rate, input_samples):
        """Get the samples for all track specs.

        Parameters:
            sample_rate (int): sample rate of input/output samples in Hz
            input_samples (array of (n, c) floats): c channels of n input samples

        Returns:
            array of (n, m) floats: n samples for each of the m track_specs.
        """
        return np.stack([processor.process(sample_rate, input_samples)
                         for processor in self.processors],
                        1)

################
# implementation
################


# simplify a single track spec; type TrackSpec -> TrackSpec
# The return value should have the same effect as the parameter. This is
# applied to just the top-level track-spec -- the simplification function for
# each type should apply this recursively to any input track specs.
_simplify_track_spec = Dispatcher("_simplify_track_spec")

# build a processor for a single track spec; type: TrackSpec -> TrackProcessorBase
# The track spec must have been simplified before this is called; this allows
# processors to ignore some cases which can be simplified away.
_track_spec_processor = Dispatcher("track_processor")


@_simplify_track_spec.register(TrackSpec)
def _simplify_base(track_spec):
    """If no simplification is specified for a type, do nothing."""
    return track_spec


# silent

@_track_spec_processor.register(SilentTrackSpec)
class SilentProcessor(TrackProcessorBase):
    def __init__(self, track_spec):
        pass

    def process(self, sample_rate, input_samples):
        return np.zeros(input_samples.shape[0])


# direct

@_track_spec_processor.register(DirectTrackSpec)
class DirectProcessor(TrackProcessorBase):
    def __init__(self, track_spec):
        self.track_index = track_spec.track_index

    def process(self, sample_rate, input_samples):
        return input_samples[:, self.track_index]


# mix

@_simplify_track_spec.register(MixTrackSpec)
def _simplify_mix(track_spec):
    """All the input specs are simplified, and any silent tracks removed. If
    there are no input tracks left, then the track is silent. If there's only
    one track, then that track can be used directly. Otherwise a mix is really
    required.
    """
    input_tracks = track_spec.input_tracks

    input_tracks = [_simplify_track_spec(input_track) for input_track in input_tracks]

    input_tracks = [input_track for input_track in input_tracks if not isinstance(input_track, SilentTrackSpec)]

    if len(input_tracks) > 1:
        return MixTrackSpec(input_tracks)
    elif len(input_tracks) == 1:
        return input_tracks[0]
    else:
        return SilentTrackSpec()


@_track_spec_processor.register(MixTrackSpec)
class MixProcessor(TrackProcessorBase):
    def __init__(self, track_spec):
        assert len(track_spec.input_tracks), "track spec not simplified before rendering"
        self.input_processors = [_track_spec_processor(track) for track in track_spec.input_tracks]

    def process(self, sample_rate, input_samples):
        output = 0
        for processor in self.input_processors:
            output += processor.process(sample_rate, input_samples)

        return output


# matrix coefficient

@_simplify_track_spec.register(MatrixCoefficientTrackSpec)
def _simplify_matrix(track_spec):
    """The input track is simplified. If it is silent, the output from the
    matrix would be silent, so a silent track is returned.
    """
    track_spec = evolve(track_spec,
                        input_track=_simplify_track_spec(track_spec.input_track))

    if isinstance(track_spec.input_track, SilentTrackSpec):
        return SilentTrackSpec()

    return track_spec


@_track_spec_processor.register(MatrixCoefficientTrackSpec)
class MatrixCoefficientProcessor(TrackProcessorBase):
    def __init__(self, track_spec):
        self.input_processor = _track_spec_processor(track_spec.input_track)
        self.coefficient = track_spec.coefficient
        self.delay = None
        self.sample_rate = None

    def init_delay(self, sample_rate):
        if self.delay is None:
            delay_samples = int(math.ceil((sample_rate * self.coefficient.delay) / 1000.0 - 0.5))
            self.delay = Delay(1, delay_samples)
            self.sample_rate = sample_rate
        else:
            assert self.sample_rate == sample_rate

    def process(self, sample_rate, input_samples):
        samples = self.input_processor.process(sample_rate, input_samples)

        if self.coefficient.gain is not None:
            samples = samples * self.coefficient.gain

        if self.coefficient.delay is not None:
            self.init_delay(sample_rate)
            samples = self.delay.process(samples[:, np.newaxis])[:, 0]

        return samples
