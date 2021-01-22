from typing import Tuple

import numpy as np

from colors import Colors


graphic_dt = np.dtype([("ch", np.int32),
                       ("fg", "3B"),
                       ("bg", "3B")])
tile_dt = np.dtype([("walkable", np.bool),
                    ("transparent", np.bool),
                    ("dark", graphic_dt)])


def new_tile(
    *,
    walkable: int,
    transparent: int,
    dark: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
) -> np.ndarray:
    return np.array((walkable, transparent, dark), dtype=tile_dt)


floor = new_tile(walkable=True, transparent=True,
                 dark=(ord(" "), Colors.white, Colors.purple))
wall = new_tile(walkable=False, transparent=False,
                dark=(ord(" "), Colors.white, Colors.navy_blue))
