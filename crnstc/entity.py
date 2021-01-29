from __future__ import annotations

import copy
import math
from typing import Optional, Tuple, Type, TypeVar, TYPE_CHECKING, Union
from dataclasses import dataclass

import color
from render_order import RenderOrder

if TYPE_CHECKING:
    from components.ai import BaseAI
    from components.consumable import Consumable
    from components.equipment import Equipment
    from components.equippable import Equippable
    from components.fighter import Fighter
    from components.inventory import Inventory
    from components.level import Level
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

    def distance(self, x: int, y: int) -> float:
        dx = x - self.x
        dy = y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy


class Actor(Entity):
    # TODO: Need to refactor this before we can use dataclass on it
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = color.white,
        name: str = "<Unnamed>",
        ai_cls: Type[BaseAI],
        equipment: Equipment,
        fighter: Fighter,
        inventory: Inventory,
        level: Level,
    ):
        super().__init__(x=x, y=y, char=char, color=color, name=name,
                         blocks_movement=True, render_order=RenderOrder.actor)
        self.ai: Optional[BaseAI] = ai_cls(self)
        self.equipment: Equipment = equipment
        self.equipment.parent = self
        self.fighter = fighter
        self.fighter.parent = self
        self.inventory = inventory
        self.inventory.parent = self
        self.level = level
        self.level.parent = self

    @property
    def is_alive(self) -> bool:
        return bool(self.ai)


class Item(Entity):
    # TODO: Need to refactor this before we can use dataclass on it
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = color.white,
        name: str = "<Unnamed>",
        consumable: Optional[Consumable] = None,
        equippable: Optional[Equippable] = None,
    ):
        super().__init__(x=x, y=y, char=char, color=color, name=name,
                         blocks_movement=False, render_order=RenderOrder.item)
        self.consumable = consumable

        if self.consumable:
            self.consumable.parent = self

        self.equippable = equippable

        if self.equippable:
            self.equippable.parent = self
