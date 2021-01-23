from __future__ import annotations

import copy
from typing import Tuple, TypeVar, TYPE_CHECKING
from dataclasses import dataclass

from colors import Colors

if TYPE_CHECKING:
    from game_map import GameMap

T = TypeVar("T", bound="Entity")


@dataclass(eq=False)
class Entity:
    x: int = 0
    y: int = 0
    char: str = "?"
    color: Tuple[int, int, int] = Colors.white
    name: str = "<Unnamed>"
    blocks_movement: bool = False

    def spawn(self: T, game_map: GameMap, x: int, y: int) -> T:
        clone = copy.deepcopy(self)
        clone.x = x
        clone.y = y
        game_map.entities.add(clone)
        return clone

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy
