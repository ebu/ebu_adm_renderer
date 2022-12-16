import numpy as np
import pytest
from ....fileio.adm.elements import (
    AudioBlockFormatObjects,
    ObjectDivergence,
    ObjectPolarPosition,
)
from ...hoa import sph_harm
from ...hoa_adapter import HOAFormat
from ...metadata_input import ExtraData, ObjectTypeMetadata
from ..gain_calc_hoa import GainCalcHOA


@pytest.fixture(scope="module")
def fmt():
    return HOAFormat(max_order=1, normalization="SN3D", channel_order="ACN")


@pytest.fixture(scope="module")
def gain_calc(fmt):
    return GainCalcHOA(fmt)


@pytest.fixture(scope="module")
def pan(fmt):
    def f(az, el):
        n, m = fmt.orders_degrees
        return sph_harm(n, m, np.radians(az), np.radians(el), fmt.norm_fn)

    return f


@pytest.fixture(scope="module")
def run_test(fmt, gain_calc, pan):
    def f(
        block_format,
        extra_data=ExtraData(),
        direct_gains=None,
        diffuse_gains=None,
        direct_position=None,
        diffuse_position=None,
        atol=1e-10,
        rtol=1e-6,
    ):
        block_format = AudioBlockFormatObjects(**block_format)

        actual = gain_calc.render(
            ObjectTypeMetadata(block_format=block_format, extra_data=extra_data)
        )

        if direct_position is not None:
            direct_gains = pan(*direct_position)
        if diffuse_position is not None:
            diffuse_gains = pan(*diffuse_position)

        if direct_gains is None:
            direct_gains = np.zeros(fmt.num_channels)
        if diffuse_gains is None:
            diffuse_gains = np.zeros(fmt.num_channels)

        np.testing.assert_allclose(actual.direct, direct_gains, atol=atol, rtol=rtol)
        np.testing.assert_allclose(actual.diffuse, diffuse_gains, atol=atol, rtol=rtol)

    return f


@pytest.mark.parametrize(
    "az,el",
    [
        (0.0, 0.0),
        (90.0, 0.0),
        (-90.0, 0.0),
        (180.0, 0.0),
        (0.0, 90.0),
        (0.0, -90.0),
    ],
)
def test_direct_pos(run_test, az, el):
    run_test(
        dict(position=ObjectPolarPosition(azimuth=az, elevation=el)),
        direct_position=(az, el),
    )


def test_gain(run_test, pan):
    run_test(
        dict(position=ObjectPolarPosition(azimuth=0.0, elevation=0.0), gain=0.5),
        direct_gains=pan(0.0, 0.0) * 0.5,
    )


def test_full_diffuse(run_test, pan):
    run_test(
        dict(position=ObjectPolarPosition(azimuth=0.0, elevation=0.0), diffuse=1.0),
        diffuse_position=(0.0, 0.0),
    )


def test_half_diffuse(run_test, pan):
    run_test(
        dict(position=ObjectPolarPosition(azimuth=0.0, elevation=0.0), diffuse=0.5),
        direct_gains=pan(0.0, 0.0) * np.sqrt(0.5),
        diffuse_gains=pan(0.0, 0.0) * np.sqrt(0.5),
    )


def test_spread_small(run_test, pan):
    run_test(
        dict(
            position=ObjectPolarPosition(azimuth=0.0, elevation=0.0),
            width=10.0,
            height=10.0,
        ),
        direct_gains=[1, 0, 0, 0.99],
        atol=1e-2,
    )

    run_test(
        dict(
            position=ObjectPolarPosition(azimuth=180.0, elevation=0.0),
            width=10.0,
            height=10.0,
        ),
        direct_gains=[1, 0, 0, -0.99],
        atol=1e-2,
    )

    run_test(
        dict(
            position=ObjectPolarPosition(azimuth=90.0, elevation=0.0),
            width=10.0,
            height=10.0,
        ),
        direct_gains=[1, 0.99, 0, 0],
        atol=1e-2,
    )


def test_spread_large(run_test, pan):
    run_test(
        dict(
            position=ObjectPolarPosition(azimuth=0.0, elevation=0.0),
            width=360.0,
            height=360.0,
        ),
        direct_gains=[1, 0, 0, 0],
        atol=1e-2,
    )

    # for FOA, full width is equivalent to full extent
    run_test(
        dict(
            position=ObjectPolarPosition(azimuth=0.0, elevation=0.0),
            width=360.0,
            height=0.0,
        ),
        direct_gains=[1, 0, 0, 0],
        atol=1e-2,
    )


def test_diverge(run_test, pan):
    run_test(
        dict(
            position=ObjectPolarPosition(azimuth=0.0, elevation=0.0),
            objectDivergence=ObjectDivergence(0.5, azimuthRange=360 / 3),
        ),
        direct_gains=[1, 0, 0, 0],
    )
