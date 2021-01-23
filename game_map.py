from __future__ import annotations

from typing import Set, Iterable, Optional, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

import numpy as np  # type: ignore
from tcod.console import Console

import tile_types

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


@dataclass
class GameMap:
    engine: Engine
    width: int
    height: int
    entities: Set[Entity] = field(init=False)
    entities_: InitVar[Iterable[Entity]]

    def __post_init__(self, entities_):
        self.entities = set(entities_)
        self.tiles = np.full((self.width, self.height),
                             fill_value=tile_types.wall, order="F")
        self.visible = np.full((self.width, self.height),
                               fill_value=False, order="F")
        self.explored = np.full((self.width, self.height),
                                fill_value=False, order="F")

    def get_blocker(self, x: int, y: int) -> Optional[Entity]:
        for entity in self.entities:
            if entity.blocks_movement and entity.x == x and entity.y == y:
                return entity

        return None

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def render(self, console: Console) -> None:
        console.tiles_rgb[0:self.width, 0:self.height] = np.select(
            condlist=[self.visible, self.explored],
            choicelist=[self.tiles["light"], self.tiles["dark"]],
            default=tile_types.shroud,
        )

        for entity in self.entities:
            if self.visible[entity.x, entity.y]:
                console.print(x=entity.x, y=entity.y, string=entity.char,
                              fg=entity.color)
