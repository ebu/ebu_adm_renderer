from __future__ import print_function
import argparse
import sys
from attr import attrs, attrib, Factory
import scipy.sparse
from itertools import chain
from ..core import bs2051, layout, Renderer
from ..core.monitor import PeakMonitor
from ..core.metadata_processing import preprocess_rendering_items
from ..core.select_items import select_rendering_items
from ..fileio import openBw64, openBw64Adm
from ..fileio.adm.elements import AudioProgramme, AudioObject
from ..fileio.bw64.chunks import FormatInfoChunk
import warnings
from ..fileio.adm.exceptions import AdmUnknownAttribute


def handle_strict(args):
    if args.strict:
        warnings.filterwarnings("error", category=AdmUnknownAttribute)


@attrs
class OfflineRenderDriver(object):
    """Obtain and store ancillary rendering parameters, and use them to perform file-to-file rendering."""

    target_layout = attrib()
    speakers_file = attrib()
    output_gain_db = attrib()
    fail_on_overload = attrib()
    enable_block_duration_fix = attrib()
    config = attrib(default=Factory(dict))

    programme_id = attrib(default=None)
    complementary_object_ids = attrib(default=Factory(list))

    blocksize = 8192

    @classmethod
    def add_args(cls, parser):
        """Add arguments to an ArgumentParser that can be used by from_args."""
        formats_string = ", ".join(bs2051.layout_names)
        parser.add_argument("-s", "--system", required=True, metavar="target_system",
                            help="Target output system, accoring to ITU-R BS.2051. "
                                 "Available systems are: {}".format(formats_string))

        parser.add_argument("-l", "--layout", type=argparse.FileType("r"), metavar="layout_file",
                            help="Layout config file")
        parser.add_argument("--output-gain-db", type=float, metavar="gain_db", default=0,
                            help="output gain in dB (default: 0)")
        parser.add_argument("--fail-on-overload", "-c", action="store_true",
                            help="fail if an overload condition is detected in the output")
        parser.add_argument("--enable-block-duration-fix", action="store_true",
                            help="automatically try to fix faulty block format durations")

        parser.add_argument("--programme", metavar="id",
                            help="select an audioProgramme to render by ID")
        parser.add_argument("--comp-object", metavar="id", action="append", default=[],
                            help="select an audioObject by ID from a complementary group")

    @classmethod
    def from_args(cls, args):
        return cls(
            target_layout=args.system,
            speakers_file=args.layout,
            output_gain_db=args.output_gain_db,
            fail_on_overload=args.fail_on_overload,
            enable_block_duration_fix=args.enable_block_duration_fix,
            programme_id=args.programme,
            complementary_object_ids=args.comp_object,
        )

    def load_output_layout(self):
        """Load the specified layout.

        Returns:
            layout (Layout): loudspeaker layout
            upmix (sparse array or None): optional matrix to apply after rendering
            n_channels (int): number of channels required in output file
        """
        spkr_layout = bs2051.get_layout(self.target_layout)

        if self.speakers_file is not None:
            real_layout = layout.load_real_layout(self.speakers_file)
            spkr_layout, upmix = spkr_layout.with_real_layout(real_layout)
            spkr_layout.check_positions()
            spkr_layout.check_upmix_matrix(upmix)
            upmix = scipy.sparse.csc_matrix(upmix.T)
            n_channels = upmix.shape[1]
        else:
            upmix = None
            n_channels = len(spkr_layout.channels)

        return spkr_layout, upmix, n_channels

    @property
    def output_gain_linear(self):
        return 10.0 ** (self.output_gain_db / 20.0)

    @classmethod
    def lookup_adm_element(cls, adm, element_id, element_type, element_type_name):
        """Lookup an element in adm by type and ID, with nice error messages."""
        if element_id is None:
            return None

        try:
            element = adm[element_id]
        except KeyError:
            raise KeyError("could not find {element_type_name} with ID {element_id}".format(
                element_type_name=element_type_name, element_id=element_id,
            ))

        if not isinstance(element, element_type):
            raise ValueError("{element_id} is not an {element_type_name}".format(
                element_type_name=element_type_name, element_id=element_id,
            ))

        return element

    def get_audio_programme(self, adm):
        return self.lookup_adm_element(adm, self.programme_id, AudioProgramme, "audioProgramme")

    def get_complementary_objects(self, adm):
        return [self.lookup_adm_element(adm, obj_id, AudioObject, "audioObject")
                for obj_id in self.complementary_object_ids]

    def get_rendering_items(self, adm):
        """Get rendering items from the input file adm.

        Parameters:
            adm (ADM): ADM to get the RenderingItems from

        Returns:
            list of RenderingItem: selected rendering items
        """
        audio_programme = self.get_audio_programme(adm)
        comp_objects = self.get_complementary_objects(adm)
        selected_items = select_rendering_items(
            adm,
            audio_programme=audio_programme,
            selected_complementary_objects=comp_objects)

        return preprocess_rendering_items(selected_items)

    def render_input_file(self, infile, spkr_layout, upmix=None):
        """Get sample blocks of the input file after rendering.

        Parameters:
            infile (Bw64AdmReader): file to read from
            spkr_layout (Layout): layout to render to
            upmix (sparse array or None): optional upmix to apply

        Yields:
            2D sample blocks
        """
        renderer = Renderer(spkr_layout, **self.config)
        renderer.set_rendering_items(self.get_rendering_items(infile.adm))

        for input_samples in chain(infile.iter_sample_blocks(self.blocksize), [None]):
            if input_samples is None:
                output_samples = renderer.get_tail(infile.sampleRate, infile.channels)
            else:
                output_samples = renderer.render(infile.sampleRate, input_samples)

            output_samples *= self.output_gain_linear

            if upmix is not None:
                output_samples *= upmix

            yield output_samples

    def run(self, input_file, output_file):
        """Render input_file to output_file."""
        spkr_layout, upmix, n_channels = self.load_output_layout()

        output_monitor = PeakMonitor(n_channels)

        with openBw64Adm(input_file, self.enable_block_duration_fix) as infile:
            formatInfo = FormatInfoChunk(formatTag=1,
                                         channelCount=n_channels,
                                         sampleRate=infile.sampleRate,
                                         bitsPerSample=infile.bitdepth)
            with openBw64(output_file, "w", formatInfo=formatInfo) as outfile:
                for output_block in self.render_input_file(infile, spkr_layout, upmix):
                    output_monitor.process(output_block)
                    outfile.write(output_block)

        output_monitor.warn_overloaded()
        if self.fail_on_overload and output_monitor.has_overloaded():
            sys.exit("error: output overloaded")


def parse_command_line():
    parser = argparse.ArgumentParser(description="EBU ADM renderer")

    parser.add_argument("-d", "--debug",
                        help="print debug information when an error occurs",
                        action="store_true")

    OfflineRenderDriver.add_args(parser)

    parser.add_argument("input_file")
    parser.add_argument("output_file")

    parser.add_argument("--strict",
                        help="treat unknown ADM attributes as errors",
                        action="store_true")

    args = parser.parse_args()
    return args


def main():
    args = parse_command_line()

    handle_strict(args)

    try:
        OfflineRenderDriver.from_args(args).run(args.input_file, args.output_file)
    except Exception as error:
        if args.debug:
            raise
        else:
            sys.exit(str(error))


if __name__ == "__main__":
    main()
