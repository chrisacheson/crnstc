from typing import Tuple

import numpy as np  # type: ignore

from crnstc import color


graphic_dt = np.dtype([("ch", np.int32),
                       ("fg", "3B"),
                       ("bg", "3B")])
tile_dt = np.dtype([("walkable", np.bool),
                    ("transparent", np.bool),
                    ("dark", graphic_dt),
                    ("light", graphic_dt)])


def new_tile(
    *,
    walkable: int,
    transparent: int,
    dark: Tuple[int, color.Color, color.Color],
    light: Tuple[int, color.Color, color.Color],
) -> np.ndarray:
    return np.array((walkable, transparent, dark, light), dtype=tile_dt)


shroud = np.array((ord(" "), color.white, color.black), dtype=graphic_dt)

floor = new_tile(walkable=True, transparent=True,
                 dark=(ord(" "), color.white, color.purple),
                 light=(ord(" "), color.white, color.gold))
wall = new_tile(walkable=False, transparent=False,
                dark=(ord(" "), color.white, color.navy_blue),
                light=(ord(" "), color.white, color.bronze))
down_stairs = new_tile(walkable=True, transparent=True,
                       dark=(ord(">"), color.navy_blue, color.purple),
                       light=(ord(">"), color.white, color.gold))
