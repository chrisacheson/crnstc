from __future__ import annotations

import random
from typing import Tuple, Iterator, List, TYPE_CHECKING
from dataclasses import dataclass, InitVar, field

import tcod

import entity_factories
from game_map import GameMap
import tile_types

if TYPE_CHECKING:
    from engine import Engine


@dataclass
class RectangularRoom:
    x: int
    y: int
    width: InitVar[int]
    height: InitVar[int]
    x2: int = field(init=False)
    y2: int = field(init=False)

    def __post_init__(self, width: int, height: int):
        self.x2 = self.x + width
        self.y2 = self.y + height

    @property
    def center(self) -> Tuple[int, int]:
        center_x = (self.x + self.x2) // 2
        center_y = (self.y + self.y2) // 2
        return center_x, center_y

    @property
    def inner(self) -> Tuple[slice, slice]:
        return slice(self.x + 1, self.x2), slice(self.y + 1, self.y2)

    def intersects(self, other: RectangularRoom) -> bool:
        return (self.x <= other.x2
                and self.x2 >= other.x
                and self.y <= other.y2
                and self.y2 >= other.y)


def place_entities(room: RectangularRoom, dungeon: GameMap,
                   max_enemies: int) -> None:
    num_enemies = random.randint(0, max_enemies)

    for i in range(num_enemies):
        x = random.randint(room.x + 1, room.x2 - 1)
        y = random.randint(room.y + 1, room.y2 - 1)

        if not any(entity.x == x and entity.y == y
                   for entity in dungeon.entities):
            if random.random() < 0.8:
                entity_factories.corpsec_guard.spawn(game_map=dungeon,
                                                     x=x, y=y)
            else:
                entity_factories.corpsec_soldier.spawn(game_map=dungeon,
                                                       x=x, y=y)


def tunnel_between(start: Tuple[int, int],
                   end: Tuple[int, int]) -> Iterator[Tuple[int, int]]:
    x1, y1 = start
    x2, y2 = end
    if random.random() < 0.5:
        corner_x, corner_y = x2, y1
    else:
        corner_x, corner_y = x1, y2

    for x, y in tcod.los.bresenham((x1, y1), (corner_x, corner_y)).tolist():
        yield x, y

    for x, y in tcod.los.bresenham((corner_x, corner_y), (x2, y2)).tolist():
        yield x, y


def generate_dungeon(max_rooms: int, room_min_size: int, room_max_size: int,
                     map_width: int, map_height: int,
                     max_enemies_per_room: int, engine: Engine) -> GameMap:
    player = engine.player
    dungeon = GameMap(engine=engine, width=map_width, height=map_height,
                      entities_=(player,))

    rooms: List[RectangularRoom] = []

    for r in range(max_rooms):
        room_width = random.randint(room_min_size, room_max_size)
        room_height = random.randint(room_min_size, room_max_size)
        x = random.randint(0, dungeon.width - room_width - 1)
        y = random.randint(0, dungeon.height - room_height - 1)
        new_room = RectangularRoom(x=x, y=y,
                                   width=room_width, height=room_height)

        if any(new_room.intersects(other_room) for other_room in rooms):
            continue

        dungeon.tiles[new_room.inner] = tile_types.floor

        if len(rooms) == 0:
            player.place(*new_room.center, dungeon)
        else:
            for x, y in tunnel_between(rooms[-1].center, new_room.center):
                dungeon.tiles[x, y] = tile_types.floor

        place_entities(new_room, dungeon, max_enemies_per_room)
        rooms.append(new_room)

    return dungeon
