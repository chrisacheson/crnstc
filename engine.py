from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass, field

from tcod.context import Context
from tcod.console import Console
from tcod.map import compute_fov

from input_handlers import EventHandler, MainGameEventHandler

if TYPE_CHECKING:
    from entity import Actor
    from game_map import GameMap


@dataclass
class Engine:
    player: Actor
    game_map: GameMap = field(init=False)

    def __post_init__(self):
        self.event_handler: EventHandler = MainGameEventHandler(self)

    def handle_enemy_turns(self) -> None:
        for entity in set(self.game_map.actors) - {self.player}:
            if entity.ai:
                entity.ai.perform()

    def update_fov(self) -> None:
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles["transparent"],
            (self.player.x, self.player.y),
            radius=8,
        )
        self.game_map.explored |= self.game_map.visible

    def render(self, console: Console, context: Context) -> None:
        self.game_map.render(console)
        console.print(x=1, y=47, string=f"HP: {self.player.fighter.hp}"
                                        f"/{self.player.fighter.max_hp}")
        context.present(console)
        console.clear()
