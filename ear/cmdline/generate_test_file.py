import lxml.etree
from ..compatibility import load_yaml
from ..core import layout
from ..fileio.adm.builder import ADMBuilder
from ..fileio.adm.elements import AudioBlockFormatObjects, JumpPosition, Frequency
from ..fileio.adm.elements import AudioBlockFormatDirectSpeakers, BoundCoordinate, DirectSpeakerPolarPosition
from ..fileio.adm.chna import populate_chna_chunk
from ..fileio.adm.generate_ids import generate_ids
from ..fileio.adm.xml import adm_to_xml
from ..fileio import openBw64
from ..fileio.bw64.chunks import ChnaChunk, FormatInfoChunk
from fractions import Fraction

"""
Generate ADM BWF files from a simple yaml format, like this:

    name: front centre
    items:
        - type: "Objects"
          channels: [1]
          blocks:
              - rtime: 0.0
                duration: 1.0
                position:
                    azimuth: 0.0
                    elevation: 0.0
                    distance: 1.0
                gain: 1.0
        - type: "DirectSpeakers"
          channels: [2]
          blocks:
              - speakerLabel: ["M+045"]
                position:
                    azimuth:
                        value: 45.0
                        min: 30.0
                        max: 50.0
                    elevation: 0.0
        - type: "DirectSpeakers"
          channels: [3]
          frequency:
              lowPass: 120.0
          blocks:
              - speakerLabel: ["LFE1"]
                position:
                    azimuth: 0.0
                    elevation: -30.0

- items corresponds to the concept of 'rendering items' in the renderer, and
  are a channel format associated with the channels that will be rendered with
  that channel format.
- block attributes should map to the attributes in the block format structures,
  more will be added as needed
- timing attributes are are parsed using Fraction, so may be numbers, decimal
  format strings, or fraction format strings. Use quotes to make exact values!

"""


def load_frequency(item):
    return Frequency(lowPass=item.get("frequency", {}).get("lowPass"),
                     highPass=item.get("frequency", {}).get("highPass"))


def load_block_common(kwargs, block):
    if "rtime" in block:
        kwargs["rtime"] = Fraction(block["rtime"])
    if "duration" in block:
        kwargs["duration"] = Fraction(block["duration"])


def load_jump_position(jumpPosition):
    kwargs = {}

    if "flag" in jumpPosition:
        kwargs["flag"] = jumpPosition["flag"]

    if "interpolationLength" in jumpPosition:
        kwargs["interpolationLength"] = Fraction(jumpPosition["interpolationLength"])

    return JumpPosition(**kwargs)


def load_block_objects(block):
    kwargs = {}
    load_block_common(kwargs, block)

    if "jumpPosition" in block:
        kwargs["jumpPosition"] = load_jump_position(block["jumpPosition"])

    for attr in ["position", "gain"]:
        if attr in block:
            kwargs[attr] = block[attr]

    return AudioBlockFormatObjects(**kwargs)


def create_item_objects(builder, item):
    blocks = list(map(load_block_objects, item["blocks"]))

    for channel in item["channels"]:
        adm_item = builder.create_item_objects(name=item.get("name", "unnamed"),
                                               track_index=channel - 1,
                                               block_formats=blocks)
        adm_item.channel_format.frequency = load_frequency(item)


def load_block_direct_speakers(block):
    kwargs = {}
    load_block_common(kwargs, block)

    if "speakerLabel" in block:
        kwargs["speakerLabel"] = block["speakerLabel"]

    def parse_bound(bound, default=None):
        if isinstance(bound, dict):
            return BoundCoordinate(value=bound["value"],
                                   min=bound.get("min"),
                                   max=bound.get("max"))
        else:
            return BoundCoordinate(value=bound)

    pos_args = block["position"]
    kwargs["position"] = DirectSpeakerPolarPosition(
        bounded_azimuth=parse_bound(pos_args["azimuth"]),
        bounded_elevation=parse_bound(pos_args["elevation"]),
        bounded_distance=parse_bound(pos_args["distance"]) if "distance" in pos_args else BoundCoordinate(value=1.0),
    )

    return AudioBlockFormatDirectSpeakers(**kwargs)


def create_item_direct_speakers(builder, item):
    blocks = list(map(load_block_direct_speakers, item["blocks"]))

    for channel in item["channels"]:
        adm_item = builder.create_item_direct_speakers(name=item.get("name", "unnamed"),
                                                       track_index=channel - 1,
                                                       block_formats=blocks)
        adm_item.channel_format.frequency = load_frequency(item)


create_item_by_type = {
    "Objects": create_item_objects,
    "DirectSpeakers": create_item_direct_speakers,
}


def create_item(builder, item):
    create_item_by_type[item["type"]](builder, item)


def load_test_file_adm(filename):
    with open(filename) as f:
        yaml = load_yaml(f)

    builder = ADMBuilder()

    builder.create_programme(
        audioProgrammeName=yaml.get("name", "unnamed"),
        start=Fraction(yaml["start"]) if "start" in yaml else None,
        end=Fraction(yaml["end"]) if "end" in yaml else None,
    )

    builder.create_content(
        audioContentName="content",
    )

    for item in yaml["items"]:
        create_item(builder, item)

    return builder.adm


def generate_test_file(test_path, in_wav_path, out_bwav_path, screen=None):
    adm = load_test_file_adm(test_path)

    if screen is not None:
        adm.audioProgrammes[0].referenceScreen = screen

    generate_ids(adm)

    xml = adm_to_xml(adm)
    axml = lxml.etree.tostring(xml, pretty_print=True)

    chna = ChnaChunk()
    populate_chna_chunk(chna, adm)

    with openBw64(in_wav_path) as infile:
        fmtInfo = FormatInfoChunk(formatTag=1,
                                  channelCount=infile.channels,
                                  sampleRate=infile.sampleRate,
                                  bitsPerSample=infile.bitdepth)

        with openBw64(out_bwav_path, 'w', chna=chna, formatInfo=fmtInfo, axml=axml) as outfile:
            while True:
                samples = infile.read(1024)
                if samples.shape[0] == 0: break
                outfile.write(samples)


def make_test_bwf_command(args):
    screen = layout.load_real_layout(args.screen).screen if args.screen is not None else None

    generate_test_file(args.meta, args.input, args.output, screen=screen)


def add_args(subparsers):
    import argparse
    subparser = subparsers.add_parser("make_test_bwf", help="make a bwf file from a wav file and some metadata")
    subparser.add_argument("output", help="output bwf file")
    subparser.add_argument("-i", "--input", help="input wav file", required=True)
    subparser.add_argument("-m", "--meta", help="input yaml metadata file", required=True)
    subparser.add_argument("--screen", type=argparse.FileType('r'), metavar="speakers_file",
                           help="YAML format speakers file to take reference screen from")
    subparser.set_defaults(command=make_test_bwf_command)
