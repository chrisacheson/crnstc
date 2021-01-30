from __future__ import annotations

import copy
from typing import Optional, Type, TypeVar, TYPE_CHECKING, Union
from dataclasses import dataclass

from crnstc import color
from crnstc.render_order import RenderOrder
from crnstc.geometry import Position, Vector

if TYPE_CHECKING:
    from crnstc.components.ai import BaseAI
    from crnstc.components.consumable import Consumable
    from crnstc.components.equipment import Equipment
    from crnstc.components.equippable import Equippable
    from crnstc.components.fighter import Fighter
    from crnstc.components.inventory import Inventory
    from crnstc.components.level import Level
    from crnstc.game_map import GameMap

T = TypeVar("T", bound="Entity")


@dataclass(eq=False)
class Entity:
    parent: Optional[Union[GameMap, Inventory]] = None
    position: Position = Position(x=0, y=0)
    char: str = "?"
    color: color.Color = color.white
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

    def spawn(self: T, game_map: GameMap, position: Position) -> T:
        clone = copy.deepcopy(self)
        clone.position = position
        clone.parent = game_map
        game_map.entities.add(clone)
        return clone

    def place(self, position: Position,
              game_map: Optional[GameMap] = None) -> None:
        self.position = position

        if game_map:
            if self.parent and self.parent is game_map:
                self.parent.entities.remove(self)  # type: ignore
            self.parent = game_map
            game_map.entities.add(self)

    def move(self, direction: Vector) -> None:
        self.position += direction


class Actor(Entity):
    # TODO: Need to refactor this before we can use dataclass on it
    def __init__(
        self,
        *,
        position: Position = Position(x=0, y=0),
        char: str = "?",
        color: color.Color = color.white,
        name: str = "<Unnamed>",
        ai_cls: Type[BaseAI],
        equipment: Equipment,
        fighter: Fighter,
        inventory: Inventory,
        level: Level,
    ):
        super().__init__(position=position, char=char, color=color, name=name,
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
        position: Position = Position(x=0, y=0),
        char: str = "?",
        color: color.Color = color.white,
        name: str = "<Unnamed>",
        consumable: Optional[Consumable] = None,
        equippable: Optional[Equippable] = None,
    ):
        super().__init__(position=position, char=char, color=color, name=name,
                         blocks_movement=False, render_order=RenderOrder.item)
        self.consumable = consumable

        if self.consumable:
            self.consumable.parent = self

        self.equippable = equippable

        if self.equippable:
            self.equippable.parent = self
