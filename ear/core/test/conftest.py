from .. import bs2051
import pytest


@pytest.fixture(params=bs2051.layout_names)
def layout_with_lfe(request):
    """Layout object."""
    return bs2051.get_layout(request.param)


@pytest.fixture
def layout(layout_with_lfe):
    return layout_with_lfe.without_lfe
