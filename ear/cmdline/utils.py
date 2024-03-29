from __future__ import print_function
import argparse
import logging
import sys
from ..compatibility import write_bytes_to_stdout
from ..fileio import openBw64
from ..fileio.bw64.chunks import ChnaChunk
import warnings
from . import ambix_to_bwf
from . import generate_test_file
from .error_handler import error_handler


logging.basicConfig()
logger = logging.getLogger("ear")


def replace_axml_command(args):
    from ..fileio.adm import xml as adm_xml
    from ..fileio.adm import chna as adm_chna

    with open(args.axml, 'rb') as axml_file:
        axml = axml_file.read()

        with openBw64(args.input) as infile:
            if args.gen_chna:
                adm = adm_xml.parse_string(axml)
                adm_chna.guess_track_indices(adm)
                chna = ChnaChunk()
                adm_chna.populate_chna_chunk(chna, adm)
            else:
                chna = infile.chna

                if chna is None:
                    warnings.warn("No CHNA information available; output will " +
                                  "not have a CHNA chunk. Either specify '-g', or use an input " +
                                  "file with a CHNA chunk.")

            with openBw64(
                args.output, "w", formatInfo=infile.formatInfo, axml=axml, chna=chna
            ) as outfile:
                while True:
                    samples = infile.read(2048)
                    if not len(samples):
                        break
                    outfile.write(samples)


def _set_axml_version(element, version_str: int):
    """find the audioFormatExtended element in element and set the version

    version_str may contain an integer or a full version number
    """
    from ..fileio.adm.xml import find_audioFormatExtended
    from ..fileio.adm.elements.version import BS2076Version, parse_version

    afe_element = find_audioFormatExtended(element)

    version_int = None
    try:
        version_int = int(version_str)
    except ValueError:
        pass

    if version_int is not None:
        version = BS2076Version(version_int)
    else:
        version = parse_version(version_str)

    afe_element.attrib["version"] = str(version)


def regenerate_command(args):
    from ..fileio.adm import xml as adm_xml
    from ..fileio.adm import chna as adm_chna
    from ..fileio.adm import timing_fixes
    from ..fileio.adm.adm import ADM
    from ..fileio.adm.chna import load_chna_chunk
    from ..fileio.adm.common_definitions import load_common_definitions
    import lxml.etree

    with openBw64(args.input) as infile:
        adm = ADM()
        load_common_definitions(adm)

        if infile.axml is not None:
            element = lxml.etree.fromstring(infile.axml)
            if args.set_version:
                _set_axml_version(element, args.set_version)

            adm_xml.load_axml_doc(adm, element)

        load_chna_chunk(adm, infile.chna)

        adm.validate()

        if args.enable_block_duration_fix:
            timing_fixes.fix_blockFormat_timings(adm)

        xml = adm_xml.adm_to_xml(adm)
        axml = lxml.etree.tostring(xml, pretty_print=True)

        chna = ChnaChunk()
        adm_chna.populate_chna_chunk(chna, adm)

        with openBw64(
            args.output, "w", formatInfo=infile.formatInfo, axml=axml, chna=chna
        ) as outfile:
            for samples in infile.iter_sample_blocks(2048):
                outfile.write(samples)


def rewrite_command(args):
    with openBw64(args.input) as infile:
        with openBw64(
            args.output,
            "w",
            formatInfo=infile.formatInfo,
            axml=infile.axml,
            chna=infile.chna,
        ) as outfile:
            while True:
                samples = infile.read(2048)
                if not len(samples):
                    break
                outfile.write(samples)


def dump_axml_command(args):
    with openBw64(args.input) as infile:
        write_bytes_to_stdout(infile.axml)

        if sys.stdout.isatty() and not infile.axml.endswith(b"\n"):
            write_bytes_to_stdout(b"\n")


def dump_chna_command(args):
    with openBw64(args.input) as infile:
        if args.binary:
            write_bytes_to_stdout(infile.get_chunk_data(b'chna'))
        else:
            for entry in infile.chna.audioIDs:
                print(entry)  # noqa


def make_parser():
    parser = argparse.ArgumentParser(description='EBU ADM renderer utilities')
    subparsers = parser.add_subparsers(title='available subcommands')

    parser.add_argument("-d", "--debug",
                        help="print debug information when an error occurs",
                        action="store_true")

    def add_replace_axml_command():
        subparser = subparsers.add_parser("replace_axml", help="replace the axml chunk in an existing ADM BWF file")
        subparser.add_argument("input", help="input bwf file")
        subparser.add_argument("output", help="output bwf file")
        subparser.add_argument("-a", "--axml", help="new axml chunk file", required=True, metavar="file")
        subparser.add_argument("-g", "--gen-chna", help="generate the CHNA information from the track UIDs", action="store_true")
        subparser.set_defaults(command=replace_axml_command)

    def add_regenerate_command():
        subparser = subparsers.add_parser("regenerate", help="read and write an ADM BWF file, regenerating the ADM and CHNA")
        subparser.add_argument("input", help="input bwf file")
        subparser.add_argument("output", help="output bwf file")
        subparser.add_argument("--enable-block-duration-fix", action="store_true",
                               help="automatically try to fix faulty block format durations")
        subparser.add_argument(
            "--set-version",
            help="set AXML version tag, either an integer version number or full version string",
        )
        subparser.set_defaults(command=regenerate_command)

    def add_rewrite_command():
        subparser = subparsers.add_parser("rewrite", help="read and write a BWF file to fix BWF format warnings")
        subparser.add_argument("input", help="input bwf file")
        subparser.add_argument("output", help="output bwf file")
        subparser.set_defaults(command=rewrite_command)

    def add_dump_axml_command():
        subparser = subparsers.add_parser("dump_axml", help="dump the axml chunk of an ADM BWF file to stdout")
        subparser.add_argument("input", help="input bwf file")
        subparser.set_defaults(command=dump_axml_command)

    def add_dump_chna_command():
        subparser = subparsers.add_parser("dump_chna", help="dump the chna chunk of an ADM BWF file to stdout")
        subparser.add_argument("input", help="input bwf file")
        subparser.add_argument("-b", "--binary", help="output binary data", action="store_true")
        subparser.set_defaults(command=dump_chna_command)

    generate_test_file.add_args(subparsers)
    add_replace_axml_command()
    add_dump_axml_command()
    add_dump_chna_command()
    add_regenerate_command()
    add_rewrite_command()
    ambix_to_bwf.add_args(subparsers)

    return parser


def parse_command_line():
    parser = make_parser()
    args = parser.parse_args()
    if 'command' not in args:
        parser.error('No command specified')

    return args


def main():
    args = parse_command_line()

    with error_handler(logger, debug=args.debug):
        args.command(args)


if __name__ == '__main__':
    main()
