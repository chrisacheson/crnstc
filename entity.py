from __future__ import annotations

import copy
from typing import Optional, Tuple, Type, TypeVar, TYPE_CHECKING, Union
from dataclasses import dataclass

import color
from render_order import RenderOrder

if TYPE_CHECKING:
    from components.ai import BaseAI
    from components.consumable import Consumable
    from components.fighter import Fighter
    from components.inventory import Inventory
    from game_map import GameMap

T = TypeVar("T", bound="Entity")


@dataclass(eq=False)
class Entity:
    parent: Optional[Union[GameMap, Inventory]] = None
    x: int = 0
    y: int = 0
    char: str = "?"
    color: Tuple[int, int, int] = color.white
    name: str = "<Unnamed>"
    blocks_movement: bool = False
    render_order: RenderOrder = RenderOrder.corpse

    def __post_init__(self):
        if self.parent and isinstance(self.parent, GameMap):
            self.parent.entities.add(self)

    @property
    def game_map(self) -> GameMap:
        assert self.parent is not None
        return self.parent.game_map

    def spawn(self: T, game_map: GameMap, x: int, y: int) -> T:
        clone = copy.deepcopy(self)
        clone.x = x
        clone.y = y
        clone.parent = game_map
        game_map.entities.add(clone)
        return clone

    def place(self, x: int, y: int,
              game_map: Optional[GameMap] = None) -> None:
        self.x, self.y = x, y

        if game_map:
            if self.parent and self.parent is game_map:
                self.parent.entities.remove(self)  # type: ignore
            self.parent = game_map
            game_map.entities.add(self)

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy


class Actor(Entity):
    # TODO: Need to refactor this before we can use dataclass on it
    def __init__(self, *, x: int = 0, y: int = 0, char: str = "?",
                 color: Tuple[int, int, int] = color.white,
                 name: str = "<Unnamed>", ai_cls: Type[BaseAI],
                 fighter: Fighter, inventory: Inventory):
        super().__init__(x=x, y=y, char=char, color=color, name=name,
                         blocks_movement=True, render_order=RenderOrder.actor)
        self.ai: Optional[BaseAI] = ai_cls(self)
        self.fighter = fighter
        self.fighter.parent = self
        self.inventory = inventory
        self.inventory.parent = self

    @property
    def is_alive(self) -> bool:
        return bool(self.ai)


class Item(Entity):
    # TODO: Need to refactor this before we can use dataclass on it
    def __init__(self, *, x: int = 0, y: int = 0, char: str = "?",
                 color: Tuple[int, int, int] = color.white,
                 name: str = "<Unnamed>", consumable: Consumable):
        super().__init__(x=x, y=y, char=char, color=color, name=name,
                         blocks_movement=False, render_order=RenderOrder.item)
        self.consumable = consumable
        self.consumable.parent = self
