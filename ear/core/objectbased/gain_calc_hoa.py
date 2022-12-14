import numpy as np
from ..hoa_adapter import HOAPointSourceAdapter
from .extent import PolarExtentPanner
from .gain_calc import (
    PolarExtentHandler,
    ScreenEdgeLockHandler,
    ScreenScaleHandler,
    coord_trans,
    direct_diffuse_split,
    diverge,
)


class PolarExtentPannerHOA(PolarExtentPanner):
    def calc_pv_spread(self, position, width, height):
        ammount_spread = np.interp(max(width, height), [0, self.fade_width], [0, 1])
        ammount_point = 1.0 - ammount_spread

        pv = 0.0
        if ammount_point > 1e-10:
            pv += ammount_point * self.panning_func(position)
        if ammount_spread > 1e-10:
            width = np.maximum(width, self.fade_width / 2)
            height = np.maximum(height, self.fade_width / 2)

            weight_f = self.get_weight_func(position, width, height)
            spread_pvs = self.spreading_panner.panning_values_for_weight(weight_f)
            spread_pvs /= spread_pvs[0]  # normalise based on omni channel
            pv += ammount_spread * spread_pvs

        return pv


class PolarExtentHandlerHOA(PolarExtentHandler):
    def __init__(self, point_source_panner):
        self.polar_extent_panner = PolarExtentPannerHOA(point_source_panner.handle)

    def handle(self, position, width, height, depth):
        """Calculate loudspeaker gains given position and extent parameters.

        Parameters:
            position (array of length 3): Cartesian source position
            width (float): block format width parameter
            height (float): block format height parameter
            depth (float): block format depth parameter
        Returns:
            gain (array of length n): loudspeaker gains of length
            self.point_source_panner.num_channels.
        """
        distance = np.linalg.norm(position)

        if depth != 0:
            distances = np.array([distance + depth / 2.0, distance - depth / 2.0])
            distances[distances < 0] = 0.0
        else:
            distances = [distance]

        pvs = [
            self.polar_extent_panner.calc_pv_spread(
                position,
                self.extent_mod(width, end_distance),
                self.extent_mod(height, end_distance),
            )
            for end_distance in distances
        ]

        if len(pvs) == 1:
            return pvs[0]
        else:
            return np.mean(pvs, axis=0)


class GainCalcHOA(object):
    def __init__(self, layout):
        self.point_source_panner = HOAPointSourceAdapter.build(layout)
        self.screen_edge_lock_handler = ScreenEdgeLockHandler(
            layout.screen, layout.without_lfe
        )
        self.screen_scale_handler = ScreenScaleHandler(
            layout.screen, layout.without_lfe
        )
        self.polar_extent_panner = PolarExtentHandlerHOA(self.point_source_panner)

    def render(self, object_meta):
        block_format = object_meta.block_format

        position = coord_trans(block_format.position)

        position = self.screen_scale_handler.handle(
            position,
            block_format.screenRef,
            object_meta.extra_data.reference_screen,
            block_format.cartesian,
        )

        position = self.screen_edge_lock_handler.handle_vector(
            position, block_format.position.screenEdgeLock, block_format.cartesian
        )

        if block_format.cartesian:
            raise RuntimeError(
                "HOA rendering is not defined for Cartesian coordinates; perhaps use conversion"
            )
        else:
            extent_pan = self.polar_extent_panner.handle

        diverged_gains, diverged_positions = diverge(
            position, block_format.objectDivergence, block_format.cartesian
        )

        gains_for_each_pos = np.apply_along_axis(
            extent_pan,
            1,
            diverged_positions,
            block_format.width,
            block_format.height,
            block_format.depth,
        )

        gains = np.dot(diverged_gains, gains_for_each_pos)

        gains = np.nan_to_num(gains)

        gains *= block_format.gain

        return direct_diffuse_split(gains, block_format.diffuse)
