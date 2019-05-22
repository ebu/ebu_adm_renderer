from attr import attrs, attrib, evolve
from .metadata_input import ObjectRenderingItem, MetadataSource
from .importance import filter_by_importance


def preprocess_rendering_items(rendering_items, importance_threshold=None):
    """ Applies configurable preproccessing steps to rendering items.

    Which preprocessing steps will be applied depends on the arguments given
    to this function.
    Each parameter instaniates a single preprocessing step.
    If the paramter is None, the associated step will be skipped.

    Parameters:
        importance_threshold (int): Installs `importance.filter_by_importance`

    Returns: List of RenderingItem
    """
    f = rendering_items
    if importance_threshold is not None:
        f = filter_by_importance(f, threshold=importance_threshold)
    return list(f)


@attrs
class MetadataSourceModifyBlockFormat(MetadataSource):
    """Metadata source wrapper which applies a given function to block_format attributes."""
    inner = attrib()
    f = attrib()

    def get_next_block(self):
        block = self.inner.get_next_block()

        if block is not None:
            block = evolve(block,
                           block_format=self.f(block.block_format))

        return block


def apply_to_object_blocks(rendering_items, f):
    """Apply f to Object block formats in rendering_items."""
    for item in rendering_items:
        if isinstance(item, ObjectRenderingItem):
            yield evolve(item,
                         metadata_source=MetadataSourceModifyBlockFormat(item.metadata_source, f))
        else:
            yield item


def convert_objects_to_polar(rendering_items):
    """Apply conversion to turn all Objects block formats into polar."""
    from .objectbased.conversion import to_polar
    return list(apply_to_object_blocks(rendering_items, to_polar))


def convert_objects_to_cartesian(rendering_items):
    """Apply conversion to turn all Objects block formats into Cartesian."""
    from .objectbased.conversion import to_cartesian
    return list(apply_to_object_blocks(rendering_items, to_cartesian))
