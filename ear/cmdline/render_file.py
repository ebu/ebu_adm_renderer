from __future__ import print_function
import argparse
import sys
import scipy.sparse
from itertools import chain
from ..core import bs2051, layout, Renderer
from ..core.monitor import PeakMonitor
from ..core.metadata_processing import preprocess_rendering_items
from ..fileio import openBw64, openBw64Adm
from ..fileio.bw64.chunks import FormatInfoChunk
import warnings
from ..fileio.adm.exceptions import AdmUnknownAttribute


def handle_strict(args):
    if args.strict:
        warnings.filterwarnings("error", category=AdmUnknownAttribute)


def process_file(input_file, output_file, target_layout, speakers_file, output_gain_db, fail_on_overload, enable_block_duration_fix, config=None):
    if config is None:
        config = {}

    spkr_layout = bs2051.get_layout(target_layout)

    if speakers_file is not None:
        real_layout = layout.load_real_layout(speakers_file)
        spkr_layout, upmix = spkr_layout.with_real_layout(real_layout)
        spkr_layout.check_upmix_matrix(upmix)
        upmix = scipy.sparse.csc_matrix(upmix.T)
        n_channels = upmix.shape[1]
    else:
        upmix = None
        n_channels = len(spkr_layout.channels)

    renderer = Renderer(spkr_layout, **config)

    output_gain_linear = 10.0 ** (output_gain_db / 20.0)

    output_monitor = PeakMonitor(n_channels)

    blocksize = 8192
    with openBw64Adm(input_file, enable_block_duration_fix) as infile:
        selected_items = preprocess_rendering_items(infile.selected_items)
        renderer.set_rendering_items(selected_items)

        formatInfo = FormatInfoChunk(formatTag=1,
                                     channelCount=n_channels,
                                     sampleRate=infile.sampleRate,
                                     bitsPerSample=infile.bitdepth)
        with openBw64(output_file, 'w', formatInfo=formatInfo) as outfile:
            for input_samples in chain(infile.iter_sample_blocks(blocksize), [None]):
                if input_samples is None:
                    output_samples = renderer.get_tail(infile.sampleRate, infile.channels)
                else:
                    output_samples = renderer.render(infile.sampleRate, input_samples)

                output_samples *= output_gain_linear

                if upmix is not None:
                    output_samples *= upmix

                output_monitor.process(output_samples)
                outfile.write(output_samples)

    output_monitor.warn_overloaded()
    if fail_on_overload and output_monitor.has_overloaded():
        sys.exit("error: output overloaded")


def parse_command_line():
    parser = argparse.ArgumentParser(description='EBU ADM renderer')

    parser.add_argument('-d', '--debug',
                        help="print debug information when an error occurres",
                        action="store_true")

    parser.add_argument('input_file')
    parser.add_argument('output_file')

    formats_string = ', '.join(bs2051.layout_names)
    parser.add_argument('-s', '--system', required=True, metavar="target_system",
                        help='Target output system, accoring to ITU-R BS.2051. '
                             'Available systems are: {}'.format(formats_string))

    parser.add_argument('-l', '--layout', type=argparse.FileType('r'), metavar='layout_file',
                        help='Layout config file')
    parser.add_argument('--output-gain-db', type=float, metavar='gain_db', default=0,
                        help='output gain in dB (default: 0)')
    parser.add_argument('--fail-on-overload', "-c", action='store_true',
                        help='fail if an overload condition is detected in the output')
    parser.add_argument('--enable-block-duration-fix', action='store_true',
                        help='automatically try to fix faulty block format durations')
    parser.add_argument('--strict',
                        help="treat unknown ADM attributes as errors",
                        action="store_true")

    args = parser.parse_args()
    return args


def main():
    args = parse_command_line()

    handle_strict(args)

    try:
        process_file(args.input_file, args.output_file, args.system, args.layout,
                     args.output_gain_db, args.fail_on_overload, args.enable_block_duration_fix)
    except Exception as error:
        if args.debug:
            raise
        else:
            sys.exit(str(error))


if __name__ == '__main__':
    main()
