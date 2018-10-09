from .metadata_input import MetadataSource, HOARenderingItem, ObjectRenderingItem


def filter_by_importance(rendering_items,
                         threshold=10):
    """Remove rendering items with an importance below the threshold

    This method is a generator that essentially combines
    `mute_audioBlockFormat_by_importance`, `filter_audioPackFormat_by_importance`
    and `filter_audioObject_by_importance`, in that order, all with the same
    importance threshold.

    Parameters:
        rendering_items (iterable of RenderingItems): RenderingItems to filter
        threshold (int): importance threshold

    Yields: RenderingItem
    """
    f = mute_audioBlockFormat_by_importance(rendering_items, threshold)
    f = filter_audioObject_by_importance(f, threshold)
    f = filter_audioPackFormat_by_importance(f, threshold)
    return f


def filter_audioObject_by_importance(rendering_items, threshold):
    """Remove rendering items with an audioObject importance below the threshold

    This method is a generator that can be used to filter RenderingItems
    based on the importance of their parent audioObject(s).

    Parameters:
        rendering_items (iterable of RenderingItems): RenderingItems to filter
        threshold (int): importance threshold

    Yields: RenderingItem
    """
    for item in rendering_items:
        if isinstance(item, HOARenderingItem):
            if any(importance.audio_object is None or importance.audio_object >= threshold
                   for importance in item.importances):
                yield item
        else:
            if item.importance.audio_object is None or item.importance.audio_object >= threshold:
                yield item


def filter_audioPackFormat_by_importance(rendering_items, threshold):
    """Remove rendering items with an audioPackFormat importance below a threshold

    This method is a generator that can be used to filter RenderingItems
    based on the importance of their parent audioPackFormat(s).


    Parameters:
        rendering_items (iterable of RenderingItems): RenderingItems to filter
        threshold (int): importance threshold

    Yields: RenderingItem
    """
    for item in rendering_items:
        if isinstance(item, HOARenderingItem):
            if any(importance.audio_pack_format is None or importance.audio_pack_format >= threshold
                   for importance in item.importances):
                yield item
        else:
            if item.importance.audio_pack_format is None or item.importance.audio_pack_format >= threshold:
                yield item


class MetadataSourceImportanceFilter(MetadataSource):
    """A Metadata source adapter to change block formats if their importance is below a given threshold.

    The intended result of "muting" the rendering item during this block format
    is emulated by setting its gain to zero and disabling any interpolation by
    activating the jumpPosition flag.

    Note: This MetadataSource can only be used for MetadataSources that
    generate `ObjectTypeMetadata`.
    """
    def __init__(self, adapted_source, threshold):
        super(MetadataSourceImportanceFilter, self).__init__()
        self._adapted = adapted_source
        self._threshold = threshold

    def get_next_block(self):
        block = self._adapted.get_next_block()
        if block is None:
            return None
        if block.block_format.importance < self._threshold:
            block.block_format.gain = 0
        return block


def mute_audioBlockFormat_by_importance(rendering_items, threshold):
    """Adapt rendering items of type `ObjectRenderingItem` to emulate block format importance handling

    This installs an `MetadataSourceImportanceFilter` with the given threshold

    Parameters:
        rendering_items (iterable of RenderingItems): RenderingItems to adapt
        threshold (int): importance threshold

    Yields: RenderingItem
    """
    for item in rendering_items:
        if isinstance(item, ObjectRenderingItem):
            item.metadata_source = MetadataSourceImportanceFilter(adapted_source=item.metadata_source, threshold=threshold)
        yield item
