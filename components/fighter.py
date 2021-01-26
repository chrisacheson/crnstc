from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass, field

from components.base_component import BaseComponent
from utils import clamp
import color
from render_order import RenderOrder

if TYPE_CHECKING:
    from entity import Actor


@dataclass
class Fighter(BaseComponent):
    max_hp: int
    defense: int
    power: int
    parent: Actor = field(init=False)

    def __post_init__(self):
        self._hp = self.max_hp

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, value: int) -> None:
        self._hp = clamp(0, value, self.max_hp)

        if self._hp <= 0 and self.parent.ai:
            self.die()

    def die(self) -> None:
        if self.engine.player is self.parent:
            death_message = "You died!"
            death_message_color = color.player_die
        else:
            death_message = f"{self.parent.name} is dead!"
            death_message_color = color.enemy_die

        self.parent.char = "%"
        self.parent.color = color.red
        self.parent.blocks_movement = False
        self.parent.ai = None
        self.parent.name = f"remains of {self.parent.name}"
        self.parent.render_order = RenderOrder.corpse
        self.engine.message_log.add_message(death_message, death_message_color)

    def heal(self, amount: int) -> int:
        old_hp = self.hp
        self.hp += amount
        recovered = self.hp - old_hp
        return recovered

    def take_damage(self, amount: int) -> None:
        self.hp -= amount
