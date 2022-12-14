# importing these registers overloads to make various renderer components
# compatible with HOA output
from . import hoa_adapter  # noqa: F401
from .direct_speakers import panner_hoa  # noqa: F401
from .objectbased import renderer_hoa  # noqa: F401
from .scenebased import design_hoa  # noqa: F401
