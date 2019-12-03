import numpy as np
import scipy.spatial
from attr import attrs, attrib, evolve
from .util import as_array, has_shape
from .geom import ngon_vertex_order, PolarPosition
from .layout import Channel
from ..options import OptionsHandler
from . import bs2051


class RegionHandler(object):
    """An interface for objects that can calculate gains for some positions,
    e.g. a triangle of loudspeakers.

    Attributes:
        output_channels (array of int): The channel numbers of the values
            returned by handle.
    """
    __slots__ = ()

    def handle(self, position):
        """Try to calculate gains for a given position.

        Args:
            position (array of 3 doubles): Cartesian source position.

        Returns:
            Array of n doubles if successful; None otherwise. The value at
            index i corresponds to the gain for channel output_channels[i], so
            if an array is returned it must have the same size as
            output_channels.
        """
        raise NotImplementedError()  # pragma: no cover

    def handle_remap(self, position, nchannels):
        """Call handle, and map the output to the channels specified in
        output_channels.

        Args:
            position (array of 3 doubles): Cartesian source position.
            nchannels (int): Size of the output array.

        Returns:
            Array of nchannels doubles if successful; None otherwise.
        """
        pv = self.handle(position)

        if pv is not None:
            out = np.zeros(nchannels)
            out[self.output_channels] = pv
            return out


@attrs(slots=True)
class Triplet(RegionHandler):
    """Region handler representing a triplet of loudspeakers, implementing VBAP.

    This is implemented such that if handle(pos) returns array x:

    - np.dot(x, positions) is collinear with pos
    = x[i] >= 0 for all i
    - norm(x) == 1

    Note that the positions are *not* normalised, as this is not always
    desirable.

    Attributes:
        output_channels: see RegionHandler.
        positions (array of (3,3) doubles): Cartesian positions of the three
            speakers; index order is speaker, axis.
    """
    output_channels = attrib(converter=as_array(dtype=int), validator=has_shape(3))
    positions = attrib(converter=as_array(dtype=float), validator=has_shape(3, 3))

    _basis = attrib(init=False, eq=False, repr=False)

    def __attrs_post_init__(self):
        self._basis = np.linalg.inv(self.positions)

    def handle(self, position):
        pv = np.dot(position, self._basis)

        epsilon = -1e-11
        if pv[0] >= epsilon and pv[1] >= epsilon and pv[2] >= epsilon:
            pv /= np.linalg.norm(pv)
            pv.clip(0, 1, out=pv)  # make sure all values are positive

            return pv


@attrs(slots=True)
class VirtualNgon(RegionHandler):
    """Region handler representing n real loudspeakers and a central virtual
    loudspeaker, whose gain is distributed to the real loudspeakers.

    Triplet regions are formed between the virtual speaker and pairs of real
    speakers on the edge of the ngon. Any gain sent to the virtual speaker is
    multiplied by centre_downmix and summed into the gains for the real
    loudspeakers,which are then normalised.

    Attributes:
        output_channels: see RegionHandler.
        positions (array of (n,3) doubles): Cartesian positions of the n
            loudspeakers.
        centre_position (array of 3 doubles): Cartesian position of the central
            virtual loudspeaker.
        centre_downmix (array of n doubles): Downmix coefficients for
            distributing gains from the centre virtual loudspeaker to the
            loudspeakers defined by positions.
    """
    output_channels = attrib(converter=as_array(dtype=int), validator=has_shape(None))
    positions = attrib(converter=as_array(dtype=float), validator=has_shape(None, 3))
    centre_position = attrib(converter=as_array(dtype=float), validator=has_shape(3))
    centre_downmix = attrib(converter=as_array(dtype=float), validator=has_shape(None))

    regions = attrib(init=False, eq=False, repr=False)

    def __attrs_post_init__(self):
        n = len(self.output_channels)
        assert n == len(self.positions) == len(self.centre_downmix)

        order = ngon_vertex_order(self.positions)

        self.regions = []
        for i in range(n):
            j = (i + 1) % n

            tri_positions = np.array([
                self.positions[order[i]],
                self.positions[order[j]],
                self.centre_position])
            tri_channels = [order[i], order[j], n]

            self.regions.append(Triplet(tri_channels, tri_positions))

    def handle(self, position):
        for region in self.regions:
            pv = region.handle_remap(position, len(self.centre_downmix) + 1)

            if pv is not None:
                # downmix the last channel containing the virtual centre
                # speaker into the real speakers, and renormalise
                pv[:-1] += pv[-1] * self.centre_downmix
                pv = pv[:-1]

                pv /= np.linalg.norm(pv)

                return pv


