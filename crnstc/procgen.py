from __future__ import annotations

import random
from typing import Dict, Tuple, Iterator, List, TYPE_CHECKING
from dataclasses import dataclass

import tcod

from crnstc import entity_factories
from crnstc.game_map import GameMap
from crnstc import tile_types
from crnstc.geometry import Rectangle, Position, Vector

if TYPE_CHECKING:
    from crnstc.engine import Engine
    from crnstc.entity import Entity


max_items_by_floor = [(1, 1), (4, 2)]
max_enemies_by_floor = [(1, 2), (4, 3), (6, 5)]
item_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(entity_factories.medkit, 35)],
    4: [(entity_factories.telescoping_baton, 5)],
    6: [
        (entity_factories.grenade, 25),
        (entity_factories.ballistic_plate_armor, 15),
    ],
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
    shape: Rectangle

    @property
    def interior(self) -> Rectangle:
        return self.shape.grow(-1)


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
    interior = room.interior

    for entity in enemies + items:
        position = interior.random_position()

        if not any(entity.position == position for entity in dungeon.entities):
            entity.spawn(dungeon, position)


def tunnel_between(start: Position, end: Position) -> Iterator[Position]:
    if random.random() < 0.5:
        corner = Position(x=end.x, y=start.y)
    else:
        corner = Position(x=start.x, y=end.y)

    for x, y in tcod.los.bresenham(start, corner).tolist():
        yield Position(x=x, y=y)

    for x, y in tcod.los.bresenham(corner, end).tolist():
        yield Position(x=x, y=y)


def generate_dungeon(max_rooms: int, room_min_size: int, room_max_size: int,
                     map_shape: Rectangle, engine: Engine) -> GameMap:
    player = engine.player
    dungeon = GameMap(engine=engine, shape=map_shape, entities_=(player,))

    rooms: List[RectangularRoom] = []
    center_of_last_room = Position(0, 0)

    for r in range(max_rooms):
        min_size = Vector(dx=room_min_size, dy=room_min_size)
        max_size = Vector(dx=room_max_size, dy=room_max_size)
        shape = map_shape.random_rectangle(min_size=min_size,
                                           max_size=max_size)

        if any(shape.intersects(other_room.shape) for other_room in rooms):
            continue

        new_room = RectangularRoom(shape=shape)
        dungeon.tiles[new_room.interior.slice] = tile_types.floor

        if len(rooms) == 0:
            player.place(shape.center, dungeon)
        else:
            for pos in tunnel_between(rooms[-1].shape.center, shape.center):
                dungeon.tiles[pos] = tile_types.floor

            center_of_last_room = shape.center

        place_entities(new_room, dungeon, engine.game_world.current_floor)
        dungeon.tiles[center_of_last_room] = tile_types.down_stairs
        dungeon.down_stairs_location = center_of_last_room
        rooms.append(new_room)

    return dungeon
