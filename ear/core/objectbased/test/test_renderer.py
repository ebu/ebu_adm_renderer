from fractions import Fraction
import numpy as np
from ..renderer import InterpretObjectMetadata, FixedGains, InterpGains
from ...metadata_input import ObjectTypeMetadata
from ....fileio.adm.elements import AudioBlockFormatObjects, JumpPosition


def test_interpret_object_metadata():
    def calc_gains(otm):
        return np.array([otm.block_format.gain])

    sr = 48000
    iom = InterpretObjectMetadata(calc_gains)

    def bf_to_states(**kwargs):
        block_format = AudioBlockFormatObjects(position=dict(azimuth=0, elevation=0, distance=1),
                                               **kwargs)
        return list(iom(sr, ObjectTypeMetadata(block_format=block_format)))

    # fixed for duration of first block
    assert (bf_to_states(rtime=Fraction(0), duration=Fraction(1), gain=0.1) ==
            [FixedGains(start_sample=0, end_sample=sr, gains=[0.1])])

    # interpolate over next regular adjacent block
    assert (bf_to_states(rtime=Fraction(1), duration=Fraction(1), gain=0.2) ==
            [InterpGains(start_sample=sr, end_sample=2*sr, gains_start=[0.1], gains_end=[0.2])])

    # jump position with no interpolation -> fixed in block
    assert (bf_to_states(rtime=Fraction(2), duration=Fraction(1), gain=0.3,
                         jumpPosition=JumpPosition(flag=True, interpolationLength=Fraction(0))) ==
            [FixedGains(start_sample=2*sr, end_sample=3*sr, gains=[0.3])])

    # jump position with some interpolation -> interpolated for part of block, constant for rest
    assert (bf_to_states(rtime=Fraction(3), duration=Fraction(1), gain=0.4,
                         jumpPosition=JumpPosition(flag=True, interpolationLength=Fraction(1, 2))) ==
            [InterpGains(start_sample=3*sr, end_sample=3.5*sr, gains_start=[0.3], gains_end=[0.4]),
                FixedGains(start_sample=3.5*sr, end_sample=4*sr, gains=[0.4])])

    # jump position with no interpolation length -> fixed in block
    assert (bf_to_states(rtime=Fraction(4), duration=Fraction(1), gain=0.5, jumpPosition=JumpPosition(flag=True)) ==
            [FixedGains(start_sample=4*sr, end_sample=5*sr, gains=[0.5])])

    # gap between blocks -> fixed for whole block (same as first)
    assert (bf_to_states(rtime=Fraction(6), duration=Fraction(1), gain=0.6) ==
            [FixedGains(start_sample=6*sr, end_sample=7*sr, gains=[0.6])])
