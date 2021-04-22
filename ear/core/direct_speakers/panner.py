from attr import attrs, attrib, evolve
from multipledispatch import dispatch
import numpy as np
import re
import warnings
from ..geom import inside_angle_range
from .. import point_source
from .. import allocentric
from ..renderer_common import is_lfe
from ...options import OptionsHandler, SubOptions, Option
from ..screen_edge_lock import ScreenEdgeLockHandler
from ...fileio.adm.elements import DirectSpeakerCartesianPosition, DirectSpeakerPolarPosition


inside_angle_range_vec = np.vectorize(inside_angle_range)


@attrs
class MappingRule(object):
    """Remap a particular channel if all output loudspeakers in gains exist and
    the input layout is as given.

    Attributes:
        speakerLabel (str): Label of speaker to match.
        gains (list of (channel name, gain)): Gains to match and apply.
        input_layouts (list of str or None): Optional ITU names of input
            layouts to match against. If this isn't given then the rule applies
            for any input layout.
        output_layouts (list of str or None): Optional ITU names of output
            layouts to match against. If this isn't given then the rule applies
            for any output layout.
    """
    speakerLabel = attrib()
    gains = attrib()
    input_layouts = attrib(default=None)
    output_layouts = attrib(default=None)

    def apply(self, input_layout, speakerLabel, output_layout):
        """Get the gains given my the rule.

        Parameters:
            input_layout (str): ITU name of input layout to map from.
            speakerLabel (str): Label of speaker to map.
            output_layout (Layout): Output channel layout to map to.
        Returns:
            None if the rule does not apply, or a list of (channel name, gain)
            tuples.
        """
        if self.input_layouts is not None and input_layout not in self.input_layouts:
            return

        if self.output_layouts is not None and output_layout.name not in self.output_layouts:
            return

        if speakerLabel != self.speakerLabel:
            return

        output_channel_names = set(output_layout.channel_names)
        if all(channel_name in output_channel_names for channel_name, gain in self.gains):
            return self.gains


def _add_symmetric_rules(rules):
    """Given a list of MappingRules, yield an expanded set of rules with
    symmetric rules added. Symmetric rules are the same except with + and -
    switched
    """
    def opposite_name(channel_name):
        if channel_name.endswith("000") or channel_name.endswith("180"):
            return channel_name
        else:
            return channel_name.replace("+", "-") if "+" in channel_name else channel_name.replace("-", "+")

    for rule in rules:
        yield rule

        new_rule = evolve(rule,
                          speakerLabel=opposite_name(rule.speakerLabel),
                          gains=[(opposite_name(l), g) for l, g in rule.gains],
                          )

        # don't add rules which would have the same effect
        if (rule.speakerLabel != new_rule.speakerLabel
                or sorted(rule.gains) != sorted(new_rule.gains)):
            yield new_rule


