# Changelog

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

[1.1.1]: https://github.com/ebu/ebu_adm_renderer/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/ebu/ebu_adm_renderer/compare/1.0.1...1.1.0
[1.0.1]: https://github.com/ebu/ebu_adm_renderer/compare/1.0.0...1.0.1
