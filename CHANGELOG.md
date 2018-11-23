# Changelog

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

[1.0.1]: https://github.com/ebu/ebu_adm_renderer/compare/1.0.0...1.0.1
