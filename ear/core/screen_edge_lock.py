from .geom import azimuth, elevation, cart
from .screen_common import PolarEdges, compensate_position
from .objectbased.conversion import point_cart_to_polar, point_polar_to_cart
import numpy as np


class ScreenEdgeLockHandler(object):

    def __init__(self, reproduction_screen, layout):
        self.layout = layout
        self.rep_screen_edges = (PolarEdges.from_screen(reproduction_screen)
                                 if reproduction_screen is not None
                                 else None)

    def lock_to_screen_edge(self, az, el, screen_edge_lock):
        if screen_edge_lock.horizontal == 'left':
            az = self.rep_screen_edges.left_azimuth
        if screen_edge_lock.horizontal == 'right':
            az = self.rep_screen_edges.right_azimuth
        if screen_edge_lock.vertical == 'top':
            el = self.rep_screen_edges.top_elevation
        if screen_edge_lock.vertical == 'bottom':
            el = self.rep_screen_edges.bottom_elevation

        return az, el

    def should_modify_position(self, screen_edge_lock):
        return (self.rep_screen_edges is not None and
                (screen_edge_lock.horizontal is not None or
                 screen_edge_lock.vertical is not None))

    def handle_vector(self, position, screen_edge_lock, cartesian=False):
        if self.should_modify_position(screen_edge_lock):
            if cartesian:
                az, el, distance = point_cart_to_polar(*position)
                new_az, new_el = self.lock_to_screen_edge(az, el, screen_edge_lock)
                comp_az, comp_el = compensate_position(new_az, new_el, self.layout)
                return point_polar_to_cart(comp_az, comp_el, distance)
            else:
                az, el, distance = azimuth(position), elevation(position), np.linalg.norm(position)
                new_az, new_el = self.lock_to_screen_edge(az, el, screen_edge_lock)
                return cart(new_az, new_el, distance)
        else:
            return position

    def handle_az_el(self, az, el, screen_edge_lock):
        if self.should_modify_position(screen_edge_lock):
            return self.lock_to_screen_edge(az, el, screen_edge_lock)
        else:
            return az, el
