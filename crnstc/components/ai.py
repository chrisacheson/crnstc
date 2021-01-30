from __future__ import annotations

from typing import List, TYPE_CHECKING

import numpy as np  # type: ignore
import tcod

from crnstc.actions import Action, MeleeAction, MovementAction, WaitAction
from crnstc.geometry import Position, Vector

if TYPE_CHECKING:
    from crnstc.entity import Actor


class BaseAI(Action):
    entity: Actor

    def perform(self) -> None:
        raise NotImplementedError()

    def get_path_to(self, position: Position) -> List[Position]:
        assert self.entity.game_map is not None
        cost = np.array(self.entity.game_map.tiles["walkable"], dtype=np.int8)

        for entity in self.entity.game_map.entities:
            if entity.blocks_movement and cost[entity.position]:
                cost[entity.position] += 10

        graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
        pathfinder = tcod.path.Pathfinder(graph)
        pathfinder.add_root(self.entity.position)
        path: List[List[int]] = pathfinder.path_to(position)[1:].tolist()

        return [Position(index[0], index[1]) for index in path]


class HostileEnemy(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Position] = []

    def perform(self) -> None:
        target = self.engine.player
        to_target = target.position - self.entity.position
        assert isinstance(to_target, Vector)
        distance = max(abs(to_target.dx), abs(to_target.dy))

        if self.engine.game_map.visible[self.entity.position]:
            if distance <= 1:
                return MeleeAction(self.entity, to_target).perform()

            self.path = self.get_path_to(target.position)

        if self.path:
            destination = self.path.pop(0)
            direction = destination - self.entity.position
            assert isinstance(direction, Vector)
            return MovementAction(self.entity, direction).perform()

        return WaitAction(self.entity).perform()
