import pytest
from ... import bs2051
from ..gain_calc import GainCalc


@pytest.fixture(scope="module")
def layout():
    return bs2051.get_layout("4+5+0")


@pytest.fixture(scope="module")
def layout_without_lfe(layout_with_lfe):
    return layout_with_lfe.without_lfe


@pytest.fixture(scope="module")
def gain_calc(layout):
    return GainCalc(layout)


@pytest.fixture(params=bs2051.layout_names)
def any_layout_with_lfe(request):
    """Layout object."""
    return bs2051.get_layout(request.param)


@pytest.fixture
def any_layout(any_layout_with_lfe):
    return any_layout_with_lfe.without_lfe
