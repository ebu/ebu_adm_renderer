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
