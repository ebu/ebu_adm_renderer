Conversion
==========

.. py:module:: ear.core.objectbased.conversion

The ``ear.core.objectbased.conversion`` module contains functionality to convert
:class:`.AudioBlockFormatObjects` objects between polar and Cartesian coordinate
conventions, according to section 10 of BS.2127-0.

Conversion functions in this module are not straightforward coordinate
conversions, they instead try to minimise the difference in behaviour between
the polar and Cartesian rendering paths.

Conversion can not account for all differences between the two rendering paths,
and while conversion of position coordinates is invertible, conversion of
extent parameters is not, except in simple cases. Because of these limitations,
conversion should be used as part of production processes, where the results
can be monitored and adjusted.

audioBlockFormat Conversion Functions
-------------------------------------

These conversions apply conversion to :class:`.AudioBlockFormatObjects` objects,
returning a new copy:

.. autofunction:: to_polar

.. autofunction:: to_cartesian

Low-Level Conversion Functions
------------------------------

These functions operate on the individual parameters, and may be useful for
testing:

.. autofunction:: point_polar_to_cart

.. autofunction:: point_cart_to_polar

.. autofunction:: extent_polar_to_cart

.. autofunction:: extent_cart_to_polar