rules = list(_add_symmetric_rules([
    MappingRule("M+000", [("M+000", 1.0)]),
    MappingRule("M+000", [("M+030", np.sqrt(1.0/2.0)), ("M-030", np.sqrt(1.0/2.0))]),

    MappingRule("M+060", [("M+060", 1.0)]),
    MappingRule("M+060", [("M+030", np.sqrt(2.0/3.0)), ("M+110", np.sqrt(1.0/3.0))]),
    MappingRule("M+060", [("M+030", np.sqrt(1.0/2.0)), ("M+090", np.sqrt(1.0/2.0))]),
    MappingRule("M+060", [("M+030", 1.0)]),

    MappingRule("M+090", [("M+090", 1.0)]),
    MappingRule("M+090", [("M+030", np.sqrt(1.0/3.0)), ("M+110", np.sqrt(2.0/3.0))], input_layouts=["9+10+3"]),
    MappingRule("M+090", [("M+030", np.sqrt(1.0/2.0)), ("M+110", np.sqrt(1.0/2.0))]),
    MappingRule("M+090", [("M+030", np.sqrt(1.0/2.0))]),

    MappingRule("M+110", [("M+110", 1.0)]),
    MappingRule("M+110", [("M+135", 1.0)]),
    MappingRule("M+110", [("M+030", np.sqrt(1.0/2.0))]),

    MappingRule("M+135", [("M+135", 1.0)]),
    MappingRule("M+135", [("M+110", 1.0)]),
    MappingRule("M+135", [("M+030", np.sqrt(1.0/2.0))]),

    MappingRule("M+180", [("M+180", 1.0)]),
    MappingRule("M+180", [("M+135", np.sqrt(1.0/2.0)),
                          ("M-135", np.sqrt(1.0/2.0))]),
    MappingRule("M+180", [("M+110", np.sqrt(1.0/2.0)),
                          ("M-110", np.sqrt(1.0/2.0))]),
    MappingRule("M+180", [("M+030", np.sqrt(1.0/4.0)),
                          ("M-030", np.sqrt(1.0/4.0))]),

    MappingRule("U+000", [("U+000", 1.0)]),
    MappingRule("U+000", [("U+030", np.sqrt(1.0/2.0)), ("U-030", np.sqrt(1.0/2.0))]),
    MappingRule("U+000", [("U+045", np.sqrt(1.0/2.0)), ("U-045", np.sqrt(1.0/2.0))]),
    MappingRule("U+000", [("M+000", 1.0)]),
    MappingRule("U+000", [("M+030", np.sqrt(1.0/2.0)), ("M-030", np.sqrt(1.0/2.0))]),

    MappingRule("U+030", [("U+030", 1.0)]),
    MappingRule("U+030", [("U+045", 1.0)]),
    MappingRule("U+030", [("M+030", 1.0)]),

    MappingRule("U+045", [("U+045", 1.0)]),
    MappingRule("U+045", [("U+030", 1.0)]),
    MappingRule("U+045", [("M+030", 1.0)]),

    MappingRule("U+090", [("U+090", 1.0)]),
    MappingRule("U+090", [("U+045", np.sqrt(2.0/3.0)), ("UH+180", np.sqrt(1.0/3.0))], input_layouts=["9+10+3"]),
    MappingRule("U+090", [("U+030", np.sqrt(1.0/2.0)), ("U+110", np.sqrt(1.0/2.0))]),
    MappingRule("U+090", [("U+045", np.sqrt(1.0/2.0)), ("U+135", np.sqrt(1.0/2.0))]),
    MappingRule("U+090", [("M+090", 1.0)]),
    MappingRule("U+090", [("U+030", np.sqrt(1.0/2.0)), ("M+110", np.sqrt(1.0/2.0))]),
    MappingRule("U+090", [("M+030", np.sqrt(1.0/2.0)), ("M+110", np.sqrt(1.0/2.0))]),
    MappingRule("U+090", [("M+030", np.sqrt(1.0/2.0))]),

    MappingRule("U+110", [("U+110", 1.0)]),
    MappingRule("U+110", [("U+135", 1.0)]),
    MappingRule("U+110", [("U+045", np.sqrt(1.0/2.0)), ("UH+180", np.sqrt(1.0/2.0))]),
    MappingRule("U+110", [("M+110", 1.0)]),
    MappingRule("U+110", [("M+135", 1.0)]),
    MappingRule("U+110", [("M+030", np.sqrt(1.0/2.0))]),

    MappingRule("U+135", [("U+135", 1.0)]),
    MappingRule("U+135", [("U+110", 1.0)]),
    MappingRule("U+135", [("U+045", np.sqrt(1.0/3.0)), ("UH+180", np.sqrt(2.0/3.0))], input_layouts=["9+10+3"]),
    MappingRule("U+135", [("U+045", np.sqrt(1.0/2.0)), ("UH+180", np.sqrt(1.0/2.0))]),
    MappingRule("U+135", [("M+135", 1.0)]),
    MappingRule("U+135", [("M+110", 1.0)]),
    MappingRule("U+135", [("M+030", np.sqrt(1.0/2.0))]),

    MappingRule("U+180", [("U+180", 1.0)]),
    MappingRule("U+180", [("UH+180", 1.0)]),
    MappingRule("U+180", [("U+135", np.sqrt(1.0/2.0)), ("U-135", np.sqrt(1.0/2.0))]),
    MappingRule("U+180", [("U+110", np.sqrt(1.0/2.0)), ("U-110", np.sqrt(1.0/2.0))]),
    MappingRule("U+180", [("M+135", np.sqrt(1.0/2.0)), ("M-135", np.sqrt(1.0/2.0))]),
    MappingRule("U+180", [("M+110", np.sqrt(1.0/2.0)), ("M-110", np.sqrt(1.0/2.0))]),
    MappingRule("U+180", [("M+030", np.sqrt(1.0/4.0)), ("M-030", np.sqrt(1.0/4.0))]),

    MappingRule("UH+180", [("UH+180", 1.0)]),
    MappingRule("UH+180", [("U+180", 1.0)]),
    MappingRule("UH+180", [("U+135", np.sqrt(1.0/2.0)), ("U-135", np.sqrt(1.0/2.0))]),
    MappingRule("UH+180", [("U+110", np.sqrt(1.0/2.0)), ("U-110", np.sqrt(1.0/2.0))]),
    MappingRule("UH+180", [("M+135", np.sqrt(1.0/2.0)), ("M-135", np.sqrt(1.0/2.0))]),
    MappingRule("UH+180", [("M+110", np.sqrt(1.0/2.0)), ("M-110", np.sqrt(1.0/2.0))]),
    MappingRule("UH+180", [("M+030", np.sqrt(1.0/4.0)), ("M-030", np.sqrt(1.0/4.0))]),

    MappingRule("T+000", [("T+000", 1.0)]),
    MappingRule("T+000", [("U+045", np.sqrt(1.0/4.0)), ("U-045", np.sqrt(1.0/4.0)),
                          ("U+135", np.sqrt(1.0/4.0)), ("U-135", np.sqrt(1.0/4.0))]),
    MappingRule("T+000", [("U+030", np.sqrt(1.0/4.0)), ("U-030", np.sqrt(1.0/4.0)),
                          ("U+110", np.sqrt(1.0/4.0)), ("U-110", np.sqrt(1.0/4.0))]),
    MappingRule("T+000", [("U+045", np.sqrt(1.0/3.0)), ("U-045", np.sqrt(1.0/3.0)), ("UH+180", np.sqrt(1.0/3.0))]),
    MappingRule("T+000", [("U+045", np.sqrt(1.0/4.0)), ("U-045", np.sqrt(1.0/4.0)),
                          ("M+135", np.sqrt(1.0/4.0)), ("M-135", np.sqrt(1.0/4.0))]),
    MappingRule("T+000", [("U+030", np.sqrt(1.0/4.0)), ("U-030", np.sqrt(1.0/4.0)),
                          ("M+110", np.sqrt(1.0/4.0)), ("M-110", np.sqrt(1.0/4.0))]),
    MappingRule("T+000", [("M+030", np.sqrt(1.0/4.0)), ("M-030", np.sqrt(1.0/4.0)),
                          ("M+135", np.sqrt(1.0/4.0)), ("M-135", np.sqrt(1.0/4.0))]),
    MappingRule("T+000", [("M+030", np.sqrt(1.0/4.0)), ("M-030", np.sqrt(1.0/4.0)),
                          ("M+110", np.sqrt(1.0/4.0)), ("M-110", np.sqrt(1.0/4.0))]),
    MappingRule("T+000", [("M+030", np.sqrt(1.0/4.0)), ("M-030", np.sqrt(1.0/4.0))]),

    MappingRule("B+000", [("B+000", 1.0)]),
    MappingRule("B+000", [("M+000", 1.0)]),
    MappingRule("B+000", [("M+030", np.sqrt(1.0/2.0)), ("M-030", np.sqrt(1.0/2.0))]),

    MappingRule("B+045", [("B+045", 1.0)]),
    MappingRule("B+045", [("M+030", 1.0)]),

    MappingRule("LFE1", [("LFE1", 1.0)], input_layouts=["9+10+3", "3+7+0"], output_layouts=["9+10+3", "3+7+0"]),
    MappingRule("LFE2", [("LFE2", 1.0)], input_layouts=["9+10+3", "3+7+0"], output_layouts=["9+10+3", "3+7+0"]),

    MappingRule("LFE1", [("LFE1", np.sqrt(1.0/2.0))], input_layouts=["9+10+3", "3+7+0"]),
    MappingRule("LFE2", [("LFE1", np.sqrt(1.0/2.0))], input_layouts=["9+10+3", "3+7+0"]),

    MappingRule("LFE1", [("LFE1", 1.0)]),
]))

