from __future__ import annotations

import copy
from typing import Optional, Tuple, Type, TypeVar, TYPE_CHECKING
from dataclasses import dataclass

from colors import Colors
from render_order import RenderOrder

if TYPE_CHECKING:
    from components.ai import BaseAI
    from components.fighter import Fighter
    from game_map import GameMap

T = TypeVar("T", bound="Entity")


@dataclass(eq=False)
class Entity:
    game_map: Optional[GameMap] = None
    x: int = 0
    y: int = 0
    char: str = "?"
    color: Tuple[int, int, int] = Colors.white
    name: str = "<Unnamed>"
    blocks_movement: bool = False
    render_order: RenderOrder = RenderOrder.corpse

    def __post_init__(self):
        if self.game_map:
            self.game_map.entities.add(self)

    def spawn(self: T, game_map: GameMap, x: int, y: int) -> T:
        clone = copy.deepcopy(self)
        clone.x = x
        clone.y = y
        clone.game_map = game_map
        game_map.entities.add(clone)
        return clone

    def place(self, x: int, y: int,
              game_map: Optional[GameMap] = None) -> None:
        self.x, self.y = x, y

        if game_map:
            if self.game_map:
                self.game_map.entities.remove(self)
            self.game_map = game_map
            game_map.entities.add(self)

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy


class Actor(Entity):
    # TODO: Need to refactor this before we can use dataclass on it
    def __init__(self, *, x: int = 0, y: int = 0, char: str = "?",
                 color: Tuple[int, int, int] = Colors.white,
                 name: str = "<Unnamed>", ai_cls: Type[BaseAI],
                 fighter: Fighter):
        super().__init__(x=x, y=y, char=char, color=color, name=name,
                         blocks_movement=True, render_order=RenderOrder.actor)
        self.ai: Optional[BaseAI] = ai_cls(self)
        self.fighter = fighter
        self.fighter.entity = self

    @property
    def is_alive(self) -> bool:
        return bool(self.ai)
