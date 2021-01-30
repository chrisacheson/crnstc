from __future__ import annotations

from typing import TYPE_CHECKING

from crnstc import color
from crnstc.geometry import Position, Rectangle

if TYPE_CHECKING:
    from tcod import Console
    from crnstc.engine import Engine
    from crnstc.game_map import GameMap


def get_names_at_location(position: Position, game_map: GameMap) -> str:
    if not game_map.in_bounds(position) or not game_map.visible[position]:
        return ""

    names = ", ".join(entity.name
                      for entity
                      in game_map.entities
                      if entity.position == position)
    return names.capitalize()


def render_bar(console: Console, current_value: int, maximum_value: int,
               shape: Rectangle) -> None:
    bar_width = int(float(current_value) / maximum_value * shape.w)
    console.draw_rect(*shape, ch=1, bg=color.bar_empty)

    if bar_width > 0:
        console.draw_rect(*shape.position, width=bar_width, height=shape.h,
                          ch=1, bg=color.bar_filled)

    console.print(*shape.relative(x=1, y=0),
                  string=f"HP: {current_value}/{maximum_value}",
                  fg=color.bar_text)


def render_dungeon_level(console: Console, dungeon_level: int,
                         position: Position) -> None:
    console.print(*position, string=f"Facility level: {dungeon_level}")


def render_names_at_mouse_location(console: Console, position: Position,
                                   engine: Engine) -> None:
    mouse_x, mouse_y = engine.mouse_location
    names_at_mouse_location = get_names_at_location(
        position=engine.mouse_location,
        game_map=engine.game_map,
    )
    console.print(*position, string=names_at_mouse_location)
