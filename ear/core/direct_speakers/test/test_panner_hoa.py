import numpy as np
import pytest
from ....fileio.adm.elements import (
    BoundCoordinate,
    DirectSpeakerPolarPosition,
    Frequency,
)
from ...hoa import sph_harm
from ...hoa_adapter import HOAFormat
from ...metadata_input import (
    AudioBlockFormatDirectSpeakers,
    DirectSpeakersTypeMetadata,
    ExtraData,
)
from .. import panner_hoa  # noqa: F401
from ..panner import build_direct_speakers_panner


def test_panner():
    fmt = HOAFormat(max_order=1, normalization="SN3D", channel_order="ACN")
    n, m = fmt.orders_degrees
    norm = fmt.norm_fn

    panner = build_direct_speakers_panner(fmt)

    positions = [
        (0.0, 0.0),
        (90.0, 0.0),
        (-90.0, 0.0),
        (180.0, 0.0),
        (0.0, 90.0),
        (0.0, -90.0),
    ]

    for az, el in positions:
        expected = sph_harm(n, m, np.radians(az), np.radians(el), norm)

        tm = DirectSpeakersTypeMetadata(
            block_format=AudioBlockFormatDirectSpeakers(
                position=DirectSpeakerPolarPosition(
                    bounded_azimuth=BoundCoordinate(az),
                    bounded_elevation=BoundCoordinate(el),
                ),
                speakerLabel=["label"],
            )
        )

        actual = panner.handle(tm)

        np.testing.assert_allclose(actual, expected)


def test_panner_lfe():
    fmt = HOAFormat(max_order=1, normalization="SN3D", channel_order="ACN")
    panner = build_direct_speakers_panner(fmt)

    expected = np.zeros(4)

    tm = DirectSpeakersTypeMetadata(
        block_format=AudioBlockFormatDirectSpeakers(
            position=DirectSpeakerPolarPosition(
                bounded_azimuth=BoundCoordinate(0.0),
                bounded_elevation=BoundCoordinate(0.0),
            ),
            speakerLabel=["LFE1"],
        ),
        extra_data=ExtraData(channel_frequency=Frequency(lowPass=120.0)),
    )

    with pytest.warns(UserWarning, match="discarding DirectSpeakers LFE channel"):
        actual = panner.handle(tm)

    np.testing.assert_allclose(actual, expected)
