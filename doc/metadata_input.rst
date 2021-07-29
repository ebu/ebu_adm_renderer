.. _metadata input:

Metadata Input
==============

.. py:module:: ear.core.metadata_input

The data structures in the ``ear.core.metadata_input`` module act as the main
interface between the core renderer classes for each type, and the wider EAR
system, or other systems which want to render audio using the EAR.

The data structures are *not ADM*: they are essentially a simplified view of
ADM data containing only the parts required for rendering: an association
between some input audio tracks, and streams of time-varying metadata to apply
to them.

The input to a renderer is a list of :class:`RenderingItem` objects, which are
specialised for each ADM type (:class:`ObjectRenderingItem`,
:class:`DirectSpeakersRenderingItem` etc.). Each rendering item contains:

- A pointer to some audio data, through a :class:`TrackSpec` object. This
  generally says something like "track 2 of the input audio stream", but can
  also contain a more complex mapping for Matrix types, or reference a silent
  input.

  In the case of HOA where multiple tracks are rendered together, multiple
  track specs are given.

  See :ref:`track specs`.

- A source of time-varying metadata, provided by a :class:`MetadataSource`.
  This can be used to access a sequence of :class:`TypeMetadata` objects, which
  are again sub-classed for each ADM type (:class:`ObjectTypeMetadata`,
  :class:`DirectSpeakersTypeMetadata` etc.).

  :class:`TypeMetadata` sub-classes generally contain a pointer to the
  corresponding audioBlockFormat data, as well as any extra data from outside
  the audioBlockFormat which is needed for rendering.

- Extra data (generally :class:`ImportanceData` and :class:`ADMPath`) which is
  not required for rendering, but may be useful for debugging, or uses other
  than straightforward rendering (for example only rendering some sub-set of an
  ADM file).

The available classes and their inheritance relationships are shown below:

.. inheritance-diagram::
   TypeMetadata ObjectTypeMetadata DirectSpeakersTypeMetadata HOATypeMetadata
   RenderingItem ObjectRenderingItem DirectSpeakersRenderingItem HOARenderingItem
   TrackSpec DirectTrackSpec SilentTrackSpec MatrixCoefficientTrackSpec MixTrackSpec
   :parts: 1


Overall Structure
-----------------

.. autoclass:: ear.core.metadata_input.RenderingItem

.. autoclass:: ear.core.metadata_input.TypeMetadata

.. autoclass:: ear.core.metadata_input.MetadataSource
   :members:

.. _track specs:

Track Specs
-----------

To render track specs, see :func:`ear.core.track_processor.TrackProcessor` and
:class:`ear.core.track_processor.MultiTrackProcessor`.

.. autoclass:: ear.core.metadata_input.TrackSpec
   :members:

.. autoclass:: ear.core.metadata_input.DirectTrackSpec
   :members:
   :show-inheritance:

.. autoclass:: ear.core.metadata_input.SilentTrackSpec
   :members:
   :show-inheritance:

.. autoclass:: ear.core.metadata_input.MatrixCoefficientTrackSpec
   :members:
   :show-inheritance:

.. autoclass:: ear.core.metadata_input.MixTrackSpec
   :members:
   :show-inheritance:

Objects
-------

.. autoclass:: ear.core.metadata_input.ObjectTypeMetadata
   :members:
   :show-inheritance:

.. autoclass:: ear.core.metadata_input.ObjectRenderingItem
   :members:
   :show-inheritance:

Direct Speakers
---------------

.. autoclass:: ear.core.metadata_input.DirectSpeakersTypeMetadata
   :members:
   :show-inheritance:

.. autoclass:: ear.core.metadata_input.DirectSpeakersRenderingItem
   :members:
   :show-inheritance:

HOA
---

.. autoclass:: ear.core.metadata_input.HOATypeMetadata
   :members:
   :show-inheritance:

.. autoclass:: ear.core.metadata_input.HOARenderingItem
   :members:
   :show-inheritance:

Shared Data
-----------

.. autoclass:: ear.core.metadata_input.ExtraData
   :members:

.. autoclass:: ear.core.metadata_input.ADMPath
   :members:

.. autoclass:: ear.core.metadata_input.ImportanceData
   :members:
