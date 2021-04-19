from .geom import azimuth, elevation, cart
from .objectbased.conversion import point_cart_to_polar, point_polar_to_cart
import numpy as np
from .screen_common import PolarEdges, compensate_position
from .util import interp_sorted


class PolarScreenScaler(object):
    """Modifies the azimuth and elevation of a position independently,
    preserving the distance:

    - azimuth is interpolated between the screen edges and +-180
    - elevation is interpolated between the screen edges and +-90
    """

    def __init__(self, reference_screen, reproduction_screen):
        self.ref_screen_edges = PolarEdges.from_screen(reference_screen)
        self.rep_screen_edges = PolarEdges.from_screen(reproduction_screen)

    def scale_az_el(self, az, el):
        new_az = interp_sorted(az,
                               (-180, self.ref_screen_edges.right_azimuth, self.ref_screen_edges.left_azimuth, 180),
                               (-180, self.rep_screen_edges.right_azimuth, self.rep_screen_edges.left_azimuth, 180))
        new_el = interp_sorted(el,
                               (-90, self.ref_screen_edges.bottom_elevation, self.ref_screen_edges.top_elevation, 90),
                               (-90, self.rep_screen_edges.bottom_elevation, self.rep_screen_edges.top_elevation, 90))

        return new_az, new_el

    def scale_position(self, position):
        az, el, distance = azimuth(position), elevation(position), np.linalg.norm(position)
        new_az, new_el = self.scale_az_el(az, el)
        return cart(new_az, new_el, distance)


class ScreenScaleHandler(object):

    def __init__(self, reproduction_screen, layout):
        self.reproduction_screen = reproduction_screen
        self.layout = layout

    def handle(self, position, screenRef, reference_screen, cartesian):
        if screenRef and self.reproduction_screen is not None:
            scaler = PolarScreenScaler(reference_screen, self.reproduction_screen)

            if cartesian:
                az, el, distance = point_cart_to_polar(*position)
                scaled_az, scaled_el = scaler.scale_az_el(az, el)
                comp_az, comp_el = compensate_position(scaled_az, scaled_el, self.layout)
                return point_polar_to_cart(comp_az, comp_el, distance)
            else:
                return scaler.scale_position(position)
        else:
            return position
