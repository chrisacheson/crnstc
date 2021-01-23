from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass, field

from tcod.context import Context
from tcod.console import Console
from tcod.map import compute_fov

from input_handlers import EventHandler

if TYPE_CHECKING:
    from entity import Entity
    from game_map import GameMap


@dataclass
class Engine:
    player: Entity
    game_map: GameMap = field(init=False)

    def __post_init__(self):
        self.event_handler: EventHandler = EventHandler(self)

    def handle_enemy_turns(self) -> None:
        for entity in self.game_map.entities - {self.player}:
            print(f"The {entity.name} wonders when it"
                  " will get to take a real turn.")

    def update_fov(self) -> None:
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles["transparent"],
            (self.player.x, self.player.y),
            radius=8,
        )
        self.game_map.explored |= self.game_map.visible

    def render(self, console: Console, context: Context) -> None:
        self.game_map.render(console)

        context.present(console)
        console.clear()
