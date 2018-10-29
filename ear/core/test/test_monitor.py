import numpy as np
from ..monitor import PeakMonitor


def test_peak_monitor():
    mon = PeakMonitor(2)

    samples = np.zeros((0, 2))
    mon.process(samples)

    samples = np.zeros((1000, 2))
    mon.process(samples)
    assert not mon.has_overloaded()

    samples = np.zeros((1000, 2))
    samples[100, 0] = 0.9
    mon.process(samples)
    assert not mon.has_overloaded()

    samples = np.zeros((1000, 2))
    samples[100, 1] = 10.0
    mon.process(samples)
    assert mon.has_overloaded()

    samples = np.zeros((1000, 2))
    mon.process(samples)
    assert mon.has_overloaded()

    import pytest
    with pytest.warns(None) as record:
        mon.warn_overloaded()
    assert len(record) == 1 and str(record[0].message) == "overload in channel 1; peak level was 20.0dBFS"
