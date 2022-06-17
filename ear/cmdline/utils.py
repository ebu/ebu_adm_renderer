from __future__ import print_function
import argparse
import logging
import sys
from ..compatibility import write_bytes_to_stdout
from ..fileio import openBw64, openBw64Adm
from ..fileio.bw64.chunks import FormatInfoChunk, ChnaChunk
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
            formatInfo = FormatInfoChunk(channelCount=infile.channels,
                                         sampleRate=infile.sampleRate,
                                         bitsPerSample=infile.bitdepth)
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

            with openBw64(args.output, 'w', formatInfo=formatInfo,
                          axml=axml, chna=chna) as outfile:
                while True:
                    samples = infile.read(2048)
                    if not len(samples):
                        break
                    outfile.write(samples)


def regenerate_command(args):
    from ..fileio.adm import xml as adm_xml
    from ..fileio.adm import chna as adm_chna
    from ..fileio.adm import timing_fixes
    import lxml.etree

    with openBw64Adm(args.input) as infile:
        formatInfo = FormatInfoChunk(channelCount=infile.channels,
                                     sampleRate=infile.sampleRate,
                                     bitsPerSample=infile.bitdepth)
        infile.adm.validate()

        if args.enable_block_duration_fix:
            timing_fixes.fix_blockFormat_timings(infile.adm)

        xml = adm_xml.adm_to_xml(infile.adm)
        axml = lxml.etree.tostring(xml, pretty_print=True)

        chna = ChnaChunk()
        adm_chna.populate_chna_chunk(chna, infile.adm)

        with openBw64(args.output, 'w', formatInfo=formatInfo,
                      axml=axml, chna=infile.chna) as outfile:
            for samples in infile.iter_sample_blocks(2048):
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
        subparser = subparsers.add_parser("regenerate", help="read and write an ADM BWF file, regnerating the ADM and CHNA")
        subparser.add_argument("input", help="input bwf file")
        subparser.add_argument("output", help="output bwf file")
        subparser.add_argument("--enable-block-duration-fix", action="store_true",
                               help="automatically try to fix faulty block format durations")
        subparser.set_defaults(command=regenerate_command)

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
