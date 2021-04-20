# EBU ADM Renderer (EAR)

[![build status badge](https://github.com/ebu/ebu_adm_renderer/workflows/test/badge.svg)](https://github.com/ebu/ebu_adm_renderer/actions?workflow=test)

The **EBU ADM Renderer** **(*EAR*)** is a complete interpretation of the **Audio Definition Model (ADM)** format, specified in Recommendation [ITU-R BS.2076-1](https://www.itu.int/rec/R-REC-BS.2076/en). ADM is the recommended format for all stages and use cases within the scope of programme productions of **Next Generation Audio (NGA)**. This repository contains a Python reference implementation of the EBU ADM Renderer.

This Renderer implementation is capable of rendering audio signals to all reproduction systems mentioned in ["Advanced sound system for programme production (ITU-R BS.2051-1)"](https://www.itu.int/rec/R-REC-BS.2051/en).

Further descriptions of the *EAR* algorithms and functionalities can be found in [EBU Tech 3388](https://tech.ebu.ch/publications/adm-renderer-for-use-in-nga-broadcasting).

***Note: Version 2.0 of the renderer represents also the reference implementation of [ITU-R BS.2127 (ITU ADM Renderer)](https://www.itu.int/rec/R-REC-BS.2127/en)***

## Test files
A initial set of ADM files to test the *EAR* can be found under
  - https://ebu.io/qc/testmaterial and
  - http://cvssp.org/data/s3a/public/radiodrama_register.php

## Installation

To install the latest release from PyPi:

```bash
$ pip install ear
```

### Python versions

*EAR* supports Python >=3.6 and runs on all major platforms (Linux, Mac OSX,
Windows).

### Installation of extra packages

If you want to run the unit tests you can install all extra requirements with pip:
```bash
$ pip install ear[test]
```

## Getting started

The *EAR* reference implementation comes with two command line tools:

- `ear-render` Is the main tool to render BW64/ADM audio files
- `ear-utils` Collection of useful ADM utilities

### Command line renderer

```bash
usage: ear-render [-h] [-d] -s target_system [-l layout_file]
                  [--output-gain-db gain_db] [--fail-on-overload]
                  [--enable-block-duration-fix] [--programme id]
                  [--comp-object id]
                  [--apply-conversion {to_cartesian,to_polar}] [--strict]
                  input_file output_file

EBU ADM renderer

positional arguments:
  input_file
  output_file

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           print debug information when an error occurs
  -s target_system, --system target_system
                        Target output system, accoring to ITU-R BS.2051.
                        Available systems are: 0+2+0, 0+5+0, 2+5+0, 4+5+0,
                        4+5+1, 3+7+0, 4+9+0, 9+10+3, 0+7+0, 4+7+0
  -l layout_file, --layout layout_file
                        Layout config file
  --output-gain-db gain_db
                        output gain in dB (default: 0)
  --fail-on-overload, -c
                        fail if an overload condition is detected in the
                        output
  --enable-block-duration-fix
                        automatically try to fix faulty block format durations
  --programme id        select an audioProgramme to render by ID
  --comp-object id      select an audioObject by ID from a complementary group
  --apply-conversion {to_cartesian,to_polar}
                        Apply conversion to Objects audioBlockFormats before
                        rendering
  --strict              treat unknown ADM attributes as errors
```

To render an ADM file, the following three parameters must be given:
  - `-s` followed by the target output format to render to
  - the name of the input file
  - the name of the output file

For example `ear-render -s 0+5+0 input.wav output_surround.wav` will render the BW64/ADM file `input.wav` to a `0+5+0` target speaker layout and store the result in `output_surround.wav`.

The *optional* `--layout` parameter allows to specify the real loudspeaker positions and screen dimensions of a reproduction setup.
Refer to [the layout file documentation](doc/layout_file.md) for more information about its format.

`--fail-on-overload` makes the rendering process fail in case an overload in the output channels to ensure any signal clipping doesn't go unnoticed. Use `--output-gain-db` to adjust the output gain.

`--enable-block-duration-fix` automatically fixes durations of `audioBlockFormats` in case they are not continuous.
**Please note** that the proper way to handle this situation is to fix the input file.

`--strict` enables strict ADM parsing mode. Some of the currently available
ADM/BW64 files may not strictly adhere to the BS.2076 specification, for example by including xml attributes that are not part of the standard.
The default behaviour is to output a warning and continue processing.
When strict mode is enabled, warnings are turned into errors and processing is  stopped.


**Please note** that, depending on the size of the file, it may
take some time to render the file. At the time of writing, the parsing of the ADM XML data is relatively slow when the ADM is large (>= a few megabytes).

### Command line ADM utilities

The `ear-utils` command provides various subcommands which can be seen on the help message
when called with `ear-utils --help`:

Each subcommand may have its own command line options, which can be
displayed using `ear-utils SUBCOMMAND --help`, where `SUBCOMMAND` is one of the supported subcommands.

```bash
usage: ear-utils [-h]
                 {make_test_bwf,replace_axml,dump_axml,dump_chna,ambix_to_bwf}
                 ...

EBU ADM renderer utilities

optional arguments:
  -h, --help            show this help message and exit

available subcommands:
  {make_test_bwf,replace_axml,dump_axml,dump_chna,ambix_to_bwf}
    make_test_bwf       make a bwf file from a wav file and some metadata
    replace_axml        replace the axml chunk in an existing ADM BWF file
    dump_axml           dump the axml chunk of an ADM BWF file to stdout
    dump_chna           dump the chna chunk of an ADM BWF file to stdout
    ambix_to_bwf        make a BWF file from an ambix format HOA file
```

#### HOA ADM Creation
```bash
usage: ear-utils ambix_to_bwf [-h] [--norm NORM] [--nfcDist NFCDIST]
                              [--screenRef] [--chna-only]
                              input output

positional arguments:
  input              input file
  output             output BWF file

optional arguments:
  -h, --help         show this help message and exit
  --norm NORM        normalization mode
  --nfcDist NFCDIST  Near-Field Compensation Distance (float)
  --screenRef        Screen Reference
  --chna-only        use only CHNA with common definitions
```


To convert an ambiX file in an ADM one, the following two parameters must be given:
-   the name of the input file
-   the name of the output file

The optional parameters are :
-   The normalization of the signals (N3D, FuMa or SN3D, which is the default value)
-   The NFC Distance, i.e., the distance at which the HOA mix was created. A float value between 0 and 20 meters must be given.
    The default value 0 means no NFC processing.
-   The screenRef flag, which tells if the audio content is screen related or not. The default value is False, which means no screen scaling.

For example, `ear-utils ambix_to_bwf --nfcDist 2.53 input.wav output.wav` will create an ADM file called output.wav containing the audio samples of the input.wav file and the ADM metadata corresponding to an ambiX file with SN3D normalization, an 2.53 meters nfcDist, and no screen scaling.

**Please note** that the software implicitly assumes that all the HOA channels are in ACN ordering and that no channel is missing. For example, it will assumes the signal is a 4th order HOA signal if it finds 25 channels ((4+1)²=25).
