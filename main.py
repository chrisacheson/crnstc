#!/usr/bin/env python3
import tcod

from engine import Engine
from entity import Entity
from input_handlers import EventHandler


def main() -> None:
    screen_width = 32
    screen_height = 32
    white = (255, 255, 255)
    yellow = (255, 255, 0)

    tileset = tcod.tileset.load_tilesheet(path="16x16-sb-ascii.png",
                                          columns=16, rows=16,
                                          charmap=tcod.tileset.CHARMAP_CP437)
    console = tcod.Console(width=screen_width, height=screen_height, order="F")
    event_handler = EventHandler()

    player = Entity(x=screen_width // 2, y=screen_height // 2, char="@",
                    color=white)
    npc = Entity(x=screen_width // 2 - 5, y=screen_height // 2, char="@",
                 color=yellow)
    entities = [npc, player]

    engine = Engine(entities=entities, event_handler=event_handler,
                    player=player)

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
