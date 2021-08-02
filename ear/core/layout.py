from __future__ import print_function
from attr import attrs, attrib, evolve, Factory
from attr.validators import instance_of, optional
import numpy as np
import sys
from .geom import CartesianPosition, PolarPosition, inside_angle_range
from ..common import list_of, CartesianScreen, PolarScreen, default_screen
from ..compatibility import load_yaml


def to_polar_position(pp):
    """Conform pp from a tuple to a PolarPosition."""
    if isinstance(pp, PolarPosition):
        return pp
    else:
        return PolarPosition(*pp)


def _print_warning(message):
    """Print a warning to stderr."""
    print(message, file=sys.stderr)  # noqa


@attrs(frozen=True, slots=True)
class Channel(object):
    """Representation of a channel, with a name, real and nominal positions,
    allowed azimuth and elevation ranges, and an lfe flag.

    Attributes:
        name (str): Channel name.
        polar_position (PolarPosition, or arguments for PolarPosition):
            real speaker location
        polar_nominal_position (PolarPosition, or arguments for PolarPosition):
            nominal speaker location, defaults to polar_position
        az_range (2-tuple of floats):
            azimuth range in degrees; allowed range is interpreted as
            starting at az_range[0], moving anticlockwise to az_range[1];
            defaults to the azimuth of polar_nominal_position.
        el_range (2-tuple of floats):
            elevation range in degrees; allowed range is interpreted as
            starting at el_range[0], moving up to el_range[1]; defaults to
            the elevation of polar_nominal_position.
        is_lfe (bool): is this an LFE channel?
    """

    name = attrib(converter=str)
    polar_position = attrib(converter=to_polar_position)
    polar_nominal_position = attrib(converter=to_polar_position,
                                    default=Factory(lambda self: self.polar_position,
                                                    takes_self=True))
    az_range = attrib(default=Factory(lambda self: (self.polar_nominal_position.azimuth,
                                                    self.polar_nominal_position.azimuth),
                                      takes_self=True))
    el_range = attrib(default=Factory(lambda self: (self.polar_nominal_position.elevation,
                                                    self.polar_nominal_position.elevation),
                                      takes_self=True))
    is_lfe = attrib(default=False, converter=bool)

    @property
    def position(self):
        return self.polar_position.as_cartesian_array()

    @property
    def norm_position(self):
        return self.polar_position.norm_position

    @property
    def nominal_position(self):
        return self.polar_nominal_position.as_cartesian_array()

    def check_position(self, callback=_print_warning):
        """Call callback with an error message if the position is outside the
        azimuth and elevation ranges.
        """
        if not inside_angle_range(self.polar_position.azimuth, *self.az_range):
            callback("{name}: azimuth {azimuth} out of range {az_range}.".format(name=self.name,
                                                                                 azimuth=self.polar_position.azimuth,
                                                                                 az_range=self.az_range))
        if not self.el_range[0] <= self.polar_position.elevation <= self.el_range[1]:
            callback("{name}: elevation {elevation} out of range {el_range}.".format(name=self.name,
                                                                                     elevation=self.polar_position.elevation,
                                                                                     el_range=self.el_range))


