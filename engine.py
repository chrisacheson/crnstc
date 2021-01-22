from typing import List, Iterable, Any
from dataclasses import dataclass

from tcod.context import Context
from tcod.console import Console

from entity import Entity
from game_map import GameMap
from input_handlers import EventHandler


@dataclass
class Engine:
    entities: List[Entity]
    event_handler: EventHandler
    game_map: GameMap
    player: Entity

    def handle_events(self, events: Iterable[Any]) -> None:
        for event in events:
            action = self.event_handler.dispatch(event)

            if action is None:
                continue

            action.perform(self, self.player)

    def render(self, console: Console, context: Context) -> None:
        self.game_map.render(console)

        for entity in self.entities:
            console.print(x=entity.x, y=entity.y, string=entity.char,
                          fg=entity.color)

        context.present(console)
        console.clear()
