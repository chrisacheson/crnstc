from __future__ import annotations

import random
from typing import Dict, Tuple, Iterator, List, TYPE_CHECKING
from dataclasses import dataclass, InitVar, field

import tcod

import entity_factories
from game_map import GameMap
import tile_types

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


max_items_by_floor = [(1, 1), (4, 2)]
max_enemies_by_floor = [(1, 2), (4, 3), (6, 5)]
item_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(entity_factories.medkit, 35)],
    6: [(entity_factories.grenade, 25)],
}
enemy_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(entity_factories.corpsec_guard, 80)],
    3: [(entity_factories.combat_drone, 15)],
    5: [(entity_factories.combat_drone, 30)],
    7: [(entity_factories.combat_drone, 60)],
}


def get_max_value_for_floor(weighted_chances_by_floor: List[Tuple[int, int]],
                            floor: int) -> int:
    current_value = 0

    for floor_minimum, value in weighted_chances_by_floor:
        if floor_minimum > floor:
            break
        else:
            current_value = value

    return current_value


def get_entitites_at_random(
    weighted_chances_by_floor: Dict[int, List[Tuple[Entity, int]]],
    number_of_entities: int,
    floor: int,
) -> List[Entity]:
    entity_weighted_chances = {}

    for key, values in weighted_chances_by_floor.items():
        if key > floor:
            break
        else:
            for value in values:
                entity, weighted_chance = value
                entity_weighted_chances[entity] = weighted_chance

    entities = list(entity_weighted_chances.keys())
    entity_weighted_chance_values = list(entity_weighted_chances.values())
    chosen_entities = random.choices(entities,
                                     weights=entity_weighted_chance_values,
                                     k=number_of_entities)
    return chosen_entities


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
                   floor_number: int) -> None:
    num_enemies = random.randint(
        0,
        get_max_value_for_floor(max_enemies_by_floor, floor_number),
    )
    num_items = random.randint(
        0,
        get_max_value_for_floor(max_items_by_floor, floor_number),
    )
    enemies: List[Entity] = get_entitites_at_random(enemy_chances, num_enemies,
                                                    floor_number)
    items: List[Entity] = get_entitites_at_random(item_chances, num_items,
                                                  floor_number)

    for entity in enemies + items:
        x = random.randint(room.x + 1, room.x2 - 1)
        y = random.randint(room.y + 1, room.y2 - 1)

        if not any(entity.x == x and entity.y == y
                   for entity in dungeon.entities):
            entity.spawn(dungeon, x, y)


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
                     engine: Engine) -> GameMap:
    player = engine.player
    dungeon = GameMap(engine=engine, width=map_width, height=map_height,
                      entities_=(player,))

    rooms: List[RectangularRoom] = []
    center_of_last_room = (0, 0)

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

            center_of_last_room = new_room.center

        place_entities(new_room, dungeon, engine.game_world.current_floor)
        dungeon.tiles[center_of_last_room] = tile_types.down_stairs
        dungeon.down_stairs_location = center_of_last_room
        rooms.append(new_room)

    return dungeon
