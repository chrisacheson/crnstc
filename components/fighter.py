from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass, field

from components.base_component import BaseComponent
from input_handlers import GameOverEventHandler
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
    entity: Actor = field(init=False)

    def __post_init__(self):
        self._hp = self.max_hp

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, value: int) -> None:
        self._hp = clamp(0, value, self.max_hp)

        if self._hp <= 0 and self.entity.ai:
            self.die()

    def die(self) -> None:
        if self.engine.player is self.entity:
            death_message = "You died!"
            death_message_color = color.player_die
            self.engine.event_handler = GameOverEventHandler(self.engine)
        else:
            death_message = f"{self.entity.name} is dead!"
            death_message_color = color.enemy_die

        self.entity.char = "%"
        self.entity.color = color.red
        self.entity.blocks_movement = False
        self.entity.ai = None
        self.entity.name = f"remains of {self.entity.name}"
        self.entity.render_order = RenderOrder.corpse
        self.engine.message_log.add_message(death_message, death_message_color)
