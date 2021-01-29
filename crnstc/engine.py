from __future__ import annotations

import lzma
import pickle
from typing import TYPE_CHECKING
from dataclasses import dataclass, field

from tcod.console import Console
from tcod.map import compute_fov

from crnstc import exceptions
from crnstc.message_log import MessageLog
from crnstc.render_functions import (render_bar,
                                     render_names_at_mouse_location,
                                     render_dungeon_level)

if TYPE_CHECKING:
    from crnstc.entity import Actor
    from crnstc.game_map import GameMap, GameWorld


@dataclass
class Engine:
    player: Actor
    game_map: GameMap = field(init=False)
    game_world: GameWorld = field(init=False)

    def __post_init__(self):
        self.message_log = MessageLog()
        self.mouse_location = (0, 0)

    def handle_enemy_turns(self) -> None:
        for entity in set(self.game_map.actors) - {self.player}:
            if entity.ai:
                try:
                    entity.ai.perform()
                except exceptions.Impossible:
                    pass

    def update_fov(self) -> None:
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles["transparent"],
            (self.player.x, self.player.y),
            radius=8,
        )
        self.game_map.explored |= self.game_map.visible

    def render(self, console: Console) -> None:
        self.game_map.render(console)
        self.message_log.render(console=console, x=21, y=45, width=40,
                                height=5)
        render_bar(console=console, current_value=self.player.fighter.hp,
                   maximum_value=self.player.fighter.max_hp, total_width=20)
        render_dungeon_level(console=console,
                             dungeon_level=self.game_world.current_floor,
                             location=(0, 47))
        render_names_at_mouse_location(console=console, x=21, y=44,
                                       engine=self)

    def save_as(self, filename: str) -> None:
        save_data = lzma.compress(pickle.dumps(self))

        with open(filename, "wb") as f:
            f.write(save_data)