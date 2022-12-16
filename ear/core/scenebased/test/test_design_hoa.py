import numpy as np
from ...hoa import norm_FuMa, norm_SN3D
from ...hoa_adapter import HOAFormat
from ...metadata_input import HOATypeMetadata
from .. import design_hoa  # noqa: F401
from ..design import build_hoa_decoder_design


def test_convert_order_norm():
    fmt = HOAFormat(max_order=1, normalization="SN3D", channel_order="ACN")

    tm = HOATypeMetadata(
        orders=[0, 1, 1, 1], degrees=[0, 1, -1, 0], normalization="FuMa"
    )

    designer = build_hoa_decoder_design(fmt)
    actual = designer.design(tm)

    # [out, in]
    expected = np.zeros((4, 4))

    expected[0, 0] = 1
    expected[1, 2] = 1
    expected[2, 3] = 1
    expected[3, 1] = 1

    n, m = fmt.orders_degrees
    expected *= (norm_SN3D(n, np.abs(m)) / norm_FuMa(n, np.abs(m)))[:, np.newaxis]

    np.testing.assert_allclose(actual, expected)


def test_upmix():
    fmt = HOAFormat(max_order=2, normalization="SN3D", channel_order="ACN")

    tm = HOATypeMetadata(
        orders=[0, 1, 1, 1], degrees=[0, -1, 0, 1], normalization="SN3D"
    )

    designer = build_hoa_decoder_design(fmt)
    actual = designer.design(tm)

    # [out, in]
    expected = np.eye(9, 4)

    np.testing.assert_allclose(actual, expected)


def test_downmix():
    fmt = HOAFormat(max_order=1, normalization="SN3D", channel_order="ACN")

    tm = HOATypeMetadata(
        orders=[0, 1, 1, 1, 2, 2, 2, 2, 2],
        degrees=[0, -1, 0, 1, -2, -1, 0, 1, 2],
        normalization="SN3D",
    )

    designer = build_hoa_decoder_design(fmt)
    actual = designer.design(tm)

    # [out, in]
    expected = np.eye(4, 9)

    np.testing.assert_allclose(actual, expected)
