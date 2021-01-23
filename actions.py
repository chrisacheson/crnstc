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
class ActionWithDirection(Action):
    dx: int
    dy: int

    def perform(self, engine: Engine, entity: Entity) -> None:
        raise NotImplementedError()


class MeleeAction(ActionWithDirection):
    def perform(self, engine: Engine, entity: Entity) -> None:
        dest_x = entity.x + self.dx
        dest_y = entity.y + self.dy
        target = engine.game_map.get_blocking_entity_at_location(x=dest_x,
                                                                 y=dest_y)
        if not target:
            return

        print(f"You hit the {target.name}")


class MovementAction(ActionWithDirection):
    def perform(self, engine: Engine, entity: Entity) -> None:
        dest_x = entity.x + self.dx
        dest_y = entity.y + self.dy

        if not engine.game_map.in_bounds(x=dest_x, y=dest_y):
            return

        if not engine.game_map.tiles["walkable"][dest_x, dest_y]:
            return

        if engine.game_map.get_blocking_entity_at_location(x=dest_x, y=dest_y):
            return

        entity.move(self.dx, self.dy)


class BumpAction(ActionWithDirection):
    def perform(self, engine: Engine, entity: Entity) -> None:
        dest_x = entity.x + self.dx
        dest_y = entity.y + self.dy
        action: ActionWithDirection

        if engine.game_map.get_blocking_entity_at_location(x=dest_x, y=dest_y):
            action = MeleeAction(dx=self.dx, dy=self.dy)
        else:
            action = MovementAction(dx=self.dx, dy=self.dy)

        return action.perform(engine=engine, entity=entity)
