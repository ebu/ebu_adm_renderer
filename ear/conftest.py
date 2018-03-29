import numpy as np
import pytest


@pytest.fixture(scope="session", autouse=True)
def np_warnings_as_errors():
    np.seterr(all="raise")
