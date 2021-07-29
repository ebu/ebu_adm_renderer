Loudspeaker Layout
==================

.. py::module:: ear.core.layout

The ``ear.core.layout`` module contains data structures which represent
loudspeaker layouts. Rather than being constructed directly, these should be
created by calling :meth:`ear.core.bs2051.get_layout`, and modified to match
real-world layouts using the functionality described in `Real-world Layouts`_.

.. autoclass:: ear.core.layout.Layout
   :members:

.. autoclass:: ear.core.layout.Channel
   :members:

BS.2051 Layouts
---------------

.. autofunction:: ear.core.bs2051.get_layout

Real-world Layouts
------------------

The following functionality is used to allow a user to specify the real
position of loudspeakers in a listening room (independent of the layouts that
can be created with them), which can be used to modify :class:`.layout.Layout`
objects using :meth:`.Layout.with_real_layout`:

.. autoclass:: ear.core.layout.RealLayout
   :members:

.. autoclass:: ear.core.layout.Speaker
   :members:

.. autofunction:: ear.core.layout.load_real_layout

   See :ref:`speakers_file` for more details and examples.
