from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass

import tcod.event

from actions import Action, QuitGameAction, BumpAction

if TYPE_CHECKING:
    from engine import Engine


@dataclass
class EventHandler(tcod.event.EventDispatch[Action]):
    engine: Engine

    def handle_events(self) -> None:
        for event in tcod.event.wait():
            action = self.dispatch(event)

            if action is None:
                continue

            action.perform()
            self.engine.handle_enemy_turns()
            self.engine.update_fov()

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        action: Optional[Action] = None
        key = event.sym
        player = self.engine.player

        if key == tcod.event.K_UP:
            action = BumpAction(entity=player, dx=0, dy=-1)
        elif key == tcod.event.K_DOWN:
            action = BumpAction(entity=player, dx=0, dy=1)
        elif key == tcod.event.K_LEFT:
            action = BumpAction(entity=player, dx=-1, dy=0)
        elif key == tcod.event.K_RIGHT:
            action = BumpAction(entity=player, dx=1, dy=0)
        elif key == tcod.event.K_ESCAPE:
            action = QuitGameAction(entity=player)

        return action