@attrs(slots=True)
class QuadRegion(RegionHandler):

    output_channels = attrib(converter=as_array(dtype=int), validator=has_shape(4))
    positions = attrib(converter=as_array(dtype=float), validator=has_shape(4, 3))

    order = attrib(default=None)
    pan_x = attrib(default=None)
    pan_y = attrib(default=None)

    @classmethod
    def pan_axis(cls, spk_positions):
        a, b, c, d = spk_positions

        poly = np.array([
            np.cross(b-a, c-d),
            np.cross(a, c-d) + np.cross(b-a, d),
            np.cross(a, d),
        ])

        def handle(position):
            roots = np.roots(np.dot(poly, position))

            epsillon = 1e-10
            for root in roots:
                if (np.abs(np.imag(root)) < epsillon and
                        -epsillon < np.real(root) < 1 + epsillon):
                    return np.clip(np.real(root), 0, 1)

        return handle

    def __attrs_post_init__(self):
        self.order = ngon_vertex_order(self.positions)
        self.pan_x = self.pan_axis(self.positions[self.order])
        self.pan_y = self.pan_axis(self.positions[self.order][[1, 2, 3, 0]])

    def handle(self, position):
        x = self.pan_x(position)
        y = self.pan_y(position)

        if x is None or y is None:
            return

        pvs = np.zeros(4)
        pvs[self.order] = np.array([
            (1-x) * (1-y),
            x * (1-y),
            x * y,
            (1-x) * y,
        ])

        if pvs.dot(self.positions).dot(position) <= 0:
            return

        pvs /= np.linalg.norm(pvs)

        return pvs


@attrs(slots=True)
class StereoPanDownmix(RegionHandler):
    """Stereo panning region handler.

    This implements a panning function similar to 0+5+0 with a BS.775 downmix,
    with corrected position and energy.

    Attributes:
        left_channel (int): Index of the left output channel.
        right_channel (int): Index of the right output channel.
    """
    left_channel = attrib(converter=int)
    right_channel = attrib(converter=int)

    psp = attrib(default=None)

    @property
    def output_channels(self):
        return np.array((self.left_channel, self.right_channel))

    def __attrs_post_init__(self):
        layout = bs2051.get_layout("0+5+0").without_lfe
        assert layout.channel_names == ["M+030", "M-030", "M+000", "M+110", "M-110"]

        self.psp = configure(layout)

    def handle(self, position):
        # downmix as in ITU-R BS.775, but with the centre downmix adjusted to
        # preserve the velocity vector rather than the output power
        downmix = [
            [1.0000, 0.0000, np.sqrt(3) / 3, np.sqrt(0.5), 0.0000],
            [0.0000, 1.0000, np.sqrt(3) / 3, 0.0000, np.sqrt(0.5)],
        ]

        # pan with 0+5+0, downmix and power normalise
        pv = self.psp.handle(position)
        pv_dmix = np.dot(downmix, pv)
        pv_dmix /= np.linalg.norm(pv_dmix)

        # vary the output level by the balance between the front and rear
        # loudspeakers; 0dB at the front to -3dB at the back
        front = np.max(pv[[0, 1, 2]])
        back = np.max(pv[[3, 4]])

        pv_dmix *= 0.5 ** (0.5 * back / (front + back))

        return pv_dmix


