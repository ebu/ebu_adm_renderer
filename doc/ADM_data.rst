ADM Data
--------

.. py:module:: ear.fileio.adm

The ADM data representation is in the `ear.fileio.adm` module.

An ADM document is represented by an :class:`adm.ADM` object, which contains
lists of all of the top-level ADM elements.

In general, element objects have properties which match the ADM XML tag or
attribute names, except for:

- The main ID of elements are stored in an ``.id`` property, rather than (for
  example) ``.audioProgrammeID``.

- ``typeDefinition`` and ``typeLabel`` are resolved to a single ``.type``
  property.

- ``formatDefinition`` and ``formatLabel`` are resolved to a single ``.format``
  property.

- References to other objects by ID are translated into a python object
  reference, or a list of references. For example, ``audioObjectIDRef``
  elements in an ``audioContent`` tag become a list of
  :class:`elements.AudioObject` stored in
  :attr:`elements.AudioContent.audioObjects`.

  .. note::
    Element objects do contain ``IDRef`` properties (e.g.
    ``audioObjectIDRef``), which are used while parsing, but these are
    cleared when references are resolved to avoid storing conflicting
    information.

- In representations of ADM elements which contain both text and attributes
  (for example ``<objectDivergence azimuthRange="30">0.5</objectDivergence>``),
  the text part is stored in a semantically-relevant property, e.g.
  :attr:`elements.ObjectDivergence.value`. For boolean elements (e.g.
  ``channelLock``), this is represented by the presence or absence of the
  object in the parent object.

.. autoclass:: ear.fileio.adm.adm.ADM
   :members:

Top-level Elements
~~~~~~~~~~~~~~~~~~

.. autoclass:: ear.fileio.adm.elements.main_elements.ADMElement
   :members:

.. autoclass:: ear.fileio.adm.elements.AudioProgramme
   :members:

.. autoclass:: ear.fileio.adm.elements.AudioContent
   :members:

.. autoclass:: ear.fileio.adm.elements.AudioObject
   :members:

.. autoclass:: ear.fileio.adm.elements.AudioPackFormat
   :members:

.. autoclass:: ear.fileio.adm.elements.AudioChannelFormat
   :members:

.. autoclass:: ear.fileio.adm.elements.AudioTrackFormat
   :members:

.. autoclass:: ear.fileio.adm.elements.AudioStreamFormat
   :members:

.. autoclass:: ear.fileio.adm.elements.AudioTrackUID
   :members:

Common Sub-Elements
~~~~~~~~~~~~~~~~~~~

.. autoclass:: ear.fileio.adm.elements.TypeDefinition
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: ear.fileio.adm.elements.FormatDefinition
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: ear.fileio.adm.elements.LoudnessMetadata
   :members:

.. autoclass:: ear.fileio.adm.elements.Frequency
   :members:

Common Types
~~~~~~~~~~~~

.. autoclass:: ear.fileio.adm.elements.ScreenEdgeLock
   :members:

audioBlockFormat types
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: ear.fileio.adm.elements.AudioBlockFormat
   :members:

Objects audioBlockFormat
''''''''''''''''''''''''

.. autoclass:: ear.fileio.adm.elements.AudioBlockFormatObjects
   :members:
   :show-inheritance:

.. autoclass:: ear.fileio.adm.elements.CartesianZone
   :members:

.. autoclass:: ear.fileio.adm.elements.PolarZone
   :members:

.. autoclass:: ear.fileio.adm.elements.ChannelLock
   :members:

.. autoclass:: ear.fileio.adm.elements.JumpPosition
   :members:

.. autoclass:: ear.fileio.adm.elements.ObjectDivergence
   :members:

.. autoclass:: ear.fileio.adm.elements.ObjectPosition
   :members:

.. autoclass:: ear.fileio.adm.elements.ObjectPolarPosition
   :members:
   :show-inheritance:

.. autoclass:: ear.fileio.adm.elements.ObjectCartesianPosition
   :members:
   :show-inheritance:

DirectSpeakers audioBlockFormat
'''''''''''''''''''''''''''''''

.. autoclass:: ear.fileio.adm.elements.AudioBlockFormatDirectSpeakers
   :members:
   :show-inheritance:

.. autoclass:: ear.fileio.adm.elements.BoundCoordinate
   :members:

.. autoclass:: ear.fileio.adm.elements.DirectSpeakerPosition
   :members:

.. autoclass:: ear.fileio.adm.elements.DirectSpeakerPolarPosition
   :members:
   :show-inheritance:

.. autoclass:: ear.fileio.adm.elements.DirectSpeakerCartesianPosition
   :members:
   :show-inheritance:

HOA AudioBlockFormat
''''''''''''''''''''

.. autoclass:: ear.fileio.adm.elements.AudioBlockFormatHoa
   :members:
   :show-inheritance:

Matrix AudioBlockFormat
'''''''''''''''''''''''

.. autoclass:: ear.fileio.adm.elements.AudioBlockFormatMatrix
   :members:
   :show-inheritance:

.. autoclass:: ear.fileio.adm.elements.MatrixCoefficient
   :members:
