from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


@dataclass
class Action:
    entity: Entity

    @property
    def engine(self) -> Engine:
        game_map = self.entity.game_map
        assert game_map is not None
        return game_map.engine

    def perform(self) -> None:
        raise NotImplementedError()


class QuitGameAction(Action):
    def perform(self) -> None:
        raise SystemExit()


@dataclass
class ActionWithDirection(Action):
    dx: int
    dy: int

    @property
    def dest_xy(self) -> Tuple[int, int]:
        return self.entity.x + self.dx, self.entity.y + self.dy

    @property
    def blocking_entity(self) -> Optional[Entity]:
        return self.engine.game_map.get_blocker(*self.dest_xy)


class MeleeAction(ActionWithDirection):
    def perform(self) -> None:
        target = self.blocking_entity

        if not target:
            return

        print(f"You hit the {target.name}")


class MovementAction(ActionWithDirection):
    def perform(self) -> None:
        dest_x, dest_y = self.dest_xy

        if not self.engine.game_map.in_bounds(x=dest_x, y=dest_y):
            return

        if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
            return

        if self.engine.game_map.get_blocker(x=dest_x, y=dest_y):
            return

        self.entity.move(dx=self.dx, dy=self.dy)


class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        if self.blocking_entity:
            return MeleeAction(entity=self.entity,
                               dx=self.dx, dy=self.dy).perform()
        else:
            return MovementAction(entity=self.entity,
                                  dx=self.dx, dy=self.dy).perform()
