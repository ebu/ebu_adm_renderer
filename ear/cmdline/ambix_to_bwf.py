import numpy as np
import lxml.etree
from ..core.hoa import from_acn
from ..fileio.adm.adm import ADM
from ..fileio.adm.elements import (
    AudioBlockFormatHoa,
    AudioChannelFormat,
    TypeDefinition,
    FormatDefinition,
)
from ..fileio.adm.elements import (
    AudioStreamFormat,
    AudioTrackFormat,
    AudioPackFormat,
    AudioObject,
    AudioTrackUID,
)
from ..fileio.adm.chna import populate_chna_chunk
from ..fileio.adm.generate_ids import generate_ids
from ..fileio.adm.xml import adm_to_xml
from ..fileio import openBw64
from ..fileio.bw64.chunks import ChnaChunk, FormatInfoChunk


def add_args(subparsers):
    subparser = subparsers.add_parser(
        "ambix_to_bwf", help="make a BWF file from an ambix format HOA file"
    )
    subparser.add_argument("--norm", default="SN3D", help="normalization mode")
    subparser.add_argument(
        "--nfcDist",
        type=float,
        default=None,
        help="Near-Field Compensation Distance (float)",
    )
    subparser.add_argument("--screenRef", help="Screen Reference", action="store_true")
    subparser.add_argument(
        "--chna-only", help="use only CHNA with common definitions", action="store_true"
    )
    subparser.add_argument("input", help="input file")
    subparser.add_argument("output", help="output BWF file")
    subparser.set_defaults(command=ambix_to_bwf)


def get_acn(n_channels, args):
    return np.arange(n_channels)


def build_adm(acn, norm, nfcDist, screenRef):
    adm = ADM()

    track_uids = []

    pack_format = AudioPackFormat(
        audioPackFormatName="HOA",
        type=TypeDefinition.HOA,
        audioChannelFormats=[],
    )
    adm.addAudioPackFormat(pack_format)

    order, degree = from_acn(acn)
    for channel_no, (order, degree) in enumerate(zip(order, degree), 1):
        block_format = AudioBlockFormatHoa(
            order=int(order),
            degree=int(degree),
            normalization=norm,
            nfcRefDist=nfcDist,
            screenRef=screenRef,
        )

        name = "channel_{}".format(channel_no)
        channel_format = AudioChannelFormat(
            audioChannelFormatName=name,
            type=TypeDefinition.HOA,
            audioBlockFormats=[block_format],
        )
        adm.addAudioChannelFormat(channel_format)
        pack_format.audioChannelFormats.append(channel_format)

        stream_format = AudioStreamFormat(
            audioStreamFormatName=name,
            format=FormatDefinition.PCM,
            audioChannelFormat=channel_format,
        )
        adm.addAudioStreamFormat(stream_format)

        track_format = AudioTrackFormat(
            audioTrackFormatName=name,
            format=FormatDefinition.PCM,
            audioStreamFormat=stream_format,
        )
        adm.addAudioTrackFormat(track_format)

        track_uid = AudioTrackUID(
            trackIndex=channel_no,
            audioTrackFormat=track_format,
            audioPackFormat=pack_format,
        )
        adm.addAudioTrackUID(track_uid)
        track_uids.append(track_uid)

    audio_object = AudioObject(
        audioObjectName="HOA",
        audioPackFormats=[pack_format],
        audioTrackUIDs=track_uids,
    )
    adm.addAudioObject(audio_object)

    return adm


def build_adm_common_defs(acns, norm):
    from ..fileio.adm.common_definitions import load_common_definitions

    adm = ADM()
    load_common_definitions(adm)

    order, degree = from_acn(acns)

    pack_name = "3D_order{order}_{norm}_ACN".format(order=max(order), norm=norm)
    [pack_format] = [
        apf for apf in adm.audioPackFormats if apf.audioPackFormatName == pack_name
    ]

    for channel_no, acn in enumerate(acns, 1):
        track_name = "PCM_{norm}_ACN_{acn}".format(norm=norm, acn=acn)
        [track_format] = [
            tf for tf in adm.audioTrackFormats if tf.audioTrackFormatName == track_name
        ]

        adm.addAudioTrackUID(
            AudioTrackUID(
                trackIndex=channel_no,
                audioTrackFormat=track_format,
                audioPackFormat=pack_format,
            )
        )

    return adm


def ambix_to_bwf(args):
    with openBw64(args.input) as infile:
        acn = get_acn(infile.channels, args)

        if args.chna_only:
            assert args.nfcDist is None
            assert not args.screenRef
            adm = build_adm_common_defs(acn, args.norm)
        else:
            adm = build_adm(acn, args.norm, args.nfcDist, args.screenRef)

        generate_ids(adm)

        if args.chna_only:
            axml = None
        else:
            xml = adm_to_xml(adm)
            axml = lxml.etree.tostring(xml, pretty_print=True)

        chna = ChnaChunk()
        populate_chna_chunk(chna, adm)

        fmtInfo = FormatInfoChunk(
            formatTag=1,
            channelCount=infile.channels,
            sampleRate=infile.sampleRate,
            bitsPerSample=infile.bitdepth,
        )

        with openBw64(
            args.output, "w", chna=chna, formatInfo=fmtInfo, axml=axml
        ) as outfile:
            while True:
                samples = infile.read(1024)
                if samples.shape[0] == 0:
                    break
                outfile.write(samples)
