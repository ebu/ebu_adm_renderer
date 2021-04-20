import pytest
import random
import numpy as np
import numpy.testing as npt
from ....fileio.adm.elements import (AudioBlockFormatObjects, CartesianZone, ChannelLock, ObjectDivergence,
                                     ObjectPolarPosition, ObjectCartesianPosition, PolarZone)
from ...metadata_input import ObjectTypeMetadata, ExtraData
from ...geom import PolarPosition
from ....common import PolarScreen


def generate_zone_exclusion(cartesian):
    if cartesian:
        split = random.choice(["X", "Y", "Z"] + [None] * 7)
        if split is not None:
            return [
                CartesianZone(
                    minX=0.0 if split == "X" else -1.0,
                    maxX=1.0,
                    minY=0.0 if split == "Y" else -1.0,
                    maxY=1.0,
                    minZ=0.5 if split == "Z" else -1.0,
                    maxZ=1.0,
                ),
            ]
            return []
    else:
        split = random.choice(["az", "el"] + [None] * 8)

        if split is not None:
            return [
                PolarZone(
                    minElevation=45.0 if split == "el" else -90.0,
                    maxElevation=90.0,
                    minAzimuth=0.0 if split == "az" else -180.0,
                    maxAzimuth=180.0,
                ),
            ]
    return []


def generate_random_ObjectTypeMetadata(cart_pos=None, cartesian=None,
                                       azimuth=None, elevation=None, distance=None,
                                       X=None, Y=None, Z=None,
                                       screen_edge_lock_horizontal=None,
                                       screen_edge_lock_vertical=None,
                                       width=None, height=None, depth=None,
                                       has_divergence=None, divergence_value=None, divergence_range=None,
                                       screenRef=None,
                                       ):
    """Generate a random ObjectTypeMetadata, with some fixed attributes if
    specified.
    """
    if cart_pos is None: cart_pos = random.choice([False, True])
    if cartesian is None: cartesian = random.choice([False, True])

    if cart_pos:
        if X is None: X = random.uniform(-1, 1)
        if Y is None: Y = random.uniform(-1, 1)
        if Z is None: Z = random.uniform(-1, 1)
        position = ObjectCartesianPosition(X=X, Y=Y, Z=Z)
    else:
        if azimuth is None: azimuth = random.uniform(-180, 180)
        if elevation is None: elevation = random.uniform(-90, 90)
        if distance is None: distance = random.uniform(0, 1)
        position = ObjectPolarPosition(azimuth=azimuth, elevation=elevation, distance=distance)

    if screen_edge_lock_horizontal is None:
        position.screenEdgeLock.vertical = random.choice([None] * 8 + ["left", "right"])
    if screen_edge_lock_vertical is None:
        position.screenEdgeLock.horizontal = random.choice([None] * 8 + ["top", "bottom"])

    if screenRef is None: screenRef = bool(random.randrange(2))
    reference_screen = PolarScreen(aspectRatio=random.uniform(1, 2),
                                   centrePosition=PolarPosition(random.uniform(-45, 45),
                                                                random.uniform(-45, 45),
                                                                1.0),
                                   widthAzimuth=random.uniform(10, 80))

    if cartesian:
        if width is None:
            width = random.uniform(0, 2)
        if height is None:
            height = random.uniform(0, 2)
        if depth is None:
            depth = random.uniform(0, 2)
    else:
        if width is None:
            width = random.uniform(0, 360)
        if height is None:
            height = random.uniform(0, 360)
        if depth is None:
            depth = random.uniform(0, 1)

    channelLock = None
    if random.randrange(15) == 0:
        channelLock = ChannelLock(maxDistance=random.uniform(0, 2))

    if has_divergence is None: has_divergence = random.choice([False, True])
    if divergence_value is None: divergence_value = random.uniform(0, 1)
    if divergence_range is None: divergence_range = random.uniform(0, 1) if cartesian else random.uniform(0, 180)

    if cartesian:
        objectDivergence = ObjectDivergence(value=divergence_value, positionRange=divergence_range)
    else:
        objectDivergence = ObjectDivergence(value=divergence_value, azimuthRange=divergence_range)

    block_format = AudioBlockFormatObjects(position=position,
                                           width=width, height=height, depth=depth,
                                           cartesian=cartesian,
                                           channelLock=channelLock,
                                           objectDivergence=objectDivergence if has_divergence else None,
                                           screenRef=screenRef,
                                           zoneExclusion=generate_zone_exclusion(cartesian))
    return ObjectTypeMetadata(block_format=block_format, extra_data=ExtraData(reference_screen=reference_screen))


