#!/usr/bin/env python3
import tcod

from engine import Engine
from entity import Entity
from input_handlers import EventHandler
from colors import Colors
from procgen import generate_dungeon


def main() -> None:
    screen_width = 80
    screen_height = 50
    map_width = 80
    map_height = 45
    room_max_size = 10
    room_min_size = 6
    max_rooms = 30

    tileset = tcod.tileset.load_tilesheet(path="16x16-sb-ascii.png",
                                          columns=16, rows=16,
                                          charmap=tcod.tileset.CHARMAP_CP437)
    console = tcod.Console(width=screen_width, height=screen_height, order="F")
    event_handler = EventHandler()

    player = Entity(x=screen_width // 2, y=screen_height // 2, char="@",
                    color=Colors.white)
    npc = Entity(x=screen_width // 2 - 5, y=screen_height // 2, char="@",
                 color=Colors.yellow)
    entities = [npc, player]
    game_map = generate_dungeon(max_rooms=max_rooms,
                                room_min_size=room_min_size,
                                room_max_size=room_max_size,
                                map_width=map_width, map_height=map_height,
                                player=player)

    engine = Engine(entities=entities, event_handler=event_handler,
                    game_map=game_map, player=player)

    with tcod.context.new(
        columns=console.width,
        rows=console.height,
        tileset=tileset,
        title="Cyberpunk Roguelike (Name Subject to Change)",
        renderer=tcod.context.RENDERER_OPENGL2,
    ) as context:
        while True:
            engine.render(console=console, context=context)
            events = tcod.event.wait()
            engine.handle_events(events)


if __name__ == "__main__":
    main()
