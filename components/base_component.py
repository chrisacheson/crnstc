from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


@dataclass
class BaseComponent:
    entity: Entity = field(init=False)

    @property
    def engine(self) -> Engine:
        game_map = self.entity.game_map
        assert game_map is not None
        return game_map.engine