@attrs(frozen=True, slots=True)
class Layout(object):
    """Representation of a loudspeaker layout, with a name and a list of channels.

    Attributes:
        name (str): layout name
        channels (list[Channel]): list of channels in the layout
        screen (Optional[Union[CartesianScreen, PolarScreen]]): screen
            information to use for screen-related content
    """
    name = attrib()
    channels = attrib()
    screen = attrib(validator=optional(instance_of((CartesianScreen, PolarScreen))),
                    default=default_screen)

    @property
    def positions(self):
        """Channel positions as an (n, 3) numpy array."""
        return np.array([channel.position for channel in self.channels])

    @property
    def norm_positions(self):
        """Normalised channel positions as an (n, 3) numpy array."""
        return np.array([channel.norm_position for channel in self.channels])

    @property
    def nominal_positions(self):
        """Nominal channel positions as an (n, 3) numpy array."""
        return np.array([channel.nominal_position for channel in self.channels])

    @property
    def without_lfe(self):
        """Layout: The same layout, without LFE channels."""
        return evolve(self, channels=[channel for channel in self.channels if not channel.is_lfe])

    @property
    def is_lfe(self):
        """Bool array corresponding to channels that selects LFE channels."""
        return np.array([channel.is_lfe for channel in self.channels])

    @property
    def channel_names(self):
        """list[str]: The channel names for each channel."""
        return [channel.name for channel in self.channels]

    @property
    def channels_by_name(self):
        """dict from channel name to Channel."""
        return dict((channel.name, channel) for channel in self.channels)

    def check_positions(self, callback=_print_warning):
        """Call callback with error messages for any channel positions that are out of range."""
        for channel in self.channels:
            channel.check_position(callback=callback)

    def with_speakers(self, speakers):
        """Remap speaker positions to those in speakers, and produce an upmix
        matrix to map from the channels in the layout to the channels in the
        speaker list.

        Parameters:
            speakers (list[Speaker]): list of speakers to map to.

        Returns:
            - A new Layout object with the same channels but with positions
              matching those in speakers.
            - An upmix matrix m, such that m.dot(x) will map values
              corresponding to the channels in self.channels to the channel
              numbers in speakers. This matrix may be missing entries or have
              duplicate entries depending on the contents of speakers; use
              check_upmix_matrix.
        """
        def find_speaker(name):
            for speaker in speakers:
                if name in speaker.names:
                    return speaker

        out_channels = max(speaker.channel for speaker in speakers) + 1

        new_channels = []
        upmix_matrix = np.zeros((out_channels, len(self.channels)))

        for i, channel in enumerate(self.channels):
            matching_speaker = find_speaker(channel.name)

            if matching_speaker is not None:
                upmix_matrix[matching_speaker.channel, i] = matching_speaker.gain_linear

                if matching_speaker.polar_position is not None:
                    channel = evolve(channel, polar_position=matching_speaker.polar_position)

            new_channels.append(channel)

        return evolve(self, channels=new_channels), upmix_matrix

    def with_real_layout(self, real_layout):
        """Incorporate information from a real layout.

        Note: see with_speakers for information on speaker mapping

        Parameters:
            real_layout (RealLayout): real layout information to incorporate

        Returns:
            - A new Layout object with updated speaker positions and screen
              information.
            - An upmix matrix to map the loudspeakers to the correct channels
              and apply gains.
        """
        if real_layout.speakers is not None:
            new_layout, upmix_matrix = self.with_speakers(real_layout.speakers)
        else:
            new_layout, upmix_matrix = self, np.eye(len(self.channels))

        return evolve(new_layout, screen=real_layout.screen), upmix_matrix

    def check_upmix_matrix(self, upmix, callback=_print_warning):
        """Call callback with error messages for any errors in an upmix matrix.

        - each input channel should be routed to 1 output channel
        - each output channel should be routed from 0 or 1 input channels
        """
        for channel, column in zip(self.channels, upmix.T):
            num_outputs = np.count_nonzero(column)
            if num_outputs == 0:
                callback("Channel {name} not mapped to any output.".format(name=channel.name))
            if num_outputs > 1:
                outputs = list(np.nonzero(column)[0])
                callback("Channel {name} mapped to multiple outputs: {outputs}.".format(name=channel.name,
                                                                                        outputs=outputs))

        for speaker, row in enumerate(upmix):
            num_channels = np.count_nonzero(row)
            if num_channels > 1:
                channel_names = [channel_name for channel_name, coeff
                                 in zip(self.channel_names, row) if coeff != 0.0]
                callback("Speaker idx {speaker} used by multiple channels: {channel_names}".format(speaker=speaker,
                                                                                                   channel_names=channel_names))


@attrs(frozen=True, slots=True)
class Speaker(object):
    """Representation of a real-world loudspeaker; an array of these represents the
    data required to use the renderer in a given listening room.

    Attributes:
        channel (int): 0-based channel number
        names (list[str]): list of BS.2051 channel names this speaker should handle.
        polar_position (Optional[PolarPosition]): real loudspeaker position, if known
        gain_linear (float): linear gain to apply to this output channel
    """
    channel = attrib()
    names = attrib()
    polar_position = attrib(default=None)
    gain_linear = attrib(default=1.0)


@attrs(frozen=True, slots=True)
class RealLayout(object):
    """Representation of a complete listening environment, onto which a
    standard layout will be mapped.

    Attributes:
        speakers (Optional[list[Speaker]]): all speakers that could be used
        screen (Optional[Union[CartesianScreen, PolarScreen]]): screen
            information to use for screen-related content
    """
    speakers = attrib(default=None, validator=optional(list_of(Speaker)))
    screen = attrib(validator=optional(instance_of((CartesianScreen, PolarScreen))),
                    default=default_screen)


def load_real_layout(fileobj):
    """Load a real layout from a yaml file.

    The format is either a list of objects representing speakers, or an object
    with optional keys ``speakers`` (which contains a list of objects
    representing speakers) and ``screen`` (which contains an object representing
    the screen).

    Objects representing speakers may have the following keys:

    channel
      0-based channel number, required
    names
      list (or a single string) of BS.2051 channel names that this speaker
      should handle, i.e. like ``"M+000"`` or ``["U+180", "UH+180"]``
    position
      optional associative array containing the real loudspeaker position, with keys:

      az
        anti-clockwise azimuth in degrees
      el
        elevation in degrees
      r
        radius in metres
    gain_linear
      optional linear gain to be applied to this channel

    A polar screen may be represented with the following keys:

    type
      ``"polar"``, required
    aspectRatio
      aspect ratio of the screen
    centrePosition
      object representing the centre position of the screen:

      az
        anti-clockwise azimuth in degrees
      el
        elevation in degrees
      r
        radius in metres
    widthAzimuth
      width of the screen in degrees

    A Cartesian screen may be represented with the following keys:

    type
      ``"cart"``, required
    aspectRatio
      aspect ratio of the screen
    centrePosition
      object representing the centre position of the screen containing X, Y and
      Z coordinates
    widthX
      width of the screen along the Cartesian X axis

    If the screen is omitted, the default screen is used; if the screen is
    specified but null, then screen-related processing will not be applied.

    Parameters:
        fileobj: a file-like object to read yaml from

    Returns:
        RealLayout: real layout information
    """
    def parse_yaml_polar_position(position):
        if set(position.keys()) == set(["az", "el", "r"]):
            return PolarPosition(position["az"], position["el"], position["r"])
        else:
            raise Exception("Unknown polar position format: {}".format(position))

    def parse_yaml_cart_position(position):
        if set(position.keys()) == set(["X", "Y", "Z"]):
            return CartesianPosition(position["X"], position["Y"], position["Z"])
        else:
            raise Exception("Unknown Cartesian position format: {}".format(position))

    def parse_yaml_speaker(yaml_speaker):
        names = yaml_speaker["names"]
        if not isinstance(names, list):
            names = [names]

        speaker = Speaker(channel=yaml_speaker["channel"],
                          names=names)

        if "position" in yaml_speaker:
            speaker = evolve(speaker,
                             polar_position=parse_yaml_polar_position(yaml_speaker["position"]))

        if "gain_linear" in yaml_speaker:
            speaker = evolve(speaker,
                             gain_linear=yaml_speaker["gain_linear"])

        return speaker

    def parse_yaml_screen(yaml_screen):
        if yaml_screen is None:
            return None

        screen_type = yaml_screen["type"]

        if screen_type == "polar":
            return PolarScreen(
                aspectRatio=float(yaml_screen["aspectRatio"]),
                centrePosition=parse_yaml_polar_position(yaml_screen["centrePosition"]),
                widthAzimuth=float(yaml_screen["widthAzimuth"]),
            )
        elif screen_type == "cart":
            return CartesianScreen(
                aspectRatio=float(yaml_screen["aspectRatio"]),
                centrePosition=parse_yaml_cart_position(yaml_screen["centrePosition"]),
                widthX=float(yaml_screen["widthX"]),
            )
        else:
            raise Exception("Unknown screen type: {!r}".format(screen_type))

    yaml_info = load_yaml(fileobj)

    if isinstance(yaml_info, dict):
        yaml_info_dict = yaml_info
    elif isinstance(yaml_info, list):
        yaml_info_dict = dict(speakers=yaml_info)
    else:
        raise Exception("Expected mapping or list of loudspeakers.")

    speakers = (list(map(parse_yaml_speaker, yaml_info_dict["speakers"]))
                if "speakers" in yaml_info_dict
                else None)

    screen = (parse_yaml_screen(yaml_info_dict["screen"])
              if "screen" in yaml_info_dict
              else default_screen)

    return RealLayout(speakers=speakers, screen=screen)


def load_speakers(fileobj):
    """Load a list of speakers from a yaml file.

    This is a legacy wrapper around load_real_layout; see its documentation for
    format info.

    Parameters:
        file: a file-like object to read yaml from

    Returns:
        list of Speaker
    """
    return load_real_layout(fileobj).speakers
