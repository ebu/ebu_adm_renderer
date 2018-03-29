import numpy as np


class ZoneExclusionDownmix(object):
    """Calculate downmix coefficients to route output away from a given set of
    loudspeakers.

    For each channel, this stores a list of groups of other channels, sorted in
    priority order. The downmix matrix generated is such that the energy from
    each excluded channel is distributed between the non-excluded channels in
    the highest priority group containing at least one non-excluded channel.

    See calc_key in __init__ for the determination of the priority of each
    channel, and therefore the overall behaviour.
    """

    def __init__(self, layout):
        assert not any(channel.is_lfe for channel in layout.channels), \
            "lfe channel passed to zone exclusion panner"

        self.layout = layout
        self.num_channels = len(self.layout.channels)

        epsilon = 1e-6

        def sign(x):
            """sign function with some tolerance around zero"""
            if x > epsilon:
                return 1
            elif x < -epsilon:
                return -1
            else:
                return 0

        # priority when moving between layers; prefer to move up before down
        layer_prio = np.array([[0, 1, 2, 3],  # B
                               [3, 0, 1, 2],  # M
                               [3, 2, 0, 1],  # U
                               [3, 2, 1, 0]]  # T
                              )

        def layer(channel):
            """layer number of a channel"""
            elevation = channel.polar_nominal_position.elevation

            if elevation < -10:
                return 0
            elif elevation < 10:
                return 1
            elif elevation < 75:
                return 2
            else:
                return 3

        def unique_groups(groups):
            """turn a list of (key, value) with duplicate keys into a list of
            (key, [value]) with unique keys; keys are tuples and are compared
            with some tolerance
            """
            uniq_groups = []
            for key, value in groups:
                for group_key, group_channels in uniq_groups:
                    if all(np.abs(key_item - group_key_item) < epsilon
                           for key_item, group_key_item in zip(key, group_key)):
                        group_channels.append(value)
                        break
                else:
                    uniq_groups.append((key, [value]))

            return uniq_groups

        def ordered_values(groups):
            """turn a list of (key, [value]) into a list of [value] sorted by key"""
            return [np.array(values)
                    for _key, values
                    in sorted(groups, key=lambda group: group[0])]

        def calc_key(from_channel, to_channel):
            """calculate a key for this channel; channels with a lower key
            (lexicographically) have a higher priority. If two channels
            have the same key, then the energy may be split between them
            """
            # prefer channels on the same layer (see layer_prio above)
            layer_priority = layer_prio[layer(from_channel), layer(to_channel)]

            # prefer to keep sources behind/in front of the listener; this
            # results in less extreme front/back movement when one side
            # (left/right) is excluded
            front_back_change = np.abs(sign(from_channel.nominal_position[1]) - sign(to_channel.nominal_position[1]))

            # prefer closer speakers
            cart_dist = np.linalg.norm(from_channel.nominal_position - to_channel.nominal_position)

            # break ties by the front/back distance; this eliminates
            # splitting that is not symmetrical around +x or +y
            front_back_dist = np.abs(from_channel.nominal_position[1] - to_channel.nominal_position[1])

            return (layer_priority, front_back_change, cart_dist, front_back_dist)

        self.channel_groups = []
        for i, from_channel in enumerate(layout.channels):
            groups = [(calc_key(from_channel, to_channel), j)
                      for j, to_channel in enumerate(layout.channels)]

            uniq_groups = unique_groups(groups)
            channel_groups_for_i = ordered_values(uniq_groups)
            assert channel_groups_for_i[0] == [i], "channel should always be mapped to itself if possible"

            self.channel_groups.append(channel_groups_for_i)

    def downmix_for_excluded(self, excluded):
        """Calculate a downmix matrix for a given set of excluded channels.

        Parameters:
            excluded (array of n bool): If excluded[i], channel i is excluded.

        Returns:
            array of (n, n): Downmix matrix. M[i,j] is the coefficient from
                channel i to channel j.
        """
        excluded = np.asarray(excluded, dtype=bool)
        assert excluded.shape == (self.num_channels,)

        if np.all(excluded) or np.all(~excluded):
            return np.eye(self.num_channels)

        downmix = np.zeros((self.num_channels, self.num_channels))

        for i, groups in enumerate(self.channel_groups):
            for group in groups:
                if not np.all(excluded[group]):
                    not_excluded = group[~excluded[group]]
                    downmix[i, not_excluded] = 1.0 / len(not_excluded)
                    break
            else:
                assert False  # pragma: no cover

        return downmix


def show_downmix(layout, downmix):
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Line3DCollection
    import mpl_toolkits.mplot3d.art3d  # noqa
    import itertools
    from .geom import cart

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d', aspect="equal")

    props_iter = itertools.cycle(plt.rcParams["axes.prop_cycle"])

    for in_channel, downmix_row in enumerate(downmix):
        if np.any(downmix_row[np.arange(len(downmix_row)) != in_channel]):
            props = next(props_iter)
        else:
            props = dict(color="#606060")

        elevation = layout.channels[in_channel].polar_nominal_position.elevation
        if elevation > 70:
            marker = '*'
        elif elevation > 10:
            marker = '^'
        elif elevation > -10:
            marker = 'o'
        else:
            marker = 'v'

        ax.scatter3D(*layout.channels[in_channel].nominal_position, s=50, alpha=0.7, marker=marker, **props)

        lines = Line3DCollection([[layout.channels[in_channel].norm_position,
                                   layout.channels[out_channel].norm_position]
                                  for out_channel, coeff in enumerate(downmix_row)
                                  if coeff != 0.0],
                                 **props)
        ax.add_collection3d(lines)

    # draw layer rings
    elevations = {channel.polar_nominal_position.elevation for channel in layout.channels}
    el_lines = Line3DCollection([cart(np.linspace(0, 360, 200), el, 1)
                                 for el in elevations],
                                color="#000000", alpha=0.2)
    ax.add_collection3d(el_lines)

    ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_zlim(-1, 1)
    ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")

    ax.view_init(elev=30, azim=-55)
    return fig, ax