def generate_random_ObjectTypeMetadatas():
    """Generate a list of ObjectTypeMetadata, including random elements and
    known edge cases.
    """
    for i in range(10):
        yield generate_random_ObjectTypeMetadata(cart_pos=True, X=0.0, Y=0.0, Z=0.0)
    for i in range(10):
        yield generate_random_ObjectTypeMetadata(cart_pos=True, X=0.0, Y=0.0, Z=0.0, width=0.0, height=0.0, depth=0.0)

    for i in range(10):
        pos = np.random.uniform(-1, 1, 3)
        pos /= np.max(np.abs(pos))
        X, Y, Z = pos
        yield generate_random_ObjectTypeMetadata(cart_pos=True, X=X, Y=Y, Z=Z, width=0.0, height=0.0, depth=0.0)
        yield generate_random_ObjectTypeMetadata(cart_pos=True, X=X, Y=Y, Z=Z)

    for i in range(10):
        yield generate_random_ObjectTypeMetadata(cart_pos=False, distance=0.0)
    for i in range(10):
        yield generate_random_ObjectTypeMetadata(cart_pos=False, distance=1.0)
    for i in range(10):
        yield generate_random_ObjectTypeMetadata(cart_pos=False, distance=0.0, width=0.0, height=0.0, depth=0.0)

    yield generate_random_ObjectTypeMetadata(cart_pos=True, X=0.0, Y=0.0, Z=0.0, screenRef=True)
    yield generate_random_ObjectTypeMetadata(cart_pos=False, distance=0.0, screenRef=True)

    for i in range(1000):
        yield generate_random_ObjectTypeMetadata()


@pytest.mark.no_cover
def test_changes_random(layout, gain_calc):
    """Check that the result of the gain calculator with a selection of
    parameters stays the same.
    """
    import py.path
    files_dir = py.path.local(__file__).dirpath() / "data" / "gain_calc_pvs"

    import pickle
    inputs_f = files_dir / "inputs.pickle"
    outputs_f = files_dir / "outputs.npz"

    if inputs_f.check():
        with open(str(inputs_f), 'rb') as f:
            inputs = pickle.load(f)
    else:
        inputs = list(generate_random_ObjectTypeMetadatas())

        inputs_f.dirpath().ensure_dir()
        with open(str(inputs_f), 'wb') as f:
            pickle.dump(inputs, f, protocol=2)

    pvs = [gain_calc.render(input) for input in inputs]
    direct = np.array([pv.direct for pv in pvs])
    diffuse = np.array([pv.diffuse for pv in pvs])

    if outputs_f.check():
        loaded = np.load(str(outputs_f))
        loaded_directs = loaded["direct"]
        loaded_diffuses = loaded["diffuse"]

        for input, pv, loaded_direct, loaded_diffuse in zip(inputs, pvs, loaded_directs, loaded_diffuses):
            npt.assert_allclose(pv.direct, loaded_direct, err_msg=repr(input))
            npt.assert_allclose(pv.diffuse, loaded_diffuse, err_msg=repr(input))
    else:
        outputs_f.dirpath().ensure_dir()
        np.savez_compressed(str(outputs_f), direct=direct, diffuse=diffuse)
        pytest.skip("generated pv file for gain calc")
