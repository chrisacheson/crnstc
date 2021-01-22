from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


class Action:
    def perform(self, engine: Engine, entity: Entity) -> None:
        raise NotImplementedError()


class QuitGameAction(Action):
    def perform(self, engine: Engine, entity: Entity) -> None:
        raise SystemExit()


@dataclass
class MovementAction(Action):
    dx: int
    dy: int

    def perform(self, engine: Engine, entity: Entity) -> None:
        dest_x = entity.x + self.dx
        dest_y = entity.y + self.dy

        if not engine.game_map.in_bounds(x=dest_x, y=dest_y):
            return

        if not engine.game_map.tiles["walkable"][dest_x, dest_y]:
            return

        entity.move(self.dx, self.dy)
