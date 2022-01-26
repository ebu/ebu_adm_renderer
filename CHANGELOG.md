# Changelog

## [2.1.0] - 2022-01-26

### Fixed
- Depth and height parameters were switched in metadata conversion. See [#26].
- Bug in channel lock priority order, which controls the loudspeaker selection when the object position is the same distance from multiple loudspeakers. See [#28].
- Screen scaling now fails explicitly in cases where it was not well-defined before, generally with extreme positions and sizes. See [#22].
- Errors with gaps at the start of metadata. See [#13].
- Rounding of times in XML writer. See [#12].
- `audioStreamFormat` referencing error messages. See [34b738a] and [04533fc].
- Improved extraData handling in BW64 reader; see [#48]

### Changed
- `DirectSpeakers` panner uses allocentric panning for Cartesian positions. See [222374a].
- Removed python 2.7 support.
- `fix_block_format_durations` parameter is deprecated, and the ADM XML parser no longer issues warnings for timing issues -- use `ear.fileio.adm.timing_fixes` for this functionality instead. See [#8].
- `--enable-block-duration-fix` performs more extensive fixes; this now fixes the following issues:
    - `audioBlockFormats` where the `rtime` plus the `duration` of one `audioBlockFormat` does not match the `rtime` of the next.
    - `interpolationTime` parameter larger than `duration`.
    - `audioBlockFormat` `rtime` plus `duration` extending past the end of the containing `audioObject`.
- Issue a warning for `DirectSpeakers` blocks with a `speakerLabel` containing `LFE` which is not detected as an LFE channel. See [#9].
- Improved warning and error output: tidier formatting, and repeated warnings are suppressed by default. See [#37].

### Added
- `loudnessMetadata` data structures, parsing and generation. See [#25].
- `ear-utils regenerate` command to re-generate AXML and CHNA chunks. See [#8].
- The `absoluteDistance` parameter is now extracted from AXML and added to the `ExtraData` structure; see [#45].
- Lots of documentation, see https://ear.readthedocs.io/

## [2.0.0] - 2019-05-22

Changes for ITU ADM renderer reference code.

- Changes to rendering of Objects specified using Cartesian parameters.
- Added conversion between Cartesian and polar Objects parameters.
- Changed to BSD-Clear license.

## [1.2.0] - 2019-05-22

### Fixed
- Slightly non-normalised gains in extent panner.

### Changed
- Improved downmix/upmix behaviour for DirectSpeakers content specified using
  the common definitions.
- Change default azimuth of M+-SC to 15.
- Support wider azimuths for M+-SC; they may now be between 5 and 25 degrees,
  or 35 and 60 degrees.
- Removed LFE behaviour for Objects.
- Validate Cartesian and frequency information for Objects

## [1.1.2] - 2019-05-22

### Fixed
- Bug whereby NaNs could be produced in polar extent panner.

## [1.1.1] - 2019-04-12

### Fixed
- `aspectRatio` is an attribute not an element.
- Accept the `urn:ebu:metadata-schema:ebuCore_2016` namespace.
- Added default for Z coordinates.
- Various deprecation warnings.

### Added
- Specified loudspeaker positions are now checked against the allowed ranges.
- Validation of screenEdgeLock in Objects.

## [1.1.0] - 2018-11-26

### Removed
- `adm_parent` references in ADM objects.

### Added
- `Matrix` type support.
- Simple validation of ADM data model, and more extensive validation of ADM
  structures.
- Support for rendering objects with silent `audioTrackUID` references.
- Support for `audioPackFormat` HOA parameters.
- Selection of `audioProgramme` and complementary `audioObjects` from
  `ear-render`.
- `adm_path` to `RenderingItems`, with pointers to the corresponding ADM
  objects. This is not used by the renderer but is a useful feature for other
  applications built on top of the underlying ADM library.
- Support for more flexible referencing of nested `audioPackFormats`; each
  `audioTrackUID` or `chna` row can reference any appropriate `audioPackFormat`
  on the path from the root `audioPackFormat` (which contains the full set of
  `audioChannelFormats` used) to the `audioPackFormat` that contains the
  `audioChannelFormat` of the track.
- Better support for using multi-channel `audioPackFormats` -- in an
  `audioObject` or `chna`-only file using multiple `audioPackFormats` may be
  ambiguous if they share some `audioChannelFormats`. This should now be
  handled correctly in all cases.

### Changed
- The reference direction between `audioTrackFormat` and `audioStreamFormat`
  was reversed in the data model (`audioTrackFormat`s now point at a single
  `audioStreamFormat`), and `axml` references in either direction now establish
  this relationship. Note that this does not follow the exact wording in
  BS.2076-1, but this helps compatibility with other systems and should match
  future revisions of BS.2076. If either of these references are omitted a
  warning will be issued when a file is rendered. When generating BW64+ADM
  files (with `ear-utils`) both reference directions are now included.
- Complete re-implementation of `RenderingItem` selection to support other
  features in this release. This functionality was moved from
  `ear.fileio.utils` to `ear.core.select_items`.
- `RenderingItems` now use the `TrackSpec` structure rather than an index to
  point to their source audio, to allow for silent and `Matrix` tracks.

## [1.0.1] - 2018-11-23

### Changed
- An error will be raised if any `audioTrackUID` elements or CHNA rows have ID
  `ATU_00000000`, as references to these elements could be confused with silent
  `audioTrackUID` references.
- Miscellaneous improvements to testing infrastructure.

### Fixed
- When generating BW64+ADM files (with `ear-utils`), do not generate
  `audioTrackUID`s with ID `ATU_00000000`, which (as above) could be confused
  with silent `audioTrackUID` references.
- Updated use of `attrs` to fix deprecation warnings.
- Wrong imports and CHNA chunk generation in `replace_axml` command.
- Pytest warnings fixed by upgrading `pytest-datafiles` to 2.0.
- Error when testing `block_aligner` on python 3.7 with coverage enabled.
- Error in `PeakMonitor` when rendering very short files.
- `dump_chna` in binary mode on python 3.
- Padding character in axml chunk.

## 1.0.0 - 2018-03-29

Initial release.

[#8]: https://github.com/ebu/ebu_adm_renderer/pull/8
[#9]: https://github.com/ebu/ebu_adm_renderer/pull/9
[#12]: https://github.com/ebu/ebu_adm_renderer/pull/12
[#13]: https://github.com/ebu/ebu_adm_renderer/pull/13
[#22]: https://github.com/ebu/ebu_adm_renderer/pull/22
[#25]: https://github.com/ebu/ebu_adm_renderer/pull/25
[#26]: https://github.com/ebu/ebu_adm_renderer/pull/26
[#28]: https://github.com/ebu/ebu_adm_renderer/pull/28
[#37]: https://github.com/ebu/ebu_adm_renderer/pull/37
[#45]: https://github.com/ebu/ebu_adm_renderer/pull/45
[#48]: https://github.com/ebu/ebu_adm_renderer/pull/48
[34b738a]: https://github.com/ebu/ebu_adm_renderer/commit/34b738a
[04533fc]: https://github.com/ebu/ebu_adm_renderer/commit/04533fc
[222374a]: https://github.com/ebu/ebu_adm_renderer/commit/222374a
[2.1.0]: https://github.com/ebu/ebu_adm_renderer/compare/2.0.0...2.1.0
[2.0.0]: https://github.com/ebu/ebu_adm_renderer/compare/1.2.0...2.0.0
[1.2.0]: https://github.com/ebu/ebu_adm_renderer/compare/1.1.2...1.2.0
[1.1.2]: https://github.com/ebu/ebu_adm_renderer/compare/1.1.1...1.1.2
[1.1.1]: https://github.com/ebu/ebu_adm_renderer/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/ebu/ebu_adm_renderer/compare/1.0.1...1.1.0
[1.0.1]: https://github.com/ebu/ebu_adm_renderer/compare/1.0.0...1.0.1
