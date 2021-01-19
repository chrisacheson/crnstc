#!/usr/bin/env python3
import tcod

from actions import QuitGameAction, MovementAction
from input_handlers import EventHandler


def main() -> None:
    screen_width = 32
    screen_height = 32
    player_x = screen_width // 2
    player_y = screen_height // 2

    tileset = tcod.tileset.load_tilesheet(path="16x16-sb-ascii.png",
                                          columns=16, rows=16,
                                          charmap=tcod.tileset.CHARMAP_CP437)
    console = tcod.Console(width=screen_width, height=screen_height, order="F")
    event_handler = EventHandler()

    with tcod.context.new(
        columns=console.width,
        rows=console.height,
        tileset=tileset,
        title="Cyberpunk Roguelike (Name Subject to Change)",
        renderer=tcod.context.RENDERER_OPENGL2,
    ) as context:
        while True:
            console.clear()
            console.print(x=player_x, y=player_y, string="@")
            context.present(console)

            for event in tcod.event.wait():
                action = event_handler.dispatch(event)

                if action is None:
                    continue

                if isinstance(action, MovementAction):
                    player_x += action.dx
                    player_y += action.dy
                elif isinstance(action, QuitGameAction):
                    raise SystemExit()


if __name__ == "__main__":
    main()