itu_packs = {
    "AP_00010001": "0+1+0",
    "AP_00010002": "0+2+0",
    "AP_0001000c": "0+5+0",
    "AP_00010003": "0+5+0",
    "AP_00010004": "2+5+0",
    "AP_00010005": "4+5+0",
    "AP_00010010": "4+5+1",
    "AP_00010007": "3+7+0",
    "AP_00010008": "4+9+0",
    "AP_00010009": "9+10+3",
    "AP_0001000f": "0+7+0",
    "AP_00010017": "4+7+0",
}


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

        self.allo_positions = allocentric.positions_for_layout(layout)
        self.allo_psp = point_source.configure_allocentric(layout.without_lfe)

        self._screen_edge_lock_handler = ScreenEdgeLockHandler(self.layout.screen, layout)

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

    def closest_channel_index(self, positions, position, candidates, tol):
        """Get the index of the candidate speaker closest to a given position.

        If there are multiple speakers that are considered equally close with
        respect to a given tolerance, no decision on the closest speaker
        can be made.

        Parameters:
            positions (array of (n, 3)): n speaker positions
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
            positions[candidate_position_indizes] - cart_position[np.newaxis],
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
            np.all(self.allo_positions + tol >= bounds_min, axis=1) &
            np.all(self.allo_positions - tol <= bounds_max, axis=1)
        )

    def is_lfe_channel(self, type_metadata):
        """Determine if type_metadata is an LFE channel, issuing a warning if
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
                                                               position.screenEdgeLock,
                                                               cartesian=True)

        return evolve(position,
                      bounded_X=evolve(position.bounded_X, value=X),
                      bounded_Y=evolve(position.bounded_Y, value=Y),
                      bounded_Z=evolve(position.bounded_Z, value=Z))

    def handle(self, type_metadata):
        tol = 1e-5

        block_format = type_metadata.block_format

        if isinstance(block_format.position, DirectSpeakerPolarPosition):
            psp = self.psp
            positions = self.positions
        elif isinstance(block_format.position, DirectSpeakerCartesianPosition):
            psp = self.allo_psp
            positions = self.allo_positions
        else:
            assert False, "unexpected type"

        is_lfe_channel = self.is_lfe_channel(type_metadata)

        if not is_lfe_channel and any("LFE" in l.upper() for l in block_format.speakerLabel):
            warnings.warn(
                "block {bf.id} not being treated as LFE, but has 'LFE' in a speakerLabel; "
                "use an ITU speakerLabel or audioChannelFormat frequency element instead".format(
                    bf=block_format
                )
            )

        if type_metadata.audioPackFormats is not None:
            pack = type_metadata.audioPackFormats[-1]
            if pack.is_common_definition and pack.id in itu_packs:
                itu_layout_name = itu_packs[pack.id]
                label = block_format.speakerLabel[0]
                nominal_label = self.nominal_speaker_label(label)

                for rule in rules:
                    gains = rule.apply(itu_layout_name, nominal_label, self.layout)

                    if gains is not None:
                        pv = np.zeros(self.n_channels)
                        for channel_name, gain in gains:
                            pv[self.channel_names.index(channel_name)] = gain
                        return pv

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
                positions,
                shifted_position,
                within_bounds,
                tol)

            # if we can uniquely identify the closest speaker, use it
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
            pv[~self.is_lfe] = psp.handle(position)
            return pv
