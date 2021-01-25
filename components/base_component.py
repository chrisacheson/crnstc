from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity
    from game_map import GameMap


@dataclass
class BaseComponent:
    parent: Entity = field(init=False)

    @property
    def game_map(self) -> GameMap:
        return self.parent.game_map

    @property
    def engine(self) -> Engine:
        return self.game_map.engine