@attrs(slots=True)
class PointSourcePanner(object):
    """Wrapper around multiple regions.

    Attributes:
        regions (list of RegionHandler): Regions used to handle a position.
        num_channels (int): Number of output channels; this is computed from
            the output channels of the regions if not provided.
    """
    regions = attrib()
    num_channels = attrib(default=None)

    def _num_required_channels(self):
        return max(np.max(region.output_channels) for region in self.regions) + 1

    def __attrs_post_init__(self):
        if self.num_channels is None:
            self.num_channels = self._num_required_channels()
        else:
            assert self.num_channels >= self._num_required_channels(), "not enough channels"

    def handle(self, position):
        """Calculate gains for position using one of self.regions.

        Args:
            position (array of 3 doubles): Cartesian source position.

        Returns:
            Array of self.num_channels doubles if a region was found to handle
            this position; None otherwise.
        """
        for region in self.regions:
            pv = region.handle_remap(position, self.num_channels)
            if pv is not None:
                return pv


@attrs(slots=True)
class PointSourcePannerDownmix(object):
    """Wrapper around a point source panner with an additional downmix.

    Attributes:
        psp (PointSourcePanner): Inner point source panner.
        downmix (array of (n,m)): Downmix matrix from m inputs to n outputs.
    """
    psp = attrib()
    downmix = attrib()

    @property
    def num_channels(self):
        return self.downmix.shape[0]

    def handle(self, position):
        pv = self.psp.handle(position)
        if pv is not None:
            pv = np.dot(self.downmix, pv)
            pv /= np.linalg.norm(pv)
            return pv


def _configure_stereo(layout):
    """Configure a point source panner assuming an 0+2+0 layout."""
    left_channel = layout.channel_names.index("M+030")
    right_channel = layout.channel_names.index("M-030")

    panner = StereoPanDownmix(left_channel=left_channel, right_channel=right_channel)

    return PointSourcePanner([panner])


def extra_pos_vertical_nominal(layout):
    """Generate extra loudspeaker positions to fill gaps in layers.

    Args:
        layout (layout.Layout): Original layout.

    Returns:
        - list of extra channels (layout.Channel).
        - downmix matrix to mix the extra channel outputs to the real channels
    """
    extra_channels = []
    downmix = list(np.identity(len(layout.channels)))

    pos = np.rec.array([(channel.polar_nominal_position.azimuth, channel.polar_nominal_position.elevation,
                         channel.polar_position.azimuth, channel.polar_position.elevation)
                        for channel in layout.channels],
                       dtype=[("nominal_az", float), ("nominal_el", float),
                              ("real_az", float), ("real_el", float)])

    mid = (-10 <= pos.nominal_el) & (pos.nominal_el <= 10)

    layers = [(-30, -70, -10), (30, 10, 70)]
    for layer_nominal_el, layer_lb, layer_ub in layers:
        layer = (layer_lb <= pos.nominal_el) & (pos.nominal_el <= layer_ub)

        # for each loudspeaker in the mid layer that has an azimuth greater
        # than az_limit, add a virtual speaker directly above/below it at the
        # elevation of the current layer, which is downmixed directly to the
        # mid layer loudspeaker. az_limit is set to the range of azimuths in
        # the current layer, with some space added to prevent fast vertical
        # source movements when sources move horizontally. If there are no
        # channels on this layer then a copy of all mid layer speakers is made.
        if np.any(layer):
            az_range = np.max(np.abs(pos.nominal_az[layer]))
            az_limit = az_range + 40
            layer_real_el = np.mean(pos[layer].real_el)
        else:
            az_limit = 0.0
            layer_real_el = layer_nominal_el

        for mid_channel, mid_pos in zip(np.where(mid)[0], pos[mid]):
            epsilon = 1e-5
            if np.abs(mid_pos.nominal_az) >= az_limit - epsilon:
                extra_channels.append(Channel(name="extra",
                                              polar_position=PolarPosition(
                                                  azimuth=mid_pos.real_az,
                                                  elevation=layer_real_el,
                                                  distance=1.0),
                                              polar_nominal_position=PolarPosition(
                                                  azimuth=mid_pos.nominal_az,
                                                  elevation=layer_nominal_el,
                                                  distance=1.0)))
                downmix_row = np.zeros(len(layout.channels))
                downmix_row[mid_channel] = 1
                downmix.append(downmix_row)

    return extra_channels, np.array(downmix).T


def _convex_hull_facets(positions):
    """Find the convex hull of a set of positions, with coplanar triangles
    being merged into facets with any number of corners.

    Args:
        positions (array of nx3 floats): Vertex positions.

    Returns:
        list of sets of ints: Facets of the convex hull; each set represents a
            facet and contains the indices of its corners in positions.
    """
    hull = scipy.spatial.ConvexHull(positions)

    facets = []
    for tri, equation in zip(hull.simplices, hull.equations):
        for facet_eqn, facet_verts in facets:
            if np.linalg.norm(facet_eqn - equation) < 1e-5:
                facet_verts.update(tri)
                break
        else:
            facets.append((equation, set(tri)))

    return [verts for eqn, verts in facets]


def _adjacent_verts(facets, vert):
    """Find the adjacent vertices in a hull to the given vertex.

    Args:
        facets (list of sets of ints): Convex hull facets, each item represents
            a facet, with the contents of the set being its vertex indices.
        vert (int): Vertex index to find vertices adjacent to.

    Returns:
        set of ints: Vertices adjacent to `vert`.
    """
    return (set.union(*[facet_verts - set([vert])
                        for facet_verts in facets
                        if vert in facet_verts]) -
            set([vert]))


def _set_screen_speaker_nominal_positions(layout):
    """Modify layout to set the nominal positions of M+-SC; 45 degrees if they
    are wider than 30 degrees, otherwise 15. This ensures that the
    triangulation is correct for both the nominal and real loudspeaker
    positions when the ordering is changed.
    """
    if "M+SC" not in layout.channel_names:
        return layout

    def mod_channel(channel):
        if channel.name not in ("M+SC", "M-SC"):
            return channel

        old_az = channel.polar_position.azimuth
        new_azimuth = np.sign(old_az) * (45 if np.abs(old_az) > 30 else 15)
        return evolve(channel,
                      polar_nominal_position=PolarPosition(
                          azimuth=new_azimuth,
                          elevation=0.0,
                          distance=1.0))

    return evolve(layout,
                  channels=[mod_channel(channel) for channel in layout.channels])


def _check_screen_speakers(layout):
    """Check that screen loudspeakers are within allowed ranges."""
    for channel in layout.channels:
        if channel.name in ("M+SC", "M-SC"):
            abs_az = np.abs(channel.polar_position.azimuth)
            if not (5.0 <= abs_az <= 25.0
                    or 35.0 <= abs_az <= 60.0):
                raise ValueError("channel {name} has azimuth {az}, which is not "
                                 "in the allowed ranges of 5 to 25 and 35 to 60 "
                                 "degrees.".format(
                                    name=channel.name,
                                    az=channel.polar_position.azimuth,
                                ))

