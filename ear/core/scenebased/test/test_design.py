import numpy as np
import pytest
from ....fileio.adm.elements import PolarPositionOffset
from ... import hoa, point_source
from ...bs2051 import get_layout
from ...metadata_input import HOATypeMetadata
from ..design import HOADecoderDesign

# compare against a reference, as otherwise we'd end up reimplementing the
# whole thing, and still would not spot changes in allrad_design

ref_decoder = np.array(
    [
        [1.71634590e-01, 1.42431019e-01, -1.17545274e-01, 1.30305331e-01],
        [1.71642551e-01, -1.42433751e-01, -1.17551622e-01, 1.30321095e-01],
        [1.13881860e-01, 7.52101654e-06, -8.55161879e-02, 1.23448338e-01],
        [3.68460920e-01, 2.13546281e-01, -1.68472356e-01, -2.38326574e-01],
        [3.68450573e-01, -2.13530753e-01, -1.68465249e-01, -2.38333209e-01],
        [1.30447818e-01, 6.67387033e-02, 1.45593901e-01, 9.44637862e-02],
        [1.30433098e-01, -6.67320618e-02, 1.45594222e-01, 9.44437810e-02],
        [1.76070328e-01, 9.23726786e-02, 2.01041658e-01, -6.00913147e-02],
        [1.76077278e-01, -9.23760367e-02, 2.01043852e-01, -6.00980940e-02],
    ]
)


@pytest.fixture(scope="module")
def layout():
    return get_layout("4+5+0").without_lfe


@pytest.fixture(scope="module")
def panner(layout):
    return HOADecoderDesign(layout)


@pytest.fixture
def type_metadata():
    order = 1
    acn = np.arange((order + 1) ** 2)
    orders, degrees = hoa.from_acn(acn)

    return HOATypeMetadata(
        orders=orders.tolist(),
        degrees=degrees.tolist(),
        normalization="N3D",
    )


def test_basic(panner, type_metadata):
    decoder = panner.design(type_metadata)
    # print(repr(decoder))
    np.testing.assert_allclose(decoder, ref_decoder, atol=1e-6)


def test_gains(panner, type_metadata):
    gains = np.linspace(0.1, 0.9, len(type_metadata.orders))
    type_metadata.gains = gains.tolist()

    decoder = panner.design(type_metadata)
    np.testing.assert_allclose(decoder, ref_decoder * gains, atol=1e-6)


def test_object_gain(panner, type_metadata):
    type_metadata.extra_data.object_gain = 0.5

    decoder = panner.design(type_metadata)
    np.testing.assert_allclose(decoder, ref_decoder * 0.5, atol=1e-6)


def test_object_mute(panner, type_metadata):
    type_metadata.extra_data.object_mute = True

    decoder = panner.design(type_metadata)
    np.testing.assert_allclose(decoder, np.zeros_like(ref_decoder), atol=1e-6)


def test_object_positionOffset(panner, type_metadata):
    type_metadata.extra_data.object_positionOffset = PolarPositionOffset(azimuth=30.0)

    with pytest.raises(ValueError, match="positionOffset is not supported with HOA"):
        panner.design(type_metadata)
