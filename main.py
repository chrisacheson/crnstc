#!/usr/bin/env python3
import copy

import tcod

import color
from engine import Engine
import entity_factories
from procgen import generate_dungeon


def main() -> None:
    screen_width = 80
    screen_height = 50
    map_width = 80
    map_height = 43
    room_max_size = 10
    room_min_size = 6
    max_rooms = 30
    max_enemies_per_room = 2

    tileset = tcod.tileset.load_tilesheet(path="16x16-sb-ascii.png",
                                          columns=16, rows=16,
                                          charmap=tcod.tileset.CHARMAP_CP437)
    console = tcod.Console(width=screen_width, height=screen_height, order="F")

    player = copy.deepcopy(entity_factories.player)
    engine = Engine(player=player)
    engine.game_map = generate_dungeon(
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
        map_width=map_width,
        map_height=map_height,
        max_enemies_per_room=max_enemies_per_room,
        engine=engine,
    )
    engine.update_fov()
    engine.message_log.add_message("You've broken into a corporate facility"
                                   " that looks suspiciously like a roguelike"
                                   " dungeon.", color.welcome_text)

    with tcod.context.new(
        columns=console.width,
        rows=console.height,
        tileset=tileset,
        title="Cyberpunk Roguelike (Name Subject to Change)",
        renderer=tcod.context.RENDERER_OPENGL2,
    ) as context:
        while True:
            console.clear()
            engine.event_handler.on_render(console=console)
            context.present(console)
            engine.event_handler.handle_events(context)


if __name__ == "__main__":
    main()