def _configure_full(layout):
    layout = _set_screen_speaker_nominal_positions(layout)

    # add some extra height speakers that are treated as real speakers until
    # the downmix in PointSourcePannerDownmix
    extra_channels, downmix = extra_pos_vertical_nominal(layout)
    layout_extra = evolve(layout, channels=layout.channels + extra_channels)

    # add some virtual speakers above and below that will be used as the centre
    # speaker in a virtual ngon. No upper speaker is added for layouts with
    # UH+180 as this speaker may actually be directly overhead, which may cause
    # a step in the gains wrt the source position.
    virtual_positions = [[0, 0, -1]]
    if not ("T+000" in layout.channel_names or "UH+180" in layout.channel_names):
        virtual_positions.append([0, 0, 1])

    positions_nominal = np.concatenate((layout_extra.nominal_positions, virtual_positions))
    positions_real = np.concatenate((layout_extra.norm_positions, virtual_positions))
    virtual_verts = len(layout_extra.channels) + np.arange(len(virtual_positions))

    facets = _convex_hull_facets(positions_nominal)

    # Turn the facets into regions for the point source panner.
    regions = []

    # Facets adjacent to one of the virtual speakers are turned into virtual
    # ngons, with an equal power downmix from the virtual speaker to the real
    # speakers.
    for virtual_vert in virtual_verts:
        real_verts = np.fromiter(_adjacent_verts(facets, virtual_vert), int)
        assert not set(real_verts).intersection(virtual_verts)

        regions.append(VirtualNgon(
            output_channels=real_verts,
            positions=positions_real[real_verts],
            centre_position=positions_real[virtual_vert],
            centre_downmix=np.full(len(real_verts), 1.0 / np.sqrt(len(real_verts)))
        ))

    # Facets not adjacent to virtual speakers are turned into triplets or
    # quads. In the supported layouts there are never facets with more
    # vertices.
    for facet_verts in facets:
        if facet_verts.intersection(virtual_verts):
            continue

        facet_verts = np.fromiter(facet_verts, int)
        if len(facet_verts) == 3:
            regions.append(Triplet(output_channels=facet_verts,
                                   positions=positions_real[facet_verts]))
        elif len(facet_verts) == 4:
            regions.append(QuadRegion(output_channels=facet_verts,
                                      positions=positions_real[facet_verts]))
        else:
            assert False, "facets with more than 4 vertices are not supported"

    return PointSourcePannerDownmix(PointSourcePanner(regions), downmix=downmix)


