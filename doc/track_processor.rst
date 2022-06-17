Track Processor
===============

.. py:module:: ear.core.track_processor

The ``ear.core.track_processor`` module can be used to render :ref:`track
specs`. Users should create a :class:`TrackProcessorBase` via
:func:`TrackProcessor`, which can be used to extract a single channel of audio
from a multi-channel bus.

:class:`MultiTrackProcessor` allows for processing multiple tracks at once.

.. autoclass:: ear.core.track_processor.TrackProcessorBase
   :members:

.. autofunction:: ear.core.track_processor.TrackProcessor

.. autoclass:: ear.core.track_processor.MultiTrackProcessor
   :members:
