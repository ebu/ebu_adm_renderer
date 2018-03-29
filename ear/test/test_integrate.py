import numpy as np
import numpy.testing as npt
import soundfile
import os.path
import subprocess
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


if __name__ == "__main__":
    regenerate = False

    if not os.path.exists(wav_file):
        print("regenerating {}".format(wav_file))  # noqa
        generate_input_wav()
        regenerate = True

    if regenerate or not os.path.exists(bwf_file):
        print("regenerating {}".format(bwf_file))  # noqa
        generate_test_bwf()
