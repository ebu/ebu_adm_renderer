ADM Utilities
=============

.. py:module:: ear.fileio.adm
   :noindex:

.. _adm builder:

ADM Builder
-----------

The :class:`builder.ADMBuilder` class makes it easier to construct basic ADM
structures which are properly linked together. For example, to make an ADM with
a single Objects channel:

.. code-block:: python

    from ear.fileio.adm.builder import ADMBuilder
    from ear.fileio.adm.elements import AudioBlockFormatObjects, ObjectPolarPosition

    builder = ADMBuilder()

    builder.create_programme(audioProgrammeName="my audioProgramme")
    builder.create_content(audioContentName="my audioContent")

    block_formats = [
        AudioBlockFormatObjects(
            position=ObjectPolarPosition(azimuth=0.0, elevation=0.0, distance=1.0),
        ),
    ]
    builder.create_item_objects(0, "MyObject 1", block_formats=block_formats)

    # do something with builder.adm

.. autoclass:: ear.fileio.adm.builder.ADMBuilder
   :members:

ID Generation
-------------

When ADM objects are created, they have their IDs set to ``None``. Before serialisation, the IDs must be generated using :func:`generate_ids`:

.. autofunction:: ear.fileio.adm.generate_ids.generate_ids

CHNA Utilities
--------------

In a BW64 file, the AXML and CHNA chunks store overlapping and related information about audioTrackUIDs:

- track index: CHNA only
- audioTrackFormat reference: CHNA and AXML
- audioPackFormat reference: CHNA and AXML

To simplify this, the :class:`elements.AudioTrackUID` class stores the track
index from the CHNA, and we provide utilities for copying data between a CHNA
and an ADM object:

.. autofunction:: ear.fileio.adm.chna.load_chna_chunk
.. autofunction:: ear.fileio.adm.chna.populate_chna_chunk
.. autofunction:: ear.fileio.adm.chna.guess_track_indices

Common Definitions
------------------

The library includes a copy of the common definitions file, which can be loaded
into an ADM structure:

.. autofunction:: ear.fileio.adm.common_definitions.load_common_definitions
