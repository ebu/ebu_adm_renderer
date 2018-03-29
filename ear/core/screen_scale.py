from .geom import azimuth, elevation, cart
import numpy as np
from .screen_common import PolarEdges


class PolarScreenScaler(object):
    """Modifies the azimuth and elevation of a position independently,
    preserving the distance:

    - azimuth is interpolated between the screen edges and +-180
    - elevation is interpolated between the screen edges and +-90
    """

    def __init__(self, reference_screen, reproduction_screen):
        self.ref_screen_edges = PolarEdges.from_screen(reference_screen)
        self.rep_screen_edges = PolarEdges.from_screen(reproduction_screen)

    def scale_position(self, position):
        az, el, distance = azimuth(position), elevation(position), np.linalg.norm(position)

        new_az = np.interp(az,
                           (-180, self.ref_screen_edges.right_azimuth, self.ref_screen_edges.left_azimuth, 180),
                           (-180, self.rep_screen_edges.right_azimuth, self.rep_screen_edges.left_azimuth, 180))
        new_el = np.interp(el,
                           (-90, self.ref_screen_edges.bottom_elevation, self.ref_screen_edges.top_elevation, 90),
                           (-90, self.rep_screen_edges.bottom_elevation, self.rep_screen_edges.top_elevation, 90))

        return cart(new_az, new_el, distance)


class ScreenScaleHandler(object):

    def __init__(self, reproduction_screen):
        self.reproduction_screen = reproduction_screen

    def handle(self, position, screenRef, reference_screen):
        if screenRef and self.reproduction_screen is not None:
            return PolarScreenScaler(reference_screen, self.reproduction_screen).scale_position(position)
        else:
            return position
