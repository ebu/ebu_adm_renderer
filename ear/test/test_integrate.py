import numpy as np
import numpy.testing as npt
import soundfile
import os.path
import subprocess
import sys
import pytest

files_dir = os.path.join(os.path.dirname(__file__), "data")

wav_file = os.path.join(files_dir, "test.wav")
meta_file = os.path.join(files_dir, "test.yaml")
bwf_file = os.path.join(files_dir, "test_bwf.wav")

sr = 48000


def generate_samples():
    n_samp = sr // 4
    return np.array([np.sin(np.arange(n_samp) * 1000 * 2 * np.pi / sr),
                     np.sin(np.arange(n_samp) * 500 * 2 * np.pi / sr),
                     np.sin(np.arange(n_samp) * 2000 * 2 * np.pi / sr),
                     np.sin(np.arange(n_samp) * 50 * 2 * np.pi / sr),
                     ]).T * 0.1


def generate_input_wav():
    soundfile.write(wav_file, generate_samples(), samplerate=sr, subtype="PCM_24")


def generate_test_bwf(bwf_file=bwf_file):
    args = ['ear-utils', 'make_test_bwf', '-m', meta_file, '-i', wav_file, bwf_file]
    assert subprocess.call(args) == 0


@pytest.mark.xfail(sys.version_info < (3, 6),
                   reason="output may vary on platforms where dictionaries are not ordered")
def test_generate(tmpdir):
    """Check that the output of the test file generator does not change

    If it should, delete ear/test/data/test_bwf.wav and run this test file as a module:

        python -m ear.test.test_integrate
    """
    bwf_file_gen = str(tmpdir / "test_bwf.wav")
    generate_test_bwf(bwf_file_gen)

    # could check the rendering of this file instead, but it's good to spot
    # changes to the output format even if they don't affect the rendering, so
    # that compatibility with other systems can be checked
    assert open(bwf_file_gen, 'rb').read() == open(bwf_file, 'rb').read()


