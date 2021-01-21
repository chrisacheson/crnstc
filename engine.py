from typing import List, Iterable, Any

from tcod.context import Context
from tcod.console import Console

from actions import QuitGameAction, MovementAction
from entity import Entity
from input_handlers import EventHandler


class Engine:
    def __init__(self, entities: List[Entity], event_handler: EventHandler,
                 player: Entity):
        self.entities = entities
        self.event_handler = event_handler
        self.player = player

    def handle_events(self, events: Iterable[Any]) -> None:
        for event in events:
            action = self.event_handler.dispatch(event)

            if action is None:
                continue

            if isinstance(action, MovementAction):
                self.player.move(dx=action.dx, dy=action.dy)
            elif isinstance(action, QuitGameAction):
                raise SystemExit()

    def render(self, console: Console, context: Context) -> None:
        for entity in self.entities:
            console.print(x=entity.x, y=entity.y, string=entity.char,
                          fg=entity.color)
        context.present(console)
        console.clear()
