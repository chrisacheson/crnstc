from __future__ import annotations

from typing import Set, Iterable, Iterator, Optional, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

import numpy as np  # type: ignore
from tcod.console import Console

from crnstc.entity import Actor, Item
from crnstc import tile_types
from crnstc.geometry import Position, Rectangle

if TYPE_CHECKING:
    from crnstc.engine import Engine
    from crnstc.entity import Entity


@dataclass
class GameMap:
    engine: Engine
    shape: Rectangle
    entities: Set[Entity] = field(init=False)
    entities_: InitVar[Iterable[Entity]]

    def __post_init__(self, entities_):
        self.entities = set(entities_)
        self.shape = Rectangle(0, 0, *self.shape.dimensions)
        dimensions = self.shape.dimensions
        self.tiles = np.full(dimensions, fill_value=tile_types.wall, order="F")
        self.visible = np.full(dimensions, fill_value=False, order="F")
        self.explored = np.full(dimensions, fill_value=False, order="F")
        self.down_stairs_location = Position(0, 0)

    @property
    def game_map(self) -> GameMap:
        return self

    @property
    def actors(self) -> Iterator[Actor]:
        yield from (entity
                    for entity
                    in self.entities
                    if isinstance(entity, Actor) and entity.is_alive)

    @property
    def items(self) -> Iterator[Item]:
        yield from (entity
                    for entity
                    in self.entities
                    if isinstance(entity, Item))

    def get_blocker(self, position: Position) -> Optional[Entity]:
        for entity in self.entities:
            if entity.blocks_movement and entity.position == position:
                return entity

        return None

    def get_actor_at(self, position: Position) -> Optional[Actor]:
        for actor in self.actors:
            if actor.position == position:
                return actor

        return None

    def in_bounds(self, position: Position) -> bool:
        return self.shape.contains(position)

    def render(self, console: Console) -> None:
        console.tiles_rgb[self.shape.slice] = np.select(
            condlist=[self.visible, self.explored],
            choicelist=[self.tiles["light"], self.tiles["dark"]],
            default=tile_types.shroud,
        )

        entities_sorted_for_rendering = sorted(
            self.entities,
            key=lambda x: x.render_order.value,
        )

        for entity in entities_sorted_for_rendering:
            if self.visible[entity.position]:
                console.print(*entity.position, string=entity.char,
                              fg=entity.color)


@dataclass
class GameWorld:
    engine: Engine
    map_shape: Rectangle
    max_rooms: int
    room_min_size: int
    room_max_size: int
    current_floor: int = 0

    def generate_floor(self) -> None:
        from crnstc.procgen import generate_dungeon

        self.current_floor += 1
        self.engine.game_map = generate_dungeon(
            max_rooms=self.max_rooms,
            room_min_size=self.room_min_size,
            room_max_size=self.room_max_size,
            map_shape=self.map_shape,
            engine=self.engine,
        )