def test_render(tmpdir):
    rendered_file = str(tmpdir / "test_bwf_render.wav")
    args = ['ear-render', '-d', '-s', '4+5+0', bwf_file, rendered_file]
    assert subprocess.call(args) == 0

    samples, sr = soundfile.read(rendered_file)

    expected_in = generate_samples()

    # gains for each of the blocks
    remap_first = np.zeros((4, 10))
    remap_first[0, 2] = 1
    remap_first[1, 6] = 1

    remap_second = np.zeros((4, 10))
    remap_second[0, 1] = 1
    remap_second[1, 6] = 1

    # apply gains to all samples
    remapped_first = np.dot(expected_in, remap_first)
    remapped_second = np.dot(expected_in, remap_second)

    # then select based on sample number
    sampleno = np.arange(len(expected_in))[:, np.newaxis]
    expected = remapped_first * (sampleno < sr // 8) + remapped_second * (sampleno >= sr // 8)

    # add in channel based content
    expected[:, 7] += expected_in[:, 2]
    expected[:, 0] += expected_in[:, 2]
    expected[:, 3] += expected_in[:, 3]

    npt.assert_allclose(samples, expected, atol=1e-6)


def test_render_adapt(tmpdir):
    meta_file = os.path.join(files_dir, "test_adapt_meta.yaml")
    layout_file = os.path.join(files_dir, "test_adapt_speakers.yaml")
    bwf_file = str(tmpdir / "test_adapt_bwf.wav")

    args = ['ear-utils', 'make_test_bwf', '-m', meta_file, '-i', wav_file, bwf_file]
    assert subprocess.call(args) == 0

    rendered_file = str(tmpdir / "test_adapt_bwf_render.wav")
    args = ['ear-render', '--layout', layout_file, '-s', '0+5+0', bwf_file, rendered_file]
    assert subprocess.call(args) == 0

    samples, sr = soundfile.read(rendered_file)

    expected_in = generate_samples()[:, 0]

    expected = np.zeros((len(expected_in), 7))
    expected[:, 6] = expected_in

    npt.assert_allclose(samples, expected, atol=1e-6)


@pytest.mark.parametrize("order", [1, 2])
@pytest.mark.parametrize("chna_only", [False, True])
def test_hoa(tmpdir, order, chna_only):
    from ..core.geom import cart, azimuth
    from ..core import hoa

    spk_azimuths = np.array([30, -30, 0, 110, -110])
    spk_positions = cart(spk_azimuths, 0, 1)

    n, m = hoa.from_acn(range((order+1)**2))
    gains_for_channels = hoa.sph_harm(n[np.newaxis], m[np.newaxis],
                                      np.radians(spk_azimuths[:, np.newaxis]), 0,
                                      hoa.norm_SN3D)

    if order == 1:
        # checked with ambix tools
        npt.assert_allclose(gains_for_channels,
                            np.array([
                                [ 1.        ,  0.5       , 0.         ,  0.8660254 ],  # noqa
                                [ 1.        , -0.5       , 0.         ,  0.8660254 ],  # noqa
                                [ 1.        ,  0.        , 0.         ,  1.        ],  # noqa
                                [ 1.        ,  0.93969262, 0.         , -0.34202014],  # noqa
                                [ 1.        , -0.93969262, 0.         , -0.34202014],  # noqa
                            ]))

    channels = [0, 1, 2, 4, 5]

    sr = 48000
    n_samples = sr // 10
    overall_gain = 0.5

    input_samples = np.repeat(gains_for_channels * overall_gain, n_samples, axis=0)

    input_fname = str(tmpdir / "hoa_input.wav")
    soundfile.write(input_fname, input_samples, samplerate=sr, subtype="PCM_24")

    bwf_fname = str(tmpdir / "hoa_bwf.wav")
    opts = ["--chna-only"] if chna_only else []
    assert subprocess.call(["ear-utils", "ambix_to_bwf"] + opts + [input_fname, bwf_fname]) == 0

    rendered_fname = str(tmpdir / "hoa_rendered.wav")
    assert subprocess.call(["ear-render", "-d", "-s", "0+5+0", bwf_fname, rendered_fname]) == 0

    rendered_samples, rendered_sr = soundfile.read(rendered_fname)
    assert rendered_sr == sr

    sample_positions = np.arange(len(channels)) * n_samples + n_samples // 2
    rendered_gains = rendered_samples[sample_positions][:, channels]

    # target channel should generally have the highest amplitude
    if order >= 2:
        assert np.all(np.argmax(rendered_gains, axis=1) == np.arange(len(channels)))

    # velocity vectors should be approximately correct
    rendered_positions = np.dot(rendered_gains, spk_positions)
    rendered_azimuths = azimuth(rendered_positions)

    atol = {1: 16, 2: 5}[order]
    npt.assert_allclose(spk_azimuths, rendered_azimuths, atol=atol)


def generate_multi_programme_comp_object(fname):
    """Generate an ADM BWF with multiple programmes and complementary objects.

    Parameters:
        fname (str): file name to write to

    Returns:
        dict: IDs of the programmes and objects.

        prog_1 is the first programme, containing track 1.

        prog_2 is the second programme, containing obj_2 (track 2) and obj_3
        (track 3), which are complementary with obj_2 being the default.
    """
    import lxml.etree
    from ..fileio.adm.builder import ADMBuilder
    from ..fileio.adm.chna import populate_chna_chunk
    from ..fileio.adm.generate_ids import generate_ids
    from ..fileio.adm.xml import adm_to_xml
    from ..fileio import openBw64
    from ..fileio.bw64.chunks import ChnaChunk, FormatInfoChunk

    builder = ADMBuilder()
    builder.load_common_definitions()

    mono_pack = builder.adm["AP_00010001"]
    mono_track = builder.adm["AT_00010003_01"]

    prog_1 = builder.create_programme(audioProgrammeName="prog_1")
    builder.create_content(audioContentName="content_1")
    obj_1 = builder.create_object(audioObjectName="object_1", audioPackFormats=[mono_pack])
    builder.create_track_uid(audioTrackFormat=mono_track, audioPackFormat=mono_pack,
                             trackIndex=1)

    prog_2 = builder.create_programme(audioProgrammeName="prog_2")
    builder.create_content(audioContentName="content_2")
    obj_2 = builder.create_object(audioObjectName="object_2", audioPackFormats=[mono_pack])
    builder.create_track_uid(audioTrackFormat=mono_track, audioPackFormat=mono_pack,
                             trackIndex=2)
    obj_3 = builder.create_object(audioObjectName="object_3", audioPackFormats=[mono_pack])
    builder.create_track_uid(audioTrackFormat=mono_track, audioPackFormat=mono_pack,
                             trackIndex=3)

    obj_2.audioComplementaryObjects.append(obj_3)

    generate_ids(builder.adm)

    xml = adm_to_xml(builder.adm)
    axml = lxml.etree.tostring(xml, pretty_print=True)

    chna = ChnaChunk()
    populate_chna_chunk(chna, builder.adm)

    samples = generate_samples()[:, :3]
    fmtInfo = FormatInfoChunk(formatTag=1,
                              channelCount=samples.shape[1],
                              sampleRate=sr,
                              bitsPerSample=24)

    with openBw64(fname, 'w', chna=chna, formatInfo=fmtInfo, axml=axml) as outfile:
        outfile.write(samples)

    return dict(
        prog_1=prog_1.id,
        prog_2=prog_2.id,
        obj_1=obj_1.id,
        obj_2=obj_2.id,
        obj_3=obj_3.id,
    )


def check_call_fails(args, match_stderr=None):
    import re

    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    assert proc.returncode != 0
    if match_stderr is not None:
        match = re.search(match_stderr, stderr)
        assert match is not None, "Pattern '{match}' not found in '{stderr}'".format(
            match=match_stderr, stderr=stderr)


def test_multi_programme_comp_object(tmpdir):
    """Test the --programme and --comp-object flags."""
    bwf_fname = str(tmpdir / "adm.wav")

    ids = generate_multi_programme_comp_object(bwf_fname)

    conditions = [  # CLI args, expected channels
        ([], 0),
        (["--programme", ids["prog_1"]], 0),
        (["--programme", ids["prog_2"]], 1),
        (["--programme", ids["prog_2"], "--comp-object", ids["obj_3"]], 2),
    ]

    samples = generate_samples()

    for i, (args, expected_channel) in enumerate(conditions):
        rendered_fname = str(tmpdir / "out_{i}.wav".format(i=i))
        assert subprocess.call(["ear-render", "-d", "-s", "0+5+0", bwf_fname, rendered_fname] + args) == 0

        rendered_samples, rendered_sr = soundfile.read(rendered_fname)
        assert rendered_sr == sr

        npt.assert_allclose(rendered_samples[:, 2], samples[:, expected_channel], atol=1e-5)

    rendered_fname = str(tmpdir / "out_err.wav")

    check_call_fails(["ear-render", "--programme", "APR_1005", "-d", "-s", "0+5+0", bwf_fname, rendered_fname],
                     b"could not find audioProgramme with ID APR_1005")

    check_call_fails(["ear-render", "--programme", ids["obj_1"], "-d", "-s", "0+5+0", bwf_fname, rendered_fname],
                     "{element_id} is not an audioProgramme".format(element_id=ids["obj_1"]).encode())


if __name__ == "__main__":
    regenerate = False

    if not os.path.exists(wav_file):
        print("regenerating {}".format(wav_file))  # noqa
        generate_input_wav()
        regenerate = True

    if regenerate or not os.path.exists(bwf_file):
        print("regenerating {}".format(bwf_file))  # noqa
        generate_test_bwf()
