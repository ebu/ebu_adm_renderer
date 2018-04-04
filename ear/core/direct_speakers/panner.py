from attr import evolve
from multipledispatch import dispatch
import numpy as np
import re
import warnings
from ..geom import inside_angle_range
from .. import point_source
from ..renderer_common import is_lfe
from ...options import OptionsHandler, SubOptions, Option
from ..screen_edge_lock import ScreenEdgeLockHandler
from ...fileio.adm.elements import DirectSpeakerCartesianPosition, DirectSpeakerPolarPosition


inside_angle_range_vec = np.vectorize(inside_angle_range)


class DirectSpeakersPanner(object):

    options = OptionsHandler(
        point_source_opts=SubOptions(
            handler=point_source.configure_options,
            description="options for point source panner",
        ),
        additional_substitutions=Option(
            default={},
            description="dictionary of additional speaker label substitutions",
        ),
    )

    @options.with_defaults
    def __init__(self, layout, point_source_opts={}, additional_substitutions={}):
        self.layout = layout
        self.psp = point_source.configure(layout.without_lfe, **point_source_opts)

        self.n_channels = len(layout.channels)
        self.channel_names = layout.channel_names

        self.azimuths = np.array([channel.polar_nominal_position.azimuth for channel in layout.channels])
        self.elevations = np.array([channel.polar_nominal_position.elevation for channel in layout.channels])
        self.distances = np.array([channel.polar_nominal_position.distance for channel in layout.channels])

        self.positions = layout.nominal_positions
        self.is_lfe = layout.is_lfe

        self._screen_edge_lock_handler = ScreenEdgeLockHandler(self.layout.screen)

        self.pvs = np.eye(self.n_channels)

        self.substitutions = {
            "LFE": "LFE1",
            "LFEL": "LFE1",
            "LFER": "LFE2",
        }
        self.substitutions.update(additional_substitutions)

    SPEAKER_URN_REGEX = re.compile("^urn:itu:bs:2051:[0-9]+:speaker:(.*)$")

    def nominal_speaker_label(self, label):
        """Get the bs.2051 speaker label from an ADM speaker label.

        This parses URNs, and deals with alternative notations for LFE
        channels.
        """
        match = self.SPEAKER_URN_REGEX.match(label)
        if match is not None:
            label = match.group(1)

        if label in self.substitutions:
            label = self.substitutions[label]

        return label

    def closest_channel_index(self, position, candidates, tol):
        """Get the index of the candidate speaker closest to a given position.

        If there are multiple speakers that are considered equally close with
        respect to a given tolerance, no decision on the closest speaker
        can be made.

        Parameters:
            position (DirectSpeakerPolarPosition or DirectSpeakerCartesianPosition):
                Target position
            candidates (boolean index array): Subset of self.speakers to be considered
            tol (float): tolerance for defintion of "closest".

        Returns:
            Index to the speaker in self.speakers that is closest to the
            target position or `None` if no such speaker can be uniquely defined.
        """
        cart_position = position.as_cartesian_array()

        candidate_position_indizes = np.flatnonzero(candidates)

        distances = np.linalg.norm(
            self.positions[candidate_position_indizes] - cart_position[np.newaxis],
            axis=1)

        min_idx = np.argmin(distances)
        min_dist = distances[min_idx]

        # if we find exactly one match within the given tolerance, use it
        if np.count_nonzero(np.abs(min_dist - distances) < tol) == 1:
            return candidate_position_indizes[min_idx]
        # Otherwise, we either don't have a match or we have multiple matches
        else:
            return None

    @dispatch(DirectSpeakerPolarPosition, float)  # noqa: F811
    def channels_within_bounds(self, position, tol):
        """Get a bit mask of channels within the bounds in position."""

        def min_max_default(bound):
            return (bound.min if bound.min is not None else bound.value,
                    bound.max if bound.max is not None else bound.value)

        az_min, az_max = min_max_default(position.bounded_azimuth)
        el_min, el_max = min_max_default(position.bounded_elevation)
        dist_min, dist_max = min_max_default(position.bounded_distance)

        return (
            (inside_angle_range_vec(self.azimuths, az_min, az_max, tol=tol) |
             # speakers at the poles have indeterminate azimuth and should match
             # any azimuth range
             (np.abs(self.elevations) >= 90.0 - tol)) &
            (self.elevations > el_min - tol) & (self.elevations < el_max + tol) &
            (self.distances > dist_min - tol) & (self.distances < dist_max + tol)
        )

    @dispatch(DirectSpeakerCartesianPosition, float)  # noqa: F811
    def channels_within_bounds(self, position, tol):
        """Get a bit mask of channels within the bounds in position."""

        bounds = [position.bounded_X, position.bounded_Y, position.bounded_Z]
        bounds_min = [bound.min if bound.min is not None else bound.value
                      for bound in bounds]
        bounds_max = [bound.max if bound.max is not None else bound.value
                      for bound in bounds]

        return (
            np.all(self.positions + tol >= bounds_min, axis=1) &
            np.all(self.positions - tol <= bounds_max, axis=1)
        )

    def is_lfe_channel(self, type_metadata):
        """Determine if type_metadata is an LFE channel, issuing a warning is
        there's a discrepancy between the speakerLabel and the frequency
        element."""
        has_lfe_freq = is_lfe(type_metadata.extra_data.channel_frequency)

        has_lfe_name = False
        for label in type_metadata.block_format.speakerLabel:
            nominal_label = self.nominal_speaker_label(label)

            if nominal_label in ("LFE1", "LFE2"):
                has_lfe_name = True

        if has_lfe_freq != has_lfe_name and type_metadata.block_format.speakerLabel:
            warnings.warn("LFE indication from frequency element does not match speakerLabel.")

        return has_lfe_freq or has_lfe_name

    @dispatch(DirectSpeakerPolarPosition)  # noqa: F811
    def apply_screen_edge_lock(self, position):
        az, el = self._screen_edge_lock_handler.handle_az_el(position.azimuth,
                                                             position.elevation,
                                                             position.screenEdgeLock)

        return evolve(position,
                      bounded_azimuth=evolve(position.bounded_azimuth, value=az),
                      bounded_elevation=evolve(position.bounded_elevation, value=el))

    @dispatch(DirectSpeakerCartesianPosition)  # noqa: F811
    def apply_screen_edge_lock(self, position):
        X, Y, Z = self._screen_edge_lock_handler.handle_vector(position.as_cartesian_array(),
                                                               position.screenEdgeLock)

        return evolve(position,
                      bounded_X=evolve(position.bounded_X, value=X),
                      bounded_Y=evolve(position.bounded_Y, value=Y),
                      bounded_Z=evolve(position.bounded_Z, value=Z))

    def handle(self, type_metadata):
        tol = 1e-5

        block_format = type_metadata.block_format

        is_lfe_channel = self.is_lfe_channel(type_metadata)

        # try to find a speaker that matches a speakerLabel and type; earlier
        # speakerLabel values have higher priority

        for label in block_format.speakerLabel:
            nominal_label = self.nominal_speaker_label(label)
            if nominal_label in self.channel_names:
                idx = self.channel_names.index(nominal_label)
                if is_lfe_channel == self.is_lfe[idx]:
                    return self.pvs[idx]

        # shift the nominal speaker position to the screen edges if specified
        shifted_position = self.apply_screen_edge_lock(block_format.position)

        # otherwise, find the closest speaker with the correct type within the given bounds

        within_bounds = self.channels_within_bounds(shifted_position, tol)
        if is_lfe_channel:
            within_bounds &= self.is_lfe
        else:
            within_bounds &= ~self.is_lfe
        if np.any(within_bounds):
            closest = self.closest_channel_index(
                shifted_position,
                within_bounds,
                tol)

            # if we can uniquely identify the closes speaker, use it
            if closest is not None:
                return self.pvs[closest]

        # otherwise, use the point source panner for non-LFE, and handle LFE
        # channels using downmixing rules

        if is_lfe_channel:
            # if there are no LFE outputs, LFE channels are thrown away (as
            # in bs.775). for 22.2 -> 5.1, according to "Downmixing Method
            # for 22.2 Multichannel Sound Signal in 8K Super Hi-Vision
            # Broadcasting", both LFE channels should be mixed into the one
            # output channel, so any LFE channels that don't have a
            # corresponding output (handled above) are sent to LFE1.
            if "LFE1" in self.channel_names:
                return self.pvs[self.channel_names.index("LFE1")]
            else:
                return np.zeros(self.n_channels)
        else:
            position = shifted_position.as_cartesian_array()

            pv = np.zeros(self.n_channels)
            pv[~self.is_lfe] = self.psp.handle(position)
            return pv