class AllocentricPanner(object):

    def __init__(self, positions):
        self.positions = positions

        self.st = self._speaker_tree(self.positions)

    def handle(self, position):
        zPlanes = self._find_planes(position[2])

        ret = np.zeros(len(self.positions))

        zGains = self._single_balance_pan(self.st[zPlanes[0]][0][0][1][2],
                                          self.st[zPlanes[1]][0][0][1][2],
                                          position[2])
        for zgain, zz in zip(zGains, zPlanes):
            yRows = AllocentricPanner._find_rows(self.st[zz], position[1])
            yGains = self._single_balance_pan(self.st[zz][yRows[0]][0][1][1],
                                              self.st[zz][yRows[1]][0][1][1],
                                              position[1])

            for ygain, yy in zip(yGains, yRows):
                xColumns = AllocentricPanner._find_columns(self.st[zz][yy], position[0])
                xGains = self._single_balance_pan(self.st[zz][yy][xColumns[0]][1][0],
                                                  self.st[zz][yy][xColumns[1]][1][0],
                                                  position[0])

                for xgain, xx in zip(xGains, xColumns):
                    ret[self.st[zz][yy][xx][0]] = zgain * ygain * xgain
        return ret

    @staticmethod
    def _single_balance_pan(minimum, maximum, value):
        if minimum == maximum:
            return (1.0, 1.0)
        if value <= minimum:
            return (0.0, 1.0)
        elif value >= maximum:
            return (1.0, 0.0)
        else:
            a = (value - minimum) / (maximum - minimum)
            aa = a * np.pi / 2.0
            return (np.cos(aa), np.sin(aa))

    def _find_planes(self, z):
        # z is smaller than z for all the channels in our layout
        if z <= self.st[0][0][0][1][2]:
            return [0, 0]

        for i, zz in enumerate(self.st):
            zPos = zz[0][0][1][2]
            if zPos == z:
                return [i, i]
            elif zPos > z:
                return [i - 1, i]

        return [len(self.st) - 1, len(self.st) - 1]

    @staticmethod
    def _find_rows(stz, y):
        # y is smaller than y for all the channels in our layout
        if y <= stz[0][0][1][1]:
            return [0, 0]

        for i, yy in enumerate(stz):
            yPos = yy[0][1][1]
            if yPos == y:
                return [i, i]
            elif yPos > y:
                return [i - 1, i]

        return [len(stz) - 1, len(stz) - 1]

    @staticmethod
    def _find_columns(stzy, x):
        # x is smaller than x for all the channels in our layout
        if x <= stzy[0][1][0]:
            return [0, 0]

        for i, xx in enumerate(stzy):
            xPos = xx[1][0]
            if xPos == x:
                return [i, i]
            elif xPos > x:
                return [i - 1, i]

        return [len(stzy) - 1, len(stzy) - 1]

    @staticmethod
    def _speaker_tree(positions):
        # This returns a 3-deep list. The inner most object is a (int, Channel).
        # where the 'int' is the index of the channel in the layout.
        # if  A = ret[az][ay][ax][1]
        # and B = ret[bz][by][bx][1]
        # then A[1][0] < B[1][0] <=> ax < bx if ay == by and az == bz
        #      A[1][1] < B[1][1] <=> ay < by if az == bz
        #      A[1][2] < B[1][2] <=> az < bz

        # [
        #   [                     z=z0
        #     [                   y=y0
        #       [CH0, CH1, CH2]
        #     ],
        #     [                   y=y1. y1>y0
        #       [CH3, CH4]
        #     ],
        #     [                   y=y2. y2>y1
        #       [CH5, CH6]
        #     ]
        #   ],
        #   []                    z=z1. z1>z0
        # ]
        ret = []

        def _zPos(zIndex):
            return ret[zIndex][0][0][1][2]

        def _yPos(zIndex, yIndex):
            return ret[zIndex][yIndex][0][1][1]

        def _xPos(zIndex, yIndex, xIndex):
            return ret[zIndex][yIndex][xIndex][1][0]

        for cc in enumerate(positions):
            index, c = cc
            inserted = False
            # Find z index
            for zi, _ in enumerate(ret):
                if _zPos(zi) == c[2]:
                    break
                elif _zPos(zi) > c[2]:
                    ret.insert(zi, [[cc]])
                    inserted = True
                    break
            else:
                ret.append([[cc]])
                inserted = True

            if inserted:
                continue

            # Find y index
            for yi, _ in enumerate(ret[zi]):
                if _yPos(zi, yi) == c[1]:
                    break
                elif _yPos(zi, yi) > c[1]:
                    ret[zi].insert(yi, [cc])
                    inserted = True
                    break
            else:
                ret[zi].append([cc])
                inserted = True

            if inserted:
                continue

            # Find x index
            for xi, _ in enumerate(ret[zi][yi]):
                if _xPos(zi, yi, xi) == c[0]:
                    assert False, "Two speakers with same location"
                elif _xPos(zi, yi, xi) > c[0]:
                    ret[zi][yi].insert(xi, cc)
                    inserted = True
                    break
            else:
                ret[zi][yi].append(cc)
                inserted = True

            assert inserted

        return ret


def configure_allocentric(layout):
    assert not any(channel.is_lfe for channel in layout.channels), \
        "lfe channel passed to point source panner"

    _check_screen_speakers(layout)

    from . import allocentric
    positions = allocentric.positions_for_layout(layout)
    return AllocentricPanner(positions)


configure_options = OptionsHandler()


def configure(layout):
    """Configure a point source panner given a loudspeaker layout.

    Args:
        layout (.layout.Layout): Loudspeaker layout.

    Returns:
        PointSourcePanner: point source panner configured to output channels in
            the same order as layout.channels.
    """
    assert not any(channel.is_lfe for channel in layout.channels), \
        "lfe channel passed to point source panner"

    _check_screen_speakers(layout)

    if layout.name == "0+2+0":
        return _configure_stereo(layout)
    else:
        return _configure_full(layout)
