from .metadata_input import MetadataSource, HOARenderingItem
from attr import evolve


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


class MetadataSourceMap(MetadataSource):
    """A metadata source which yields the blocks from input_source after
    applying callback to them."""

    def __init__(self, input_source, callback):
        super(MetadataSourceMap, self).__init__()
        self._input_source = input_source
        self._callback = callback

    def get_next_block(self):
        block = self._input_source.get_next_block()
        if block is None:
            return None
        return self._callback(block)


def mute_audioBlockFormat_by_importance(rendering_items, threshold):
    """Adapt non-HOA rendering items to emulate block format importance handling

    This installs an `MetadataSourceMap` which sets gains to 0 if the block
    importance is less than the given threshold.

    Parameters:
        rendering_items (iterable of RenderingItems): RenderingItems to adapt
        threshold (int): importance threshold

    Yields: RenderingItem
    """

    def mute_unimportant_block(type_metadata):
        if type_metadata.block_format.importance < threshold:
            return evolve(
                type_metadata, block_format=evolve(type_metadata.block_format, gain=0.0)
            )
        else:
            return type_metadata

    for item in rendering_items:
        if isinstance(item, HOARenderingItem):
            yield item
        else:
            yield evolve(
                item,
                metadata_source=MetadataSourceMap(
                    item.metadata_source, mute_unimportant_block
                ),
            )
