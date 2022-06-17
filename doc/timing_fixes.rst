Timing Fixes
============

.. py:module:: ear.fileio.adm.timing_fixes

This module contains functions which can be used to fix common timing issues in
ADM files. Generally these are caused by rounding of `start`, `rtime` and
`duration` parameters.

The following timing issues are addressed:

- `audioBlockFormats` where the `rtime` plus the `duration` of one
  `audioBlockFormat` does not match the `rtime` of the next.

- `interpolationTime` parameter larger than `duration`.

- `audioBlockFormat` `rtime` plus `duration` extending past the end of the
  containing `audioObject`.

.. autofunction:: check_blockFormat_timings

.. autofunction:: fix_blockFormat_timings
