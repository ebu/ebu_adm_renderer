Usage
=====

Command-Line Tools
------------------

The EAR reference implementation comes with two command line tools:

|ear-render|_
    Is the main tool to render BW64/ADM audio files

|ear-utils|_
    Collection of useful ADM utilities

.. |ear-render| replace:: ``ear-render``
.. |ear-utils| replace:: ``ear-utils``

.. _ear-render:

``ear-render``
~~~~~~~~~~~~~~

To render an ADM file, the following three parameters must be given:

- ``-s`` followed by the target output format to render to
- the name of the input file
- the name of the output file

For example, ``ear-render -s 0+5+0 input.wav output_surround.wav`` will render
the BW64/ADM file ``input.wav`` to a ``0+5+0`` target speaker layout and store
the result in ``output_surround.wav``.

.. argparse::
   :module: ear.cmdline.render_file
   :func: make_parser
   :prog: ear-render
   :nodescription:

   -l, --layout
       See speakers_file_.

.. _ear-utils:

``ear-utils``
~~~~~~~~~~~~~

The ``ear-utils`` command contains a collection of utilities for working with
ADM files as sub-commands.

.. argparse::
   :module: ear.cmdline.utils
   :func: make_parser
   :prog: ear-utils

   --screen
       See speakers_file_.

.. _speakers_file:

Speakers File Format
--------------------

Information about the loudspeaker layout can be passed to the renderer
by using a speakers file with the ``--speakers`` flag.

File Format
~~~~~~~~~~~

A speakers file is a `YAML <https://en.wikipedia.org/wiki/YAML>`__
document, which contains a list of loudspeakers under the ``speakers``
key, and the screen information under the ``screen`` key. Either may be
omitted if not required.

Speakers list
^^^^^^^^^^^^^

The top level ``speakers`` item should contain a sequence of mappings,
one for each output loudspeaker.

Each mapping should look something like this:

.. code:: yaml

   - {channel: 7, names: M+000, position: {az: 0.0, el: 0.0, r: 2.0 }}

which defines a loudspeaker connected to channel 7 (zero based),
assigned to M+000 (in bs.2051 terms), with a given position. The file
should contain a sequence of lines as above; one line per speaker.

The possible keys are as follows:

``channel`` (required)
    The zero-based output channel number.

``names`` (required)
    A list (or a single string) of BS.2051 channel names that this speaker
    should handle, i.e. like ``M+000`` or ``[U+180, UH+180]``.

``position`` (optional)
    A mapping containing the real loudspeaker position, with keys ``az``,
    ``el`` and ``r`` specifying the azimuth, elevation and distance of the
    loudspeaker in ADM angle format (anticlockwise azimuth, degrees) and
    metres.

``gain_linear`` (optional)
    A linear gain to apply to this output channel; this is useful for LFE
    outputs.

Screen
^^^^^^

The top level ``screen`` item should contain a mapping, with at least a
``type`` key, and the following options, depending on the type. If the
screen key is omitted, the default polar screen position specified in
BS.2076-1 will be assumed. If a null screen is specified, then
screen-related processing will not be applied.

if ``type == "polar"``
''''''''''''''''''''''

``aspectRatio`` (required)
    Screen width divided by screen height

``centrePosition`` (required)
    Polar position of the centre of the screen, in the same format as the
    speaker ``position`` attribute.

``widthAzimuth`` (required)
    Width of the screen in degrees.

if ``type == "cart"``
'''''''''''''''''''''

``aspectRatio`` (required)
    Screen width divided by screen height

``centrePosition`` (required)
    Cartesian position of the centre of the screen; a mapping with keys ``X``,
    ``Y`` and ``Z``.

``widthX`` (required)
    Width of the screen in Cartesian coordinates.

Examples
~~~~~~~~

Useful speakers files should be stored in ``ear/doc/speakers_files/``.

A minimal example with a polar screen would look like:

.. code:: yaml

   speakers:
       - {channel: 0, names: M+030, position: {az: 30.0, el: 0.0, r: 2.0 }}
       - {channel: 1, names: M-030, position: {az: -30.0, el: 0.0, r: 2.0 }}
   screen:
       type: polar
       aspectRatio: 1.78
       centrePosition: {az: 0.0, el: 0.0, r: 1.0}
       widthAzimuth: 58.0

A minimal example with a Cartesian screen would look like:

.. code:: yaml

   speakers:
       - {channel: 0, names: M+030, position: {az: 30.0, el: 0.0, r: 2.0 }}
       - {channel: 1, names: M-030, position: {az: -30.0, el: 0.0, r: 2.0 }}
   screen:
       type: cart
       aspectRatio: 1.78
       centrePosition: {X: 0.0, Y: 1.0, Z: 0.0}
       widthX: 0.5

A minimal example with screen processing disabled:

.. code:: yaml

   speakers:
       - {channel: 0, names: M+030, position: {az: 30.0, el: 0.0, r: 2.0 }}
       - {channel: 1, names: M-030, position: {az: -30.0, el: 0.0, r: 2.0 }}
   screen: null

